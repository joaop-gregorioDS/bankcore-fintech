import asyncio
import os
import sys
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.getenv("BANKCORE_TEST_DATABASE_URL")


@unittest.skipUnless(
    TEST_DATABASE_URL,
    "requires BANKCORE_TEST_DATABASE_URL pointing to an isolated PostgreSQL database",
)
class PostgresIdempotencyIntegrationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "services/transactions-service"))
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
        os.environ.setdefault("REDIS_URL", "redis://unused")
        os.environ.setdefault("JWT_SECRET_KEY", "integration-test-only")

        from app.database import Base
        from app.idempotency import build_request_fingerprint
        from app.models import IdempotencyRecord, LedgerTransaction
        from app.services.ledger import _claim_idempotency, _complete_idempotency
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        cls.Base = Base
        cls.build_request_fingerprint = staticmethod(build_request_fingerprint)
        cls.async_sessionmaker = staticmethod(async_sessionmaker)
        cls.create_async_engine = staticmethod(create_async_engine)
        cls.AsyncSession = AsyncSession
        cls.IdempotencyRecord = IdempotencyRecord
        cls.LedgerTransaction = LedgerTransaction
        cls.claim = staticmethod(_claim_idempotency)
        cls.complete = staticmethod(_complete_idempotency)

    async def asyncSetUp(self):
        self.engine = self.create_async_engine(TEST_DATABASE_URL, echo=False)
        self.AsyncSessionLocal = self.async_sessionmaker(
            self.engine,
            class_=self.AsyncSession,
            expire_on_commit=False,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(self.Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    def scope(self, *, user_id=None, account_id=None, operation_type="TRANSFER", key=None):
        return {
            "user_id": user_id or uuid4(),
            "account_id": account_id or uuid4(),
            "operation_type": operation_type,
            "idempotency_key": key or f"integration-{uuid4()}",
        }

    def fingerprint(self, scope, *, amount_cents=100, destination_account_id=None, description="test"):
        return self.build_request_fingerprint(
            **scope,
            amount_cents=amount_cents,
            destination_account_id=destination_account_id,
            description=description,
        )

    async def make_completed(self, session, scope, *, amount_cents=100, description="test"):
        fingerprint = self.fingerprint(scope, amount_cents=amount_cents, description=description)
        existing, record = await self.claim(session, **scope, fingerprint=fingerprint)
        self.assertIsNone(existing)
        transaction = self.LedgerTransaction(
            idempotency_key=scope["idempotency_key"],
            amount_cents=amount_cents,
            transaction_type=scope["operation_type"],
            status="COMPLETED",
        )
        session.add(transaction)
        await session.flush()
        self.complete(record, transaction)
        await session.commit()
        return transaction, fingerprint

    async def test_first_request_and_identical_replay_return_same_transaction(self):
        scope = self.scope()
        async with self.AsyncSessionLocal() as session:
            transaction, fingerprint = await self.make_completed(session, scope)
            replay, _ = await self.claim(session, **scope, fingerprint=fingerprint)
            self.assertEqual(replay.id, transaction.id)

    async def test_payload_change_returns_409(self):
        scope = self.scope()
        async with self.AsyncSessionLocal() as session:
            _, fingerprint = await self.make_completed(session, scope, amount_cents=100)
            different = self.fingerprint(scope, amount_cents=5000)
            self.assertNotEqual(fingerprint, different)
            with self.assertRaises(HTTPException) as context:
                await self.claim(session, **scope, fingerprint=different)
            self.assertEqual(context.exception.status_code, 409)

    async def test_other_scope_is_independent_and_does_not_reveal_original(self):
        scope = self.scope()
        other_account = self.scope(user_id=scope["user_id"], key=scope["idempotency_key"])
        async with self.AsyncSessionLocal() as session:
            _, fingerprint = await self.make_completed(session, scope)
            other_fingerprint = self.fingerprint(other_account)
            replay, record = await self.claim(session, **other_account, fingerprint=other_fingerprint)
            self.assertIsNone(replay)
            self.assertEqual(record.account_id, other_account["account_id"])
            self.assertNotEqual(record.request_fingerprint, fingerprint)
            await session.rollback()

    async def test_other_user_and_operation_have_independent_namespaces(self):
        scope = self.scope()
        other_user = self.scope(account_id=scope["account_id"], key=scope["idempotency_key"])
        other_operation = self.scope(
            user_id=scope["user_id"],
            account_id=scope["account_id"],
            operation_type="DEPOSIT",
            key=scope["idempotency_key"],
        )
        async with self.AsyncSessionLocal() as session:
            await self.make_completed(session, scope)
            for independent_scope in (other_user, other_operation):
                replay, _ = await self.claim(
                    session,
                    **independent_scope,
                    fingerprint=self.fingerprint(independent_scope),
                )
                self.assertIsNone(replay)
                await session.rollback()

    async def test_rollback_removes_processing_record(self):
        scope = self.scope()
        async with self.AsyncSessionLocal() as first:
            _, record = await self.claim(
                first,
                **scope,
                fingerprint=self.fingerprint(scope),
            )
            self.assertIsNotNone(record)
            await first.rollback()

        async with self.AsyncSessionLocal() as retry:
            replay, record = await self.claim(
                retry,
                **scope,
                fingerprint=self.fingerprint(scope),
            )
            self.assertIsNone(replay)
            self.assertEqual(record.status, "PROCESSING")
            await retry.rollback()

    async def test_concurrent_same_scope_allows_only_one_claim(self):
        scope = self.scope()
        fingerprint = self.fingerprint(scope)
        first = self.AsyncSessionLocal()
        second = self.AsyncSessionLocal()
        try:
            first_result = await self.claim(first, **scope, fingerprint=fingerprint)
            second_task = asyncio.create_task(
                self.claim(second, **scope, fingerprint=fingerprint)
            )
            await asyncio.sleep(0.05)
            await first.commit()
            with self.assertRaises(HTTPException) as context:
                await second_task
            self.assertEqual(context.exception.status_code, 409)
        finally:
            await first.rollback()
            await second.rollback()
            await first.close()
            await second.close()
        self.assertIsNone(first_result[0])

if __name__ == "__main__":
    unittest.main()
