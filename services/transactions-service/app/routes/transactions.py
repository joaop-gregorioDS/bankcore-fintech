from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
import httpx
from app.config import settings
from app.database import get_db, get_redis
from app.deps import get_current_user, bearer_scheme
from app.models import Account
from app.schemas import DepositRequest, PixTransferRequest, TransactionResponse
from app.seed import SETTLEMENT_ACCOUNT_ID, is_settlement
from app.services.ledger import deposit_funds, transfer_funds

router = APIRouter(prefix="/transactions", tags=["Transações Financeiras"])


def _tx_response(tx: object, direction: str) -> TransactionResponse:
    return TransactionResponse(
        transaction_id=tx.id,
        idempotency_key=tx.idempotency_key,
        source_account_id=tx.source_account_id,
        destination_account_id=tx.destination_account_id,
        amount_reais=tx.amount_cents / 100.0,
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
    bearer_token: str,
) -> UUID:
    raw = destination_key.strip()
    as_uuid = _parse_uuid_key(raw)
    if as_uuid:
        if as_uuid == SETTLEMENT_ACCOUNT_ID:
            raise HTTPException(status_code=400, detail="Chave Pix inválida.")
        result = await db.execute(select(Account).where(Account.id == as_uuid))
        acc = result.scalars().first()
        if not acc or is_settlement(acc):
            raise HTTPException(status_code=404, detail="Chave Pix não encontrada no banco.")
        return acc.id

    tax_id = "".join(ch for ch in raw if ch.isdigit())
    if len(tax_id) < 11:
        raise HTTPException(status_code=400, detail="Informe um CPF/CNPJ ou a chave da conta.")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{settings.AUTH_SERVICE_URL}/auth/directory/{tax_id}",
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao consultar diretório Pix: {exc}") from exc

    if res.status_code == 404:
        raise HTTPException(status_code=404, detail="Chave Pix (CPF) não encontrada no banco.")
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="Diretório Pix indisponível.")

    dest_user_id = UUID(res.json()["user_id"])
    q = select(Account).where(
        Account.user_id == dest_user_id,
        Account.id != SETTLEMENT_ACCOUNT_ID,
    ).order_by(Account.created_at.asc())
    r = await db.execute(q)
    acc = r.scalars().first()
    if not acc:
        raise HTTPException(status_code=404, detail="Destinatário ainda não possui conta corrente.")
    return acc.id


@router.post("/deposit", response_model=TransactionResponse)
async def deposit(
    payload: DepositRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])
    await _require_own_account(db, payload.account_id, user_id)
    tx = await deposit_funds(
        db=db,
        account_id=payload.account_id,
        amount_cents=int(round(payload.amount_reais * 100)),
        idempotency_key=payload.idempotency_key,
        redis=redis,
    )
    return _tx_response(tx, "CREDIT")


@router.post("/pix", response_model=TransactionResponse)
async def pix_transfer(
    payload: PixTransferRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    current_user: dict = Depends(get_current_user),
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    user_id = UUID(current_user["sub"])
    await _require_own_account(db, payload.source_account_id, user_id)

    dest_account_id = await _resolve_pix_destination(
        db,
        payload.destination_key,
        creds.credentials,
    )

    if dest_account_id == payload.source_account_id:
        raise HTTPException(status_code=400, detail="Não é permitido fazer Pix para a própria conta.")

    tx = await transfer_funds(
        db=db,
        source_account_id=payload.source_account_id,
        destination_account_id=dest_account_id,
        amount_cents=int(round(payload.amount_reais * 100)),
        idempotency_key=payload.idempotency_key,
        description=payload.description or "Transferência Pix BankCore",
        redis=redis,
    )
    return _tx_response(tx, "DEBIT")

