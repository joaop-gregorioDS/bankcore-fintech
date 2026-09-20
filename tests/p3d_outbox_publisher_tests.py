import asyncio
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from sqlalchemy import select, update

from environment import validate_test_database_url


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ["BANKCORE_TEST_DATABASE_URL"]
KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
KAFKA_TOPIC = os.environ["KAFKA_TOPIC"]
validate_test_database_url(TEST_DATABASE_URL)
sys.path.insert(0, str(ROOT / "services/transactions-service"))
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import OutboxEvent  # noqa: E402
from app.outbox_publisher import OutboxPublisher  # noqa: E402


class FailingProducer:
    async def send_and_wait(self, *args, **kwargs):
        raise RuntimeError("Authorization: Bearer secret-token password=database-secret")


class OutboxPublisherKafkaTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_DATABASE_URL, echo=False)
        self.sessions = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        await self.ensure_topic()
        self.event_id = uuid4()
        self.message_key = str(uuid4())
        self.payload = {
            "event_id": str(self.event_id),
            "event_type": "transaction.completed",
            "event_version": 1,
            "occurred_at": "2026-09-20T12:00:00Z",
            "producer": "transactions-service",
            "correlation_id": str(uuid4()),
            "data": {
                "transaction_id": self.message_key,
                "source_account_id": str(uuid4()),
                "destination_account_id": str(uuid4()),
                "amount_cents": 2500,
                "operation_type": "PIX",
                "risk_assessment_id": str(uuid4()),
                "risk_rules_version": "risk-rules-v1",
            },
        }
        async with self.sessions() as session:
            await session.execute(OutboxEvent.__table__.delete())
            session.add(
                OutboxEvent(
                    id=self.event_id,
                    aggregate_type="transaction",
                    aggregate_id=uuid4(),
                    event_type="transaction.completed",
                    event_version=1,
                    message_key=self.message_key,
                    payload=self.payload,
                    occurred_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

    async def asyncTearDown(self):
        async with self.sessions() as session:
            await session.execute(OutboxEvent.__table__.delete())
            await session.commit()
        await self.engine.dispose()

    async def ensure_topic(self):
        admin = AIOKafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
        await admin.start()
        try:
            try:
                await admin.create_topics(
                    [NewTopic(name=KAFKA_TOPIC, num_partitions=1, replication_factor=1)]
                )
            except Exception as error:
                if "TopicExists" not in str(error) and "already exists" not in str(error):
                    raise
        finally:
            await admin.close()

    async def row(self):
        async with self.sessions() as session:
            return await session.scalar(
                select(OutboxEvent).where(OutboxEvent.id == self.event_id)
            )

    async def consume_matching(self, expected: int = 1):
        consumer = AIOKafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=f"p3d-test-{uuid4()}",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        await consumer.start()
        matches = []
        deadline = asyncio.get_running_loop().time() + 15
        try:
            while len(matches) < expected and asyncio.get_running_loop().time() < deadline:
                try:
                    record = await asyncio.wait_for(consumer.getone(), timeout=1)
                except asyncio.TimeoutError:
                    continue
                if record.key and record.key.decode("utf-8") == self.message_key:
                    matches.append((record.key.decode("utf-8"), json.loads(record.value)))
        finally:
            await consumer.stop()
        self.assertEqual(len(matches), expected)
        return matches

    async def real_publisher(self, publisher_id="publisher-real"):
        return OutboxPublisher(
            session_factory=self.sessions,
            publisher_id=publisher_id,
        )

    async def test_real_kafka_publish_marks_after_ack_and_preserves_payload(self):
        publisher = await self.real_publisher()
        self.assertEqual(await publisher.run_once(), (1, 0))

        records = await self.consume_matching()
        self.assertEqual(records[0], (self.message_key, self.payload))
        persisted = await self.row()
        self.assertIsNotNone(persisted.published_at)
        self.assertIsNone(persisted.locked_by)
        self.assertIsNone(persisted.locked_until)
        self.assertEqual(persisted.attempts, 0)

    async def test_already_published_event_is_not_polled_again(self):
        publisher = await self.real_publisher()
        self.assertEqual(await publisher.run_once(), (1, 0))
        self.assertEqual(await publisher.run_once(), (0, 0))

    async def test_publish_failure_keeps_event_pending_and_sanitizes_error(self):
        publisher = await self.real_publisher("publisher-failing")
        self.assertEqual(await publisher.run_once(producer=FailingProducer()), (0, 1))
        persisted = await self.row()
        self.assertIsNone(persisted.published_at)
        self.assertEqual(persisted.attempts, 1)
        self.assertIn("<redacted>", persisted.last_error)
        self.assertNotIn("secret-token", persisted.last_error)
        self.assertNotIn("database-secret", persisted.last_error)

    async def test_unavailable_kafka_keeps_event_pending(self):
        producer = AIOKafkaProducer(
            bootstrap_servers="kafka:19092",
            acks="all",
            enable_idempotence=True,
            request_timeout_ms=750,
            retry_backoff_ms=100,
        )
        try:
            publisher = OutboxPublisher(
                session_factory=self.sessions,
                producer_factory=lambda: producer,
                publisher_id="publisher-unavailable",
            )
            self.assertEqual(await publisher.run_once(), (0, 1))
        finally:
            await producer.stop()
        persisted = await self.row()
        self.assertIsNone(persisted.published_at)
        self.assertEqual(persisted.attempts, 1)

    async def test_recovery_publishes_previously_failed_event(self):
        failing = await self.real_publisher("publisher-failing")
        self.assertEqual(await failing.run_once(producer=FailingProducer()), (0, 1))
        recovering = await self.real_publisher("publisher-recovering")
        self.assertEqual(await recovering.run_once(), (1, 0))
        await self.consume_matching()

    async def test_two_publishers_claim_once_and_expired_lease_is_recoverable(self):
        first = await self.real_publisher("publisher-one")
        second = await self.real_publisher("publisher-two")
        claims = await asyncio.gather(first.claim_pending(), second.claim_pending())
        self.assertEqual(sorted(len(claim) for claim in claims), [0, 1])

        async with self.sessions() as session:
            await session.execute(
                update(OutboxEvent)
                .where(OutboxEvent.id == self.event_id)
                .values(locked_until=datetime.now(timezone.utc) - timedelta(seconds=1))
            )
            await session.commit()

        recovered = await second.claim_pending()
        self.assertEqual(len(recovered), 1)

    async def test_ack_before_mark_window_can_redeliver_same_event_id(self):
        first = await self.real_publisher("publisher-crashed")
        claimed = await first.claim_pending()
        self.assertEqual(len(claimed), 1)

        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            acks="all",
            enable_idempotence=True,
        )
        await producer.start()
        try:
            event = claimed[0]
            await producer.send_and_wait(
                KAFKA_TOPIC,
                key=event.message_key.encode("utf-8"),
                value=json.dumps(event.payload, sort_keys=True, separators=(",", ":")).encode(),
            )
        finally:
            await producer.stop()

        async with self.sessions() as session:
            await session.execute(
                update(OutboxEvent)
                .where(OutboxEvent.id == self.event_id)
                .values(locked_until=datetime.now(timezone.utc) - timedelta(seconds=1))
            )
            await session.commit()

        second = await self.real_publisher("publisher-restarted")
        self.assertEqual(await second.run_once(), (1, 0))
        records = await self.consume_matching(expected=2)
        self.assertEqual(records[0][1]["event_id"], records[1][1]["event_id"])


if __name__ == "__main__":
    unittest.main()
