import os
import sys
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
from fastapi import HTTPException


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "services", "transactions-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/bankcore_test_transactions")
os.environ.setdefault("REDIS_URL", "redis://unused")
os.environ.setdefault("JWT_ACTIVE_KID", "test-runner")
os.environ.setdefault("AUTH_SERVICE_TOKEN", "test-runner")


class _FakeClient:
    def __init__(self, responses):
        self.responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, *_args, **_kwargs):
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class _ClientFactory:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0

    def __call__(self, **_kwargs):
        self.calls += 1
        return _FakeClient(self.responses)


def _response(status_code, body=None):
    return httpx.Response(
        status_code,
        json=body,
        request=httpx.Request("POST", "http://risk/internal/risk/assessments"),
    )


class RiskResilienceTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        import app.risk_client as risk_client

        cls.risk_client = risk_client

    async def asyncSetUp(self):
        self.breaker = self.risk_client.RiskCircuitBreaker(failure_threshold=3, open_seconds=60)
        self.breaker_patch = patch.object(self.risk_client, "circuit_breaker", self.breaker)
        self.breaker_patch.start()
        self.token_patch = patch.object(
            self.risk_client,
            "get_internal_service_token",
            AsyncMock(return_value="risk-token"),
        )
        self.token_patch.start()
        self.invalidate_patch = patch.object(
            self.risk_client,
            "invalidate_internal_service_token",
            AsyncMock(),
        )
        self.invalidate_patch.start()

    async def asyncTearDown(self):
        self.invalidate_patch.stop()
        self.token_patch.stop()
        self.breaker_patch.stop()

    def request_kwargs(self):
        return {
            "transaction_id": uuid4(),
            "source_account_id": uuid4(),
            "destination_account_id": uuid4(),
            "amount_cents": 1000,
            "operation_type": "PIX",
        }

    def approved(self):
        return _response(
            200,
            {
                "assessment_id": str(uuid4()),
                "decision": "APPROVED",
                "rules_version": "risk-rules-v1",
            },
        )

    async def assess(self, responses, **overrides):
        factory = _ClientFactory(list(responses))
        with patch.object(self.risk_client.httpx, "AsyncClient", factory), patch.object(
            self.risk_client.settings,
            "RISK_RETRY_COUNT",
            overrides.get("retry_count", 1),
        ), patch.object(
            self.risk_client.settings,
            "RISK_RETRY_DELAY_SECONDS",
            0,
        ):
            result = await self.risk_client.assess_transaction_risk(**self.request_kwargs())
        return result, factory

    async def test_timeout_retries_once_then_succeeds(self):
        timeout = httpx.ReadTimeout("risk timeout", request=httpx.Request("POST", "http://risk"))
        result, client = await self.assess([timeout, self.approved()])

        self.assertEqual(result.decision, "APPROVED")
        self.assertEqual(client.calls, 2)

    async def test_503_retries_once_then_succeeds(self):
        result, client = await self.assess([_response(503), self.approved()])

        self.assertEqual(result.rules_version, "risk-rules-v1")
        self.assertEqual(client.calls, 2)

    async def test_non_transient_4xx_is_not_retried(self):
        with self.assertRaises(HTTPException) as context:
            await self.assess([_response(400)])

        self.assertEqual(context.exception.status_code, 503)

    async def test_conflict_is_not_retried_and_is_explicit(self):
        with self.assertRaises(HTTPException) as context:
            await self.assess([_response(409)])

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(context.exception.detail, "RISK_ASSESSMENT_CONFLICT")

    async def test_invalid_response_fails_closed(self):
        with self.assertRaises(HTTPException) as context:
            await self.assess([_response(200, {"decision": "APPROVED"})])

        self.assertEqual(context.exception.status_code, 503)

    async def test_expired_internal_token_is_refreshed_once(self):
        result, client = await self.assess([_response(401), self.approved()])

        self.assertEqual(result.decision, "APPROVED")
        self.assertEqual(client.calls, 2)
        self.risk_client.invalidate_internal_service_token.assert_awaited_once_with(scope="risk:assess")

    async def test_circuit_opens_after_transient_failures_and_recovers(self):
        breaker = self.risk_client.RiskCircuitBreaker(failure_threshold=2, open_seconds=60)
        with patch.object(self.risk_client, "circuit_breaker", breaker), patch.object(
            self.risk_client.settings, "RISK_RETRY_COUNT", 0
        ):
            for _ in range(2):
                with self.assertRaises(HTTPException):
                    await self.assess([_response(503)], retry_count=0)

            factory = _ClientFactory([self.approved()])
            with patch.object(self.risk_client.httpx, "AsyncClient", factory):
                with self.assertRaises(HTTPException) as context:
                    await self.risk_client.assess_transaction_risk(**self.request_kwargs())

            self.assertEqual(context.exception.detail, "RISK_CIRCUIT_OPEN")
            self.assertEqual(factory.calls, 0)

    async def test_circuit_half_open_closes_after_recovery(self):
        breaker = self.risk_client.RiskCircuitBreaker(failure_threshold=1, open_seconds=0)
        with patch.object(self.risk_client, "circuit_breaker", breaker), patch.object(
            self.risk_client.settings, "RISK_RETRY_COUNT", 0
        ):
            with self.assertRaises(HTTPException):
                await self.assess([_response(503)], retry_count=0)

            result, client = await self.assess([self.approved()], retry_count=0)

        self.assertEqual(result.decision, "APPROVED")
        self.assertEqual(client.calls, 1)


if __name__ == "__main__":
    unittest.main()
