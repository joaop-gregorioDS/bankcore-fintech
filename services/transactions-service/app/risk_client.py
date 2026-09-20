import asyncio
import logging
import time
from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.config import settings
from app.internal_auth import get_internal_service_token, invalidate_internal_service_token
from common.observability import current_correlation_id, current_request_id, log_event
from common.tracing import inject_trace_headers, tracer

logger = logging.getLogger("bankcore.transactions.risk")
_tracer = tracer("bankcore.transactions")


@dataclass(frozen=True)
class RiskAssessment:
    assessment_id: UUID
    decision: str
    rules_version: str


class RiskCircuitBreaker:
    """Small process-local breaker for the synchronous Risk dependency."""

    def __init__(self, *, failure_threshold: int, open_seconds: float) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.open_seconds = max(0.0, open_seconds)
        self._failures = 0
        self._opened_until = 0.0
        self._half_open = False
        self._lock = asyncio.Lock()

    async def allow_request(self) -> bool:
        async with self._lock:
            now = time.monotonic()
            if self._opened_until and now < self._opened_until:
                return False
            if self._opened_until:
                if self._half_open:
                    return False
                self._half_open = True
            return True

    async def record_success(self) -> None:
        async with self._lock:
            self._failures = 0
            self._opened_until = 0.0
            self._half_open = False

    async def record_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._opened_until = time.monotonic() + self.open_seconds
                self._half_open = False

    async def reset(self) -> None:
        async with self._lock:
            self._failures = 0
            self._opened_until = 0.0
            self._half_open = False


circuit_breaker = RiskCircuitBreaker(
    failure_threshold=settings.RISK_CIRCUIT_FAILURE_THRESHOLD,
    open_seconds=settings.RISK_CIRCUIT_OPEN_SECONDS,
)


def _unavailable(status_code: int = 503, detail: str = "RISK_UNAVAILABLE") -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


async def assess_transaction_risk(
    *,
    transaction_id: UUID,
    source_account_id: UUID,
    destination_account_id: UUID,
    amount_cents: int,
    operation_type: str,
) -> RiskAssessment:
    if not await circuit_breaker.allow_request():
        raise _unavailable(detail="RISK_CIRCUIT_OPEN")

    request_body = {
        "transaction_id": str(transaction_id),
        "source_account_id": str(source_account_id),
        "destination_account_id": str(destination_account_id),
        "amount_cents": amount_cents,
        "operation_type": operation_type,
    }
    token_refreshed = False
    transient_attempt = 0
    log_event(
        logger,
        "risk.assessment.started",
        transaction_id=str(transaction_id),
        operation_type=operation_type,
    )

    while True:
        try:
            service_token = await get_internal_service_token(scope="risk:assess")
            async with httpx.AsyncClient(timeout=settings.RISK_TIMEOUT_SECONDS) as client:
                request_headers = {
                    "Authorization": f"Bearer {service_token}",
                    **(
                        {"X-Request-ID": current_request_id()}
                        if current_request_id()
                        else {}
                    ),
                    **(
                        {"X-Correlation-ID": current_correlation_id()}
                        if current_correlation_id()
                        else {}
                    ),
                }
                with _tracer.start_as_current_span("risk.assess") as span:
                    span.set_attribute("risk.attempt", transient_attempt + 1)
                    inject_trace_headers(request_headers)
                    response = await client.post(
                        f"{settings.RISK_SERVICE_URL}/internal/risk/assessments",
                        headers=request_headers,
                        json=request_body,
                    )
        except httpx.TimeoutException as exc:
            if transient_attempt < settings.RISK_RETRY_COUNT:
                transient_attempt += 1
                await asyncio.sleep(settings.RISK_RETRY_DELAY_SECONDS)
                continue
            await circuit_breaker.record_failure()
            log_event(
                logger,
                "risk.assessment.failed",
                level=logging.WARNING,
                transaction_id=str(transaction_id),
                status=504,
                error_type=type(exc).__name__,
            )
            raise _unavailable(status_code=504) from exc
        except httpx.RequestError as exc:
            if transient_attempt < settings.RISK_RETRY_COUNT:
                transient_attempt += 1
                await asyncio.sleep(settings.RISK_RETRY_DELAY_SECONDS)
                continue
            await circuit_breaker.record_failure()
            log_event(
                logger,
                "risk.assessment.failed",
                level=logging.WARNING,
                transaction_id=str(transaction_id),
                status=503,
                error_type=type(exc).__name__,
            )
            raise _unavailable() from exc

        if response.status_code in (401, 403) and not token_refreshed:
            # This is a credential refresh, not a generic retry of a 4xx.
            await invalidate_internal_service_token(scope="risk:assess")
            token_refreshed = True
            continue

        if response.status_code in (500, 502, 503, 504):
            if transient_attempt < settings.RISK_RETRY_COUNT:
                transient_attempt += 1
                await asyncio.sleep(settings.RISK_RETRY_DELAY_SECONDS)
                continue
            await circuit_breaker.record_failure()
            log_event(
                logger,
                "risk.assessment.failed",
                level=logging.WARNING,
                transaction_id=str(transaction_id),
                status=response.status_code,
            )
            raise _unavailable()

        if response.status_code == 409:
            await circuit_breaker.record_success()
            log_event(
                logger,
                "risk.assessment.conflict",
                level=logging.WARNING,
                transaction_id=str(transaction_id),
                status=409,
            )
            raise _unavailable(status_code=409, detail="RISK_ASSESSMENT_CONFLICT")

        if response.status_code != 200:
            await circuit_breaker.record_success()
            raise _unavailable()

        try:
            body = response.json()
            assessment = RiskAssessment(
                assessment_id=UUID(body["assessment_id"]),
                decision=str(body["decision"]).upper(),
                rules_version=str(body["rules_version"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            await circuit_breaker.record_failure()
            log_event(
                logger,
                "risk.assessment.failed",
                level=logging.WARNING,
                transaction_id=str(transaction_id),
                status=503,
                error_type=type(exc).__name__,
            )
            raise _unavailable() from exc

        await circuit_breaker.record_success()
        log_event(
            logger,
            "risk.assessment.completed",
            transaction_id=str(transaction_id),
            risk_assessment_id=str(assessment.assessment_id),
            decision=assessment.decision,
            rules_version=assessment.rules_version,
            status=200,
        )
        return assessment
