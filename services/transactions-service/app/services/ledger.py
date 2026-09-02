import json
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Account, LedgerTransaction, TransactionType, TransactionStatus
from app.schemas import TransferRequest, DepositRequest

async def execute_deposit(payload: DepositRequest, db: AsyncSession, redis) -> LedgerTransaction:
    # 1. Verificar idempotência no Redis
    cache_key = f"idempotency:{payload.idempotency_key}"
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        return LedgerTransaction(**data)

    amount_cents = int(round(payload.amount_reais * 100))

    # 2. Bloqueio pessimista da conta destino
    query = select(Account).where(Account.id == payload.account_id).with_for_update()
    result = await db.execute(query)
    account = result.scalars().first()
    if not account:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")

    # 3. Creditar saldo
    account.balance_cents += amount_cents

    # 4. Registrar no Livro-Razão
    tx = LedgerTransaction(
        idempotency_key=payload.idempotency_key,
        source_account_id=None,
        destination_account_id=account.id,
        amount_cents=amount_cents,
        transaction_type=TransactionType.DEPOSIT.value,
        status=TransactionStatus.COMPLETED.value,
        description="Depósito de Fundos"
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    # 5. Salvar resultado no Redis com TTL de 24h
    await redis.setex(cache_key, 86400, json.dumps({
        "id": str(tx.id),
        "idempotency_key": tx.idempotency_key,
        "source_account_id": None,
        "destination_account_id": str(tx.destination_account_id),
        "amount_cents": tx.amount_cents,
        "transaction_type": tx.transaction_type,
        "status": tx.status,
        "description": tx.description,
        "created_at": tx.created_at.isoformat()
    }))

    return tx

async def execute_transfer(payload: TransferRequest, db: AsyncSession, redis) -> LedgerTransaction:
    if payload.source_account_id == payload.destination_account_id:
        raise HTTPException(status_code=400, detail="A conta de origem e destino não podem ser iguais.")

    # 1. Verificar idempotência no Redis
    cache_key = f"idempotency:{payload.idempotency_key}"
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        return LedgerTransaction(**data)

    amount_cents = int(round(payload.amount_reais * 100))

    # 2. Ordenar IDs para prevenir DEADLOCK no banco de dados
    first_id, second_id = sorted([payload.source_account_id, payload.destination_account_id])

    q1 = select(Account).where(Account.id == first_id).with_for_update()
    q2 = select(Account).where(Account.id == second_id).with_for_update()
    r1 = await db.execute(q1)
    r2 = await db.execute(q2)
    acc_map = {acc.id: acc for acc in [r1.scalars().first(), r2.scalars().first()] if acc}

    source_acc = acc_map.get(payload.source_account_id)
    dest_acc = acc_map.get(payload.destination_account_id)

    if not source_acc or not dest_acc:
        raise HTTPException(status_code=404, detail="Conta de origem ou destino não encontrada.")

    # 3. Garantir que tem saldo suficiente
    if source_acc.balance_cents < amount_cents:
        raise HTTPException(status_code=422, detail="Saldo insuficiente para realizar a transferência.")

    # 4. Transação Atômica: Débito e Crédito
    source_acc.balance_cents -= amount_cents
    dest_acc.balance_cents += amount_cents

    # 5. Registro no Livro-Razão
    tx = LedgerTransaction(
        idempotency_key=payload.idempotency_key,
        source_account_id=source_acc.id,
        destination_account_id=dest_acc.id,
        amount_cents=amount_cents,
        transaction_type=TransactionType.PIX.value,
        status=TransactionStatus.COMPLETED.value,
        description=payload.description
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    # 6. Salvar cache de idempotência
    await redis.setex(cache_key, 86400, json.dumps({
        "id": str(tx.id),
        "idempotency_key": tx.idempotency_key,
        "source_account_id": str(tx.source_account_id),
        "destination_account_id": str(tx.destination_account_id),
        "amount_cents": tx.amount_cents,
        "transaction_type": tx.transaction_type,
        "status": tx.status,
        "description": tx.description,
        "created_at": tx.created_at.isoformat()
    }))

    return tx
