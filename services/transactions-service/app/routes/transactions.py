import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
import httpx
from app.config import settings
from app.database import get_db
from app.demo_mode import require_demo_mode
from app.deps import get_current_user
from app.internal_auth import get_internal_service_token
from app.idempotency import build_transaction_id
from app.models import Account
from app.money import cents_to_reais, reais_to_cents
from app.schemas import DepositRequest, PixTransferRequest, TransactionResponse
from app.seed import SETTLEMENT_ACCOUNT_ID, is_settlement
from app.services.ledger import deposit_funds, transfer_funds
from app.risk_client import assess_transaction_risk
from common.observability import (
    current_correlation_id,
    current_request_id,
    log_event,
    set_correlation_id,
)

router = APIRouter(prefix="/transactions", tags=["Transações Financeiras"])
logger = logging.getLogger("bankcore.transactions")
PIX_DESTINATION_NOT_FOUND = "Destinatário não encontrado."


def require_demo_deposit_mode() -> None:
    require_demo_mode(settings.DEMO_MODE)


def _tx_response(tx: object, direction: str) -> TransactionResponse:
    return TransactionResponse(
        transaction_id=tx.id,
        idempotency_key=tx.idempotency_key,
        source_account_id=tx.source_account_id,
        destination_account_id=tx.destination_account_id,
        amount_reais=float(cents_to_reais(tx.amount_cents)),
        transaction_type=tx.transaction_type,
        direction=direction,
        status=tx.status,
        created_at=tx.created_at,
        description=tx.description,
    )


async def _require_own_account(db: AsyncSession, account_id: UUID, user_id: UUID) -> Account:
    result = await db.execute(select(Account).where(Account.id == account_id))
    acc = result.scalars().first()
    if not acc or is_settlement(acc) or acc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conta bancária não encontrada.")
    return acc


def _parse_uuid_key(raw: str) -> UUID | None:
    compact = raw.replace("-", "")
    if len(compact) != 32:
        return None
    try:
        return UUID(compact)
    except ValueError:
        return None


async def _resolve_pix_destination(
    db: AsyncSession,
    destination_key: str,
) -> UUID:
    raw = destination_key.strip()
    as_uuid = _parse_uuid_key(raw)
    if as_uuid:
        if as_uuid == SETTLEMENT_ACCOUNT_ID:
            raise HTTPException(status_code=404, detail=PIX_DESTINATION_NOT_FOUND)
        result = await db.execute(select(Account).where(Account.id == as_uuid))
        acc = result.scalars().first()
        if not acc or is_settlement(acc):
            raise HTTPException(status_code=404, detail=PIX_DESTINATION_NOT_FOUND)
        return acc.id

    tax_id = "".join(ch for ch in raw if ch.isdigit())
    if len(tax_id) not in (11, 14):
        raise HTTPException(status_code=404, detail=PIX_DESTINATION_NOT_FOUND)

    try:
        service_token = await get_internal_service_token()
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                f"{settings.AUTH_SERVICE_URL}/auth/internal/pix/resolve",
                headers={
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
                },
                json={"pix_key": tax_id},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Diretório Pix indisponível.") from exc

    if res.status_code == 404:
        raise HTTPException(status_code=404, detail=PIX_DESTINATION_NOT_FOUND)
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="Diretório Pix indisponível.")

    dest_user_id = UUID(res.json()["destination_user_id"])
    q = select(Account).where(
        Account.user_id == dest_user_id,
        Account.id != SETTLEMENT_ACCOUNT_ID,
    ).order_by(Account.created_at.asc())
    r = await db.execute(q)
    acc = r.scalars().first()
    if not acc:
        raise HTTPException(status_code=404, detail=PIX_DESTINATION_NOT_FOUND)
    return acc.id


@router.post(
    "/deposit",
    response_model=TransactionResponse,
    dependencies=[Depends(require_demo_deposit_mode)],
)
async def deposit(
    payload: DepositRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_demo_mode(settings.DEMO_MODE)
    user_id = UUID(current_user["sub"])
    await _require_own_account(db, payload.account_id, user_id)
    tx = await deposit_funds(
        db=db,
        user_id=user_id,
        account_id=payload.account_id,
        amount_cents=reais_to_cents(payload.amount_reais),
        idempotency_key=payload.idempotency_key,
    )
    set_correlation_id(str(tx.id))
    log_event(
        logger,
        "transactions.ledger.committed",
        transaction_id=str(tx.id),
        operation_type="DEPOSIT",
        status=200,
    )
    return _tx_response(tx, "CREDIT")


@router.post("/pix", response_model=TransactionResponse)
async def pix_transfer(
    payload: PixTransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])
    await _require_own_account(db, payload.source_account_id, user_id)

    transaction_id = build_transaction_id(
        user_id=user_id,
        account_id=payload.source_account_id,
        operation_type="TRANSFER",
        idempotency_key=payload.idempotency_key,
    )
    set_correlation_id(str(transaction_id))

    dest_account_id = await _resolve_pix_destination(
        db,
        payload.destination_key,
    )

    if dest_account_id == payload.source_account_id:
        raise HTTPException(status_code=400, detail="Não é permitido fazer Pix para a própria conta.")

    amount_cents = reais_to_cents(payload.amount_reais)
    log_event(
        logger,
        "transactions.operation.started",
        transaction_id=str(transaction_id),
        operation_type="PIX",
    )

    # End the pre-flight session transaction before any network call to Risk.
    await db.rollback()
    risk = await assess_transaction_risk(
        transaction_id=transaction_id,
        source_account_id=payload.source_account_id,
        destination_account_id=dest_account_id,
        amount_cents=amount_cents,
        operation_type="PIX",
    )
    if risk.decision == "REVIEW":
        raise HTTPException(status_code=409, detail="RISK_REVIEW_REQUIRED")
    if risk.decision == "REJECTED":
        raise HTTPException(status_code=422, detail="RISK_REJECTED")
    if risk.decision != "APPROVED":
        raise HTTPException(status_code=503, detail="RISK_UNAVAILABLE")

    tx = await transfer_funds(
        db=db,
        user_id=user_id,
        source_account_id=payload.source_account_id,
        destination_account_id=dest_account_id,
        amount_cents=amount_cents,
        idempotency_key=payload.idempotency_key,
        description=payload.description or "Transferência Pix BankCore",
        transaction_id=transaction_id,
        risk_assessment_id=risk.assessment_id,
        risk_decision=risk.decision,
        risk_rules_version=risk.rules_version,
    )
    log_event(
        logger,
        "transactions.ledger.committed",
        transaction_id=str(tx.id),
        risk_assessment_id=str(risk.assessment_id),
        operation_type="PIX",
        status=200,
    )
    log_event(
        logger,
        "transactions.outbox.created",
        transaction_id=str(tx.id),
        risk_assessment_id=str(risk.assessment_id),
        operation_type="PIX",
        status=200,
    )
    return _tx_response(tx, "DEBIT")

