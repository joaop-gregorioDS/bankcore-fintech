import asyncio
import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from environment import validate_test_database_url


ROOT = Path(__file__).resolve().parents[1]
TX_DATABASE_URL = os.environ["BANKCORE_TEST_DATABASE_URL"]
AUDIT_DATABASE_URL = os.environ["AUDIT_TEST_DATABASE_URL"]
KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
KAFKA_TOPIC = os.environ["KAFKA_TOPIC"]
validate_test_database_url(TX_DATABASE_URL)
validate_test_database_url(AUDIT_DATABASE_URL)
sys.path.insert(0, str(ROOT / "services/transactions-service"))
sys.path.insert(0, str(ROOT / "services/audit-service"))
os.environ["DATABASE_URL"] = TX_DATABASE_URL
os.environ["AUDIT_DATABASE_URL"] = AUDIT_DATABASE_URL

from app.models import Account, IdempotencyRecord, LedgerEntry, LedgerTransaction, OutboxEvent  # noqa: E402
from app.outbox_publisher import OutboxPublisher  # noqa: E402
from app.services.ledger import transfer_funds  # noqa: E402
from audit_app.consumer import AuditConsumer  # noqa: E402
from audit_app.contracts import InvalidAuditEvent  # noqa: E402
from audit_app.models import AuditEvent  # noqa: E402


class FailingSessionFactory:
    def __call__(self):
        return self

    async def __aenter__(self):
        raise RuntimeError("audit database unavailable")

    async def __aexit__(self, *args):
        return False


class AuditConsumerKafkaTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tx_engine = create_async_engine(TX_DATABASE_URL, echo=False)
        self.tx_sessions = async_sessionmaker(
            self.tx_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.audit_engine = create_async_engine(AUDIT_DATABASE_URL, echo=False)
        self.audit_sessions = async_sessionmaker(
            self.audit_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        await self.ensure_topic()
        self.user_id = uuid4()
        self.source_id = uuid4()
        self.destination_id = uuid4()
        self.transaction_id = uuid4()
        self.risk_assessment_id = uuid4()
        async with self.tx_sessions() as session:
            await session.execute(OutboxEvent.__table__.delete())
            await session.execute(LedgerEntry.__table__.delete())
            await session.execute(IdempotencyRecord.__table__.delete())
            await session.execute(LedgerTransaction.__table__.delete())
            await session.execute(Account.__table__.delete())
            session.add_all(
                [
                    Account(
                        id=self.source_id,
                        user_id=self.user_id,
                        account_number=f"src-{uuid4().hex[:16]}",
                        balance_cents=100_000,
                    ),
                    Account(
                        id=self.destination_id,
                        user_id=uuid4(),
                        account_number=f"dst-{uuid4().hex[:16]}",
                        balance_cents=0,
                    ),
                ]
            )
            await session.commit()
        async with self.audit_sessions() as session:
            await session.execute(AuditEvent.__table__.delete())
            await session.commit()

    async def asyncTearDown(self):
        await self.tx_engine.dispose()
        await self.audit_engine.dispose()

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

    async def transfer_and_publish(self):
        async with self.tx_sessions() as session:
            transaction = await transfer_funds(
                db=session,
                user_id=self.user_id,
                source_account_id=self.source_id,
                destination_account_id=self.destination_id,
                amount_cents=1_000,
                idempotency_key=f"p3e-{uuid4()}",
                description="P3-E audit transfer",
                transaction_id=self.transaction_id,
                risk_assessment_id=self.risk_assessment_id,
                risk_decision="APPROVED",
                risk_rules_version="risk-rules-v1",
            )
        publisher = OutboxPublisher(
            session_factory=self.tx_sessions,
            publisher_id="p3e-test-publisher",
        )
        self.assertEqual(await publisher.run_once(), (1, 0))
        return transaction

    async def receive_event(self):
        consumer = AIOKafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=f"p3e-receive-{uuid4()}",
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
                payload = json.loads(record.value)
                if payload.get("data", {}).get("transaction_id") == str(self.transaction_id):
                    return record
        finally:
            await consumer.stop()
        self.fail("Published transaction event was not received from Kafka")

    async def audit_count(self):
        async with self.audit_sessions() as session:
            return await session.scalar(select(func.count()).select_from(AuditEvent))

    async def test_pix_to_publisher_to_kafka_to_audit_is_one_effect(self):
        await self.transfer_and_publish()
        record = await self.receive_event()
        audit = AuditConsumer(session_factory=self.audit_sessions)
        event = await audit.process_record(record)
        self.assertEqual(event.event_type, "transaction.completed")
        self.assertEqual(await self.audit_count(), 1)
        async with self.tx_sessions() as session:
            self.assertEqual(
                await session.scalar(select(func.count()).select_from(LedgerTransaction)), 1
            )
            self.assertEqual(await session.scalar(select(func.count()).select_from(LedgerEntry)), 2)
            self.assertEqual(await session.scalar(select(func.count()).select_from(OutboxEvent)), 1)

    async def test_same_record_twenty_times_is_one_audit_row(self):
        await self.transfer_and_publish()
        record = await self.receive_event()
        audit = AuditConsumer(session_factory=self.audit_sessions)
        for _ in range(20):
            await audit.process_record(record)
        self.assertEqual(await self.audit_count(), 1)

    async def test_replay_after_database_commit_before_offset_commit_is_idempotent(self):
        await self.transfer_and_publish()
        record = await self.receive_event()
        audit = AuditConsumer(session_factory=self.audit_sessions)
        await audit.process_record(record)
        await audit.process_record(record)
        self.assertEqual(await self.audit_count(), 1)

    async def test_malformed_event_is_rejected_without_valid_audit_row(self):
        audit = AuditConsumer(session_factory=self.audit_sessions)
        record = SimpleNamespace(value=json.dumps({"event_id": str(uuid4())}).encode())
        with self.assertRaises(InvalidAuditEvent):
            await audit.process_record(record)
        self.assertEqual(await self.audit_count(), 0)

    async def test_database_failure_does_not_commit_offset(self):
        await self.transfer_and_publish()
        record = await self.receive_event()
        commits = []

        class OffsetSpy:
            async def commit(self):
                commits.append(True)

        audit = AuditConsumer(session_factory=FailingSessionFactory())
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            await audit.process_record(record, OffsetSpy())
        self.assertEqual(commits, [])

        recovered = AuditConsumer(session_factory=self.audit_sessions)
        await recovered.process_record(record, OffsetSpy())
        self.assertEqual(await self.audit_count(), 1)

    async def test_two_consumer_instances_share_group_and_deduplicate(self):
        await self.transfer_and_publish()
        record = await self.receive_event()
        first = AuditConsumer(session_factory=self.audit_sessions, group_id="bankcore-audit-v1")
        second = AuditConsumer(session_factory=self.audit_sessions, group_id="bankcore-audit-v1")
        await first.process_record(record)
        await second.process_record(record)
        self.assertEqual(first.group_id, second.group_id)
        self.assertEqual(await self.audit_count(), 1)


if __name__ == "__main__":
    unittest.main()
