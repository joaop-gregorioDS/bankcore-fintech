from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db, get_redis
from app.schemas import DepositRequest, TransferRequest, TransactionResponse
from app.services.ledger import execute_deposit, execute_transfer

router = APIRouter(prefix="/transactions", tags=["Transações & Pix"])

@router.post("/deposit", response_model=TransactionResponse)
async def deposit(payload: DepositRequest, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)):
    tx = await execute_deposit(payload, db, redis)
    return TransactionResponse(
        transaction_id=tx.id,
        idempotency_key=tx.idempotency_key,
        amount_reais=tx.amount_cents / 100.0,
        transaction_type=tx.transaction_type,
        status=tx.status,
        created_at=tx.created_at,
        description=tx.description
    )

@router.post("/transfer", response_model=TransactionResponse)
async def transfer(payload: TransferRequest, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)):
    tx = await execute_transfer(payload, db, redis)
    return TransactionResponse(
        transaction_id=tx.id,
        idempotency_key=tx.idempotency_key,
        amount_reais=tx.amount_cents / 100.0,
        transaction_type=tx.transaction_type,
        status=tx.status,
        created_at=tx.created_at,
        description=tx.description
    )
