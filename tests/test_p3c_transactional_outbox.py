import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException

from environment import validate_test_database_url


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.getenv("BANKCORE_TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "requires BANKCORE_TEST_DATABASE_URL")
class TransactionalOutboxPostgresTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        validate_test_database_url(TEST_DATABASE_URL)
        sys.path.insert(0, str(ROOT / "services/transactions-service"))
        for module_name in list(sys.modules):
            if module_name == "app" or module_name.startswith("app."):
                del sys.modules[module_name]
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
        os.environ.setdefault("REDIS_URL", "redis://unused")
        os.environ.setdefault("JWT_ACTIVE_KID", "integration-test")
        os.environ.setdefault("AUTH_SERVICE_TOKEN", "integration-test-only")

        from alembic import command
        from alembic.config import Config
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.models import Account, IdempotencyRecord, LedgerEntry, LedgerTransaction, OutboxEvent
        from app.services.ledger import transfer_funds

        migration_config = Config(str(ROOT / "infra/postgres/alembic/transactions/alembic.ini"))
        migration_config.set_main_option(
            "script_location",
            str(ROOT / "infra/postgres/alembic/transactions").replace("%", "%%"),
        )
        migration_config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL.replace("%", "%%"))
        command.upgrade(migration_config, "head")

        cls.AsyncSession = AsyncSession
        cls.async_sessionmaker = staticmethod(async_sessionmaker)
        cls.create_async_engine = staticmethod(create_async_engine)
        cls.Account = Account
        cls.IdempotencyRecord = IdempotencyRecord
        cls.LedgerEntry = LedgerEntry
        cls.LedgerTransaction = LedgerTransaction
        cls.OutboxEvent = OutboxEvent
        cls.transfer_funds = staticmethod(transfer_funds)

    async def asyncSetUp(self):
        self.engine = self.create_async_engine(TEST_DATABASE_URL, echo=False)
        self.sessions = self.async_sessionmaker(
            self.engine,
            class_=self.AsyncSession,
            expire_on_commit=False,
        )
        self.user_id = uuid4()
        self.source_id = uuid4()
        self.destination_id = uuid4()
        self.transaction_id = uuid4()
        self.risk_assessment_id = uuid4()
        async with self.sessions() as session:
            await session.execute(self.OutboxEvent.__table__.delete())
            await session.execute(self.LedgerEntry.__table__.delete())
            await session.execute(self.IdempotencyRecord.__table__.delete())
            await session.execute(self.LedgerTransaction.__table__.delete())
            await session.execute(self.Account.__table__.delete())
            session.add_all(
                [
                    self.Account(
                        id=self.source_id,
                        user_id=self.user_id,
                        account_number=f"src-{uuid4().hex[:16]}",
                        balance_cents=100_000,
                    ),
                    self.Account(
                        id=self.destination_id,
                        user_id=uuid4(),
                        account_number=f"dst-{uuid4().hex[:16]}",
                        balance_cents=0,
                    ),
                ]
            )
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def transfer(self, *, key="p3c-key", amount_cents=1_000, **overrides):
        arguments = {
            "user_id": self.user_id,
            "source_account_id": self.source_id,
            "destination_account_id": self.destination_id,
            "amount_cents": amount_cents,
            "idempotency_key": key,
            "description": "P3-C test transfer",
            "transaction_id": self.transaction_id,
            "risk_assessment_id": self.risk_assessment_id,
            "risk_decision": "APPROVED",
            "risk_rules_version": "risk-rules-v1",
        }
        arguments.update(overrides)
        async with self.sessions() as session:
            return await self.transfer_funds(db=session, **arguments)

    async def counts(self):
        from sqlalchemy import func, select

        async with self.sessions() as session:
            transactions = await session.scalar(select(func.count()).select_from(self.LedgerTransaction))
            entries = await session.scalar(select(func.count()).select_from(self.LedgerEntry))
            outbox = await session.scalar(select(func.count()).select_from(self.OutboxEvent))
            return transactions, entries, outbox

    async def outbox_for(self, transaction_id):
        from sqlalchemy import select

        async with self.sessions() as session:
            return (
                await session.execute(
                    select(self.OutboxEvent).where(self.OutboxEvent.aggregate_id == transaction_id)
                )
            ).scalars().all()

    async def test_approved_transfer_commits_one_ledger_and_one_contract_event(self):
        transaction = await self.transfer()
        self.assertEqual(await self.counts(), (1, 2, 1))

        events = await self.outbox_for(transaction.id)
        self.assertEqual(len(events), 1)
        event = events[0]
        payload = event.payload
        self.assertEqual(str(event.id), payload["event_id"])
        self.assertEqual(event.aggregate_type, "transaction")
        self.assertEqual(event.aggregate_id, transaction.id)
        self.assertEqual(event.message_key, str(transaction.id))
        self.assertEqual(event.event_type, "transaction.completed")
        self.assertEqual(event.event_version, 1)
        self.assertIsNone(event.published_at)
        self.assertEqual(event.attempts, 0)
        self.assertEqual(payload["event_type"], "transaction.completed")
        self.assertEqual(payload["event_version"], 1)
        self.assertEqual(payload["producer"], "transactions-service")
        self.assertEqual(payload["data"]["transaction_id"], str(transaction.id))
        self.assertEqual(payload["data"]["amount_cents"], 1_000)
        self.assertEqual(payload["data"]["operation_type"], "PIX")
        self.assertNotIn("email", json.dumps(payload))
        self.assertNotIn("pix_key", json.dumps(payload))
        self.assertNotIn("password", json.dumps(payload))

    async def test_risk_review_rejected_or_unavailable_creates_no_outbox(self):
        for decision, assessment_id in (
            ("REVIEW", self.risk_assessment_id),
            ("REJECTED", self.risk_assessment_id),
            ("APPROVED", None),
        ):
            with self.subTest(decision=decision):
                with self.assertRaises(HTTPException):
                    await self.transfer(
                        key=f"{decision}-{uuid4()}",
                        risk_decision=decision,
                        risk_assessment_id=assessment_id,
                        risk_rules_version=None if assessment_id is None else "risk-rules-v1",
                    )
                self.assertEqual(await self.counts(), (0, 0, 0))

    async def test_failure_at_commit_rolls_back_ledger_entries_and_outbox(self):
        async with self.sessions() as session:
            with patch.object(session, "commit", new=AsyncMock(side_effect=RuntimeError("forced rollback"))):
                with self.assertRaisesRegex(RuntimeError, "forced rollback"):
                    await self.transfer_funds(
                        db=session,
                        user_id=self.user_id,
                        source_account_id=self.source_id,
                        destination_account_id=self.destination_id,
                        amount_cents=1_000,
                        idempotency_key="rollback-key",
                        description="P3-C rollback",
                        transaction_id=self.transaction_id,
                        risk_assessment_id=self.risk_assessment_id,
                        risk_decision="APPROVED",
                        risk_rules_version="risk-rules-v1",
                    )
        self.assertEqual(await self.counts(), (0, 0, 0))

    async def test_identical_replay_keeps_one_outbox_and_stable_event_id(self):
        first = await self.transfer()
        second = await self.transfer()
        first_event, second_event = await self.outbox_for(first.id), await self.outbox_for(second.id)
        self.assertEqual(first.id, second.id)
        self.assertEqual(first_event[0].id, second_event[0].id)
        self.assertEqual(await self.counts(), (1, 2, 1))

    async def test_payload_divergence_is_409_without_second_outbox(self):
        await self.transfer(amount_cents=1_000)
        with self.assertRaises(HTTPException) as context:
            await self.transfer(amount_cents=5_000)
        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(await self.counts(), (1, 2, 1))

    async def test_concurrent_identical_requests_create_one_event(self):
        async def one_request():
            return await self.transfer()

        results = await asyncio.gather(*(one_request() for _ in range(10)))
        self.assertEqual({result.id for result in results}, {self.transaction_id})
        self.assertEqual(await self.counts(), (1, 2, 1))

    async def test_event_contract_has_only_allowlisted_fields(self):
        transaction = await self.transfer()
        payload = (await self.outbox_for(transaction.id))[0].payload
        schema = json.loads(
            (ROOT / "docs/events/transaction.completed.v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(payload), set(schema["required"]))
        self.assertEqual(set(payload["data"]), set(schema["properties"]["data"]["required"]))
        self.assertEqual(payload["event_type"], schema["properties"]["event_type"]["const"])
        self.assertEqual(payload["event_version"], schema["properties"]["event_version"]["const"])
        self.assertEqual(payload["producer"], schema["properties"]["producer"]["const"])


if __name__ == "__main__":
    unittest.main()
