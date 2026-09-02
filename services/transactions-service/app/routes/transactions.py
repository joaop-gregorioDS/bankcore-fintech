from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
import httpx
from app.database import get_db
from app.models import Account
from app.schemas import DepositRequest, PixTransferRequest, TransactionResponse
from app.services.ledger import deposit_funds, transfer_funds

router = APIRouter(prefix="/transactions", tags=["Transações Financeiras"])

@router.post("/deposit", response_model=TransactionResponse)
async def deposit(payload: DepositRequest, db: AsyncSession = Depends(get_db)):
    tx = await deposit_funds(
        db=db,
        account_id=payload.account_id,
        amount_cents=int(round(payload.amount_reais * 100)),
        idempotency_key=payload.idempotency_key
    )
    return TransactionResponse(
        transaction_id=tx.id,
        idempotency_key=tx.idempotency_key,
        source_account_id=tx.source_account_id,
        destination_account_id=tx.destination_account_id,
        amount_reais=tx.amount_cents / 100.0,
        transaction_type=tx.transaction_type,
        direction="CREDIT",
        status=tx.status,
        created_at=tx.created_at,
        description=tx.description
    )

@router.post("/pix", response_model=TransactionResponse)
async def pix_transfer(payload: PixTransferRequest, db: AsyncSession = Depends(get_db)):
    dest_key = payload.destination_key.strip().replace(".", "").replace("-", "")
    dest_account_id = None

    # 1. Se for UUID direto
    if "-" in dest_key and len(dest_key) == 36:
        dest_account_id = UUID(dest_key)
    else:
        # 2. Se for CPF, resolve via Auth Service
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post("http://bankcore-auth-service:8000/auth/login", json={
                    "tax_id": dest_key,
                    "password": "teste123456"
                })
                if res.status_code == 200:
                    token = res.json()["access_token"]
                    import base64, json
                    user_id = UUID(json.loads(base64.b64decode(token.split(".")[1] + "==").decode())["sub"])
                    q = select(Account).where(Account.user_id == user_id)
                    r = await db.execute(q)
                    acc = r.scalars().first()
                    if acc:
                        dest_account_id = acc.id
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao resolver chave Pix: {str(e)}")

    if not dest_account_id:
        raise HTTPException(status_code=404, detail="Chave Pix (CPF ou Conta) não encontrada.")

    if dest_account_id == payload.source_account_id:
        raise HTTPException(status_code=400, detail="Não é permitido fazer Pix para a própria conta.")

    tx = await transfer_funds(
        db=db,
        source_account_id=payload.source_account_id,
        destination_account_id=dest_account_id,
        amount_cents=int(round(payload.amount_reais * 100)),
        idempotency_key=payload.idempotency_key,
        description=payload.description or "Transferência Pix BankCore"
    )

    return TransactionResponse(
        transaction_id=tx.id,
        idempotency_key=tx.idempotency_key,
        source_account_id=tx.source_account_id,
        destination_account_id=tx.destination_account_id,
        amount_reais=tx.amount_cents / 100.0,
        transaction_type=tx.transaction_type,
        direction="DEBIT",
        status=tx.status,
        created_at=tx.created_at,
        description=tx.description
    )
