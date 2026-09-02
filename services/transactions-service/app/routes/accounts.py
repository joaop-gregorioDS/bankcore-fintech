import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from app.database import get_db
from app.models import Account, LedgerTransaction
from app.schemas import AccountCreateRequest, AccountResponse, TransactionResponse

router = APIRouter(prefix="/accounts", tags=["Contas Bancárias"])

@router.post("/", response_model=AccountResponse, status_code=201)
async def create_or_get_account(payload: AccountCreateRequest, db: AsyncSession = Depends(get_db)):
    query = select(Account).where(Account.user_id == payload.user_id).order_by(Account.created_at.asc())
    result = await db.execute(query)
    existing = result.scalars().first()
    if existing:
        return AccountResponse(
            id=existing.id,
            user_id=existing.user_id,
            account_number=existing.account_number,
            balance_reais=existing.balance_cents / 100.0,
            is_active=existing.is_active
        )

    acc_num = f"{random.randint(10000, 99999)}-{random.randint(0, 9)}"
    acc = Account(user_id=payload.user_id, account_number=acc_num, balance_cents=1000000)
    db.add(acc)
    await db.commit()
    await db.refresh(acc)

    return AccountResponse(
        id=acc.id,
        user_id=acc.user_id,
        account_number=acc.account_number,
        balance_reais=acc.balance_cents / 100.0,
        is_active=acc.is_active
    )

@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: UUID, db: AsyncSession = Depends(get_db)):
    query = select(Account).where(Account.id == account_id)
    result = await db.execute(query)
    acc = result.scalars().first()
    if not acc:
        raise HTTPException(status_code=404, detail="Conta bancária não encontrada.")
    return AccountResponse(
        id=acc.id,
        user_id=acc.user_id,
        account_number=acc.account_number,
        balance_reais=acc.balance_cents / 100.0,
        is_active=acc.is_active
    )

@router.get("/{account_id}/statement", response_model=list[TransactionResponse])
async def get_statement(account_id: UUID, db: AsyncSession = Depends(get_db)):
    query = select(LedgerTransaction).where(
        (LedgerTransaction.source_account_id == account_id) | 
        (LedgerTransaction.destination_account_id == account_id)
    ).order_by(LedgerTransaction.created_at.desc())
    result = await db.execute(query)
    txs = result.scalars().all()
    
    response = []
    for tx in txs:
        is_credit = (tx.transaction_type == "DEPOSIT") or (tx.destination_account_id == account_id and tx.source_account_id != account_id)
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
            description=tx.description
        ))
    return response
