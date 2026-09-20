from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import HTTPException

from app.config import settings
from app.internal_auth import get_internal_service_token


@dataclass(frozen=True)
class RiskAssessment:
    assessment_id: UUID
    decision: str
    rules_version: str


async def assess_transaction_risk(
    *,
    transaction_id: UUID,
    source_account_id: UUID,
    destination_account_id: UUID,
    amount_cents: int,
    operation_type: str,
) -> RiskAssessment:
    try:
        service_token = await get_internal_service_token(scope="risk:assess")
        async with httpx.AsyncClient(timeout=settings.RISK_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.RISK_SERVICE_URL}/internal/risk/assessments",
                headers={"Authorization": f"Bearer {service_token}"},
                json={
                    "transaction_id": str(transaction_id),
                    "source_account_id": str(source_account_id),
                    "destination_account_id": str(destination_account_id),
                    "amount_cents": amount_cents,
                    "operation_type": operation_type,
                },
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="RISK_UNAVAILABLE") from exc
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=503, detail="RISK_UNAVAILABLE") from exc

    if response.status_code in (401, 403) or response.status_code >= 500:
        raise HTTPException(status_code=503, detail="RISK_UNAVAILABLE")
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="RISK_UNAVAILABLE")

    try:
        body = response.json()
        return RiskAssessment(
            assessment_id=UUID(body["assessment_id"]),
            decision=str(body["decision"]).upper(),
            rules_version=str(body["rules_version"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="RISK_UNAVAILABLE") from exc
