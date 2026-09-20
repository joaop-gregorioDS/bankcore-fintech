import asyncio
import os
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from fastapi import HTTPException

from environment import validate_test_database_url

ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.getenv("BANKCORE_TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "requires BANKCORE_TEST_DATABASE_URL")
class PixRiskGatePostgresTests(unittest.IsolatedAsyncioTestCase):
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
        from app.models import Account, IdempotencyRecord, LedgerEntry, LedgerTransaction

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

    async def asyncSetUp(self):
        self.engine = self.create_async_engine(TEST_DATABASE_URL, echo=False)
        self.sessions = self.async_sessionmaker(self.engine, class_=self.AsyncSession, expire_on_commit=False)
        async with self.sessions() as session:
            await session.execute(self.LedgerEntry.__table__.delete())
            await session.execute(self.IdempotencyRecord.__table__.delete())
            await session.execute(self.LedgerTransaction.__table__.delete())
            await session.execute(self.Account.__table__.delete())
            self.user_id = uuid4()
            self.source_id = uuid4()
            self.destination_id = uuid4()
            session.add_all(
                [
                    self.Account(id=self.source_id, user_id=self.user_id, account_number=f"src-{uuid4().hex[:16]}", balance_cents=100_000),
                    self.Account(id=self.destination_id, user_id=uuid4(), account_number=f"dst-{uuid4().hex[:16]}", balance_cents=0),
                ]
            )
            await session.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    def payload(self, *, amount="10.00", key="p2f-key"):
        from app.schemas import PixTransferRequest

        return PixTransferRequest(
            source_account_id=self.source_id,
            destination_key=str(self.destination_id),
            amount_reais=Decimal(amount),
            idempotency_key=key,
        )

    def risk(self, decision="APPROVED"):
        from app.risk_client import RiskAssessment

        return RiskAssessment(uuid4(), decision, "risk-rules-v1")

    async def invoke(self, payload, risk_result=None, risk_side_effect=None, transfer_side_effect=None):
        from app.routes.transactions import _resolve_pix_destination, pix_transfer

        async with self.sessions() as session:
            resolver = AsyncMock(return_value=self.destination_id)
            assessor = AsyncMock(return_value=risk_result or self.risk())
            if risk_side_effect is not None:
                assessor.side_effect = risk_side_effect
            with patch("app.routes.transactions._resolve_pix_destination", resolver), patch(
                "app.routes.transactions.assess_transaction_risk", assessor
            ):
                if transfer_side_effect is None:
                    result = await pix_transfer(
                        payload,
                        db=session,
                        current_user={"sub": str(self.user_id)},
                    )
                else:
                    with patch(
                        "app.routes.transactions.transfer_funds",
                        AsyncMock(side_effect=transfer_side_effect),
                    ):
                        result = await pix_transfer(
                            payload,
                            db=session,
                            current_user={"sub": str(self.user_id)},
                        )
            return result, assessor

    async def counts(self):
        from sqlalchemy import func, select

        async with self.sessions() as session:
            transactions = await session.scalar(select(func.count()).select_from(self.LedgerTransaction))
            entries = await session.scalar(select(func.count()).select_from(self.LedgerEntry))
            return transactions, entries

    async def test_approved_creates_one_transaction_and_two_entries_with_audit_link(self):
        result, _ = await self.invoke(self.payload())

        self.assertEqual(result.status, "COMPLETED")
        transactions, entries = await self.counts()
        self.assertEqual((transactions, entries), (1, 2))
        async with self.sessions() as session:
            tx = await session.get(self.LedgerTransaction, result.transaction_id)
            self.assertEqual(tx.risk_decision, "APPROVED")
            self.assertEqual(tx.risk_rules_version, "risk-rules-v1")
            self.assertIsNotNone(tx.risk_assessment_id)

    async def test_review_and_rejected_never_create_ledger_entries(self):
        for decision, expected_status in (("REVIEW", 409), ("REJECTED", 422)):
            with self.subTest(decision=decision):
                with self.assertRaises(HTTPException) as context:
                    await self.invoke(self.payload(key=f"{decision}-key"), risk_result=self.risk(decision))
                self.assertEqual(context.exception.status_code, expected_status)
                self.assertEqual(await self.counts(), (0, 0))

    async def test_risk_failure_is_fail_closed(self):
        with self.assertRaises(HTTPException) as context:
            await self.invoke(
                self.payload(),
                risk_side_effect=HTTPException(status_code=504, detail="RISK_UNAVAILABLE"),
            )

        self.assertEqual(context.exception.status_code, 504)
        self.assertEqual(await self.counts(), (0, 0))

    async def test_replay_keeps_same_transaction_and_risk_id(self):
        first, first_assessor = await self.invoke(self.payload())
        second, second_assessor = await self.invoke(self.payload())

        self.assertEqual(first.transaction_id, second.transaction_id)
        self.assertEqual(
            first_assessor.await_args.kwargs["transaction_id"],
            second_assessor.await_args.kwargs["transaction_id"],
        )
        self.assertEqual(await self.counts(), (1, 2))

    async def test_approved_then_ledger_failure_retries_with_same_transaction_id(self):
        from app.routes import transactions as transaction_routes

        assessment = self.risk()
        calls = 0
        real_transfer = transaction_routes.transfer_funds

        async def fail_once_then_commit(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise HTTPException(status_code=503, detail="LEDGER_UNAVAILABLE")
            return await real_transfer(**kwargs)

        with self.assertRaises(HTTPException) as context:
            await self.invoke(
                self.payload(),
                risk_result=assessment,
                transfer_side_effect=fail_once_then_commit,
            )
        self.assertEqual(context.exception.status_code, 503)

        result, assessor = await self.invoke(
            self.payload(),
            risk_result=assessment,
            transfer_side_effect=fail_once_then_commit,
        )

        self.assertEqual(calls, 2)
        self.assertEqual(
            assessor.await_args.kwargs["transaction_id"],
            transaction_routes.build_transaction_id(
                user_id=self.user_id,
                account_id=self.source_id,
                operation_type="TRANSFER",
                idempotency_key="p2f-key",
            ),
        )
        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(await self.counts(), (1, 2))

    async def test_payload_change_with_same_key_is_rejected_before_ledger(self):
        await self.invoke(self.payload(amount="10.00"))

        async def divergent_risk(**_kwargs):
            raise HTTPException(status_code=409, detail="assessment_conflict")

        with self.assertRaises(HTTPException) as context:
            await self.invoke(self.payload(amount="50.00"), risk_side_effect=divergent_risk)

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(await self.counts(), (1, 2))

    async def test_ten_concurrent_identical_requests_create_one_ledger(self):
        from app.routes.transactions import _resolve_pix_destination, pix_transfer

        async def one_request():
            async with self.sessions() as session:
                with patch(
                    "app.routes.transactions._resolve_pix_destination",
                    AsyncMock(return_value=self.destination_id),
                ), patch(
                    "app.routes.transactions.assess_transaction_risk",
                    AsyncMock(return_value=self.risk()),
                ):
                    return await pix_transfer(
                        self.payload(),
                        db=session,
                        current_user={"sub": str(self.user_id)},
                    )

        results = await asyncio.gather(*(one_request() for _ in range(10)))
        self.assertEqual({result.transaction_id for result in results}, {results[0].transaction_id})
        self.assertEqual(await self.counts(), (1, 2))

    async def test_risk_is_called_after_preflight_session_is_closed(self):
        observed = []

        async def assert_no_transaction(**_kwargs):
            observed.append(True)
            return self.risk()

        await self.invoke(self.payload(), risk_side_effect=assert_no_transaction)
        self.assertEqual(observed, [True])


if __name__ == "__main__":
    unittest.main()
