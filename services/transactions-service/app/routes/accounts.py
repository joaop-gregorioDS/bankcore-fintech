import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from app.database import get_db
from app.deps import get_current_user
from app.models import Account, LedgerTransaction
from app.schemas import AccountCreateRequest, AccountResponse, TransactionResponse
from app.seed import SETTLEMENT_ACCOUNT_ID, welcome_balance_cents, is_settlement

router = APIRouter(prefix="/accounts", tags=["Contas Bancárias"])


def _to_response(acc: Account) -> AccountResponse:
    return AccountResponse(
        id=acc.id,
        user_id=acc.user_id,
        account_number=acc.account_number,
        balance_reais=acc.balance_cents / 100.0,
        is_active=acc.is_active,
    )


def _owned_or_404(acc: Account | None, user_id: UUID) -> Account:
    if not acc or is_settlement(acc) or acc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conta bancária não encontrada.")
    return acc


@router.post("", response_model=AccountResponse, status_code=201)
@router.post("/", response_model=AccountResponse, status_code=201)
async def create_or_get_account(
    payload: AccountCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])
    if payload.user_id != user_id:
        raise HTTPException(status_code=403, detail="Não é permitido operar a conta de outro correntista.")

    query = select(Account).where(
        Account.user_id == user_id,
        Account.id != SETTLEMENT_ACCOUNT_ID,
    ).order_by(Account.created_at.asc())
    result = await db.execute(query)
    existing = result.scalars().first()
    if existing:
        return _to_response(existing)

    acc_num = f"{random.randint(10000, 99999)}-{random.randint(0, 9)}"
    acc = Account(
        user_id=user_id,
        account_number=acc_num,
        balance_cents=welcome_balance_cents(current_user.get("tax_id")),
    )
    db.add(acc)
    await db.commit()
    await db.refresh(acc)
    return _to_response(acc)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])
    result = await db.execute(select(Account).where(Account.id == account_id))
    acc = _owned_or_404(result.scalars().first(), user_id)
    return _to_response(acc)


@router.get("/{account_id}/statement", response_model=list[TransactionResponse])
async def get_statement(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = UUID(current_user["sub"])
    result = await db.execute(select(Account).where(Account.id == account_id))
    _owned_or_404(result.scalars().first(), user_id)

    query = select(LedgerTransaction).where(
        (LedgerTransaction.source_account_id == account_id) |
        (LedgerTransaction.destination_account_id == account_id)
    ).order_by(LedgerTransaction.created_at.desc())
    result = await db.execute(query)
    txs = result.scalars().all()

    response = []
    for tx in txs:
        is_credit = (tx.transaction_type == "DEPOSIT") or (
            tx.destination_account_id == account_id and tx.source_account_id != account_id
        )
        response.append(TransactionResponse(
            transaction_id=tx.id,
            idempotency_key=tx.idempotency_key,
            source_account_id=tx.source_account_id,
            destination_account_id=tx.destination_account_id,
            amount_reais=tx.amount_cents / 100.0,
            transaction_type=tx.transaction_type,
            direction="CREDIT" if is_credit else "DEBIT",
            status=tx.status,
            created_at=tx.created_at,
            description=tx.description,
        ))
    return response
