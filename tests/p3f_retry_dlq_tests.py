import asyncio
import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from environment import validate_test_database_url


ROOT = Path(__file__).resolve().parents[1]
TX_DATABASE_URL = os.environ["BANKCORE_TEST_DATABASE_URL"]
AUDIT_DATABASE_URL = os.environ["AUDIT_TEST_DATABASE_URL"]
KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
KAFKA_TOPIC = os.environ["KAFKA_TOPIC"]
RETRY_TOPIC = os.environ.get("KAFKA_RETRY_TOPIC", f"{KAFKA_TOPIC}.retry")
DLQ_TOPIC = os.environ.get("KAFKA_DLQ_TOPIC", f"{KAFKA_TOPIC}.dlq")
validate_test_database_url(TX_DATABASE_URL)
validate_test_database_url(AUDIT_DATABASE_URL)
sys.path.insert(0, str(ROOT / "services/audit-service"))
os.environ["AUDIT_DATABASE_URL"] = AUDIT_DATABASE_URL

from audit_app.consumer import AuditConsumer  # noqa: E402
from audit_app.models import AuditEvent  # noqa: E402


class FailingSessionFactory:
    def __call__(self):
        return self

    async def __aenter__(self):
        raise RuntimeError("audit database unavailable password=not-a-real-secret")

    async def __aexit__(self, *args):
        return False


class FailingProducer:
    async def send_and_wait(self, *args, **kwargs):
        raise RuntimeError("broker unavailable token=not-a-real-token")


class OffsetSpy:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


def event_payload(event_id=None, transaction_id=None):
    return {
        "event_id": str(event_id or uuid4()),
        "event_type": "transaction.completed",
        "event_version": 1,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "producer": "transactions-service",
        "correlation_id": str(uuid4()),
        "data": {
            "transaction_id": str(transaction_id or uuid4()),
            "source_account_id": str(uuid4()),
            "destination_account_id": str(uuid4()),
            "amount_cents": 1000,
            "operation_type": "PIX",
            "risk_assessment_id": str(uuid4()),
            "risk_rules_version": "risk-rules-v1",
        },
    }


def record_from_payload(payload, *, topic=KAFKA_TOPIC, headers=None, partition=0, offset=0):
    encoded = payload if isinstance(payload, bytes) else json.dumps(payload, sort_keys=True).encode("utf-8")
    parsed = json.loads(encoded)
    return SimpleNamespace(
        topic=topic,
        partition=partition,
        offset=offset,
        key=parsed.get("data", {}).get("transaction_id", "").encode("utf-8") or None,
        value=encoded,
        headers=headers or [],
    )


def headers_as_dict(record):
    return {
        key: value.decode("utf-8") if isinstance(value, bytes) else str(value)
        for key, value in record.headers
    }


class RetryDlqKafkaTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.audit_engine = create_async_engine(AUDIT_DATABASE_URL, echo=False)
        self.audit_sessions = async_sessionmaker(
            self.audit_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        await self.ensure_topics()
        async with self.audit_sessions() as session:
            await session.execute(AuditEvent.__table__.delete())
            await session.commit()
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            acks="all",
            enable_idempotence=True,
        )
        await self.producer.start()

    async def asyncTearDown(self):
        await self.producer.stop()
        await self.audit_engine.dispose()

    async def ensure_topics(self):
        admin = AIOKafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
        await admin.start()
        try:
            topics = [
                NewTopic(name=KAFKA_TOPIC, num_partitions=3, replication_factor=1),
                NewTopic(name=RETRY_TOPIC, num_partitions=3, replication_factor=1),
                NewTopic(name=DLQ_TOPIC, num_partitions=3, replication_factor=1),
            ]
            try:
                await admin.create_topics(topics)
            except Exception as error:
                if "TopicExists" not in str(error) and "already exists" not in str(error):
                    raise
        finally:
            await admin.close()

    async def audit_count(self):
        async with self.audit_sessions() as session:
            return await session.scalar(select(func.count()).select_from(AuditEvent))

    async def consume_one(self, topic, group_id=None):
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id or f"p3f-read-{uuid4()}",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        await consumer.start()
        try:
            return await asyncio.wait_for(consumer.getone(), timeout=15)
        finally:
            await consumer.stop()

    async def consume_value(self, topic, expected_value):
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=f"p3f-match-{uuid4()}",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        await consumer.start()
        try:
            deadline = asyncio.get_running_loop().time() + 15
            while asyncio.get_running_loop().time() < deadline:
                try:
                    record = await asyncio.wait_for(consumer.getone(), timeout=1)
                except asyncio.TimeoutError:
                    continue
                if record.value == expected_value:
                    return record
        finally:
            await consumer.stop()
        self.fail(f"Expected payload was not found on topic {topic}")

    async def test_invalid_event_goes_directly_to_dlq(self):
        source = OffsetSpy()
        consumer = AuditConsumer(session_factory=self.audit_sessions)
        record = record_from_payload(b'{"event_id":"broken"}')

        result = await consumer.handle_record(record, source, self.producer)

        self.assertEqual(result, "dlq")
        self.assertEqual(source.commits, 1)
        dlq_record = await self.consume_value(DLQ_TOPIC, record.value)
        self.assertEqual(dlq_record.value, record.value)
        headers = headers_as_dict(dlq_record)
        self.assertEqual(headers["failure-class"], "PERMANENT")
        self.assertNotIn("Authorization", headers.get("failure-reason", ""))
        self.assertEqual(await self.audit_count(), 0)

    async def test_transient_failure_retries_then_succeeds_without_payload_change(self):
        source = OffsetSpy()
        payload = json.dumps(event_payload(), sort_keys=True).encode("utf-8")
        record = record_from_payload(payload)
        failing = AuditConsumer(session_factory=FailingSessionFactory())

        result = await failing.handle_record(record, source, self.producer)

        self.assertEqual(result, "retry")
        self.assertEqual(source.commits, 1)
        retry_record = await self.consume_value(RETRY_TOPIC, payload)
        self.assertEqual(retry_record.value, payload)
        retry_headers = headers_as_dict(retry_record)
        self.assertEqual(retry_headers["retry-count"], "1")
        self.assertEqual(retry_headers["failure-class"], "TRANSIENT")
        self.assertNotIn("not-a-real-secret", retry_headers["failure-reason"])

        recovered = AuditConsumer(session_factory=self.audit_sessions)
        retry_source = OffsetSpy()
        self.assertEqual(
            await recovered.handle_record(retry_record, retry_source, self.producer),
            "processed",
        )
        self.assertEqual(retry_source.commits, 1)
        self.assertEqual(await self.audit_count(), 1)
        await recovered.handle_record(retry_record, OffsetSpy(), self.producer)
        self.assertEqual(await self.audit_count(), 1)

    async def test_retry_limit_routes_transient_failure_to_dlq(self):
        source = OffsetSpy()
        record = record_from_payload(
            event_payload(),
            topic=RETRY_TOPIC,
            headers=[("retry-count", b"3")],
        )
        failing = AuditConsumer(session_factory=FailingSessionFactory())

        self.assertEqual(await failing.handle_record(record, source, self.producer), "dlq")
        self.assertEqual(source.commits, 1)
        dlq_record = await self.consume_value(DLQ_TOPIC, record.value)
        headers = headers_as_dict(dlq_record)
        self.assertEqual(headers["failure-class"], "TRANSIENT")
        self.assertEqual(headers["retry-count"], "3")

    async def test_failure_publish_error_does_not_advance_source_offset(self):
        source = OffsetSpy()
        record = record_from_payload(b'{"invalid":true}')
        failing = AuditConsumer(session_factory=self.audit_sessions)

        with self.assertRaisesRegex(RuntimeError, "broker unavailable"):
            await failing.handle_record(record, source, FailingProducer())
        self.assertEqual(source.commits, 0)

    async def test_poison_message_does_not_block_following_valid_message(self):
        source = OffsetSpy()
        consumer = AuditConsumer(session_factory=self.audit_sessions)
        poison = record_from_payload(b'{"invalid":true}', offset=1)
        valid = record_from_payload(event_payload(), offset=2)

        self.assertEqual(await consumer.handle_record(poison, source, self.producer), "dlq")
        self.assertEqual(await consumer.handle_record(valid, source, self.producer), "processed")
        self.assertEqual(source.commits, 2)
        self.assertEqual(await self.audit_count(), 1)

    async def test_two_consumers_distribute_one_hundred_events_across_three_partitions(self):
        payloads = [event_payload() for _ in range(100)]
        for payload in payloads:
            await self.producer.send_and_wait(
                KAFKA_TOPIC,
                key=payload["data"]["transaction_id"].encode("utf-8"),
                value=json.dumps(payload, sort_keys=True).encode("utf-8"),
            )

        group_id = "bankcore-audit-v1"
        consumers = [
            AIOKafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
            )
            for _ in range(2)
        ]
        for consumer in consumers:
            await consumer.start()
        try:
            deadline = asyncio.get_running_loop().time() + 10
            while (
                len(consumers[0].assignment()) + len(consumers[1].assignment()) < 3
                and asyncio.get_running_loop().time() < deadline
            ):
                await asyncio.sleep(0.1)
            self.assertGreaterEqual(len(consumers[0].assignment()), 1)
            self.assertGreaterEqual(len(consumers[1].assignment()), 1)

            handlers = [AuditConsumer(session_factory=self.audit_sessions) for _ in consumers]
            counts = [0, 0]
            done = asyncio.Event()

            async def worker(index):
                while not done.is_set():
                    batches = await consumers[index].getmany(timeout_ms=500, max_records=20)
                    for batch in batches.values():
                        for record in batch:
                            await handlers[index].handle_record(
                                record,
                                consumers[index],
                                self.producer,
                            )
                            counts[index] += 1
                            if sum(counts) >= len(payloads):
                                done.set()
                                return

            await asyncio.wait_for(
                asyncio.gather(worker(0), worker(1)),
                timeout=30,
            )
            self.assertEqual(sum(counts), 100)
            self.assertGreater(counts[0], 0)
            self.assertGreater(counts[1], 0)
            self.assertEqual(await self.audit_count(), 100)
        finally:
            for consumer in consumers:
                await consumer.stop()


if __name__ == "__main__":
    unittest.main()
