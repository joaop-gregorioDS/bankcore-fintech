from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models import Account, LedgerTransaction, TransactionType, TransactionStatus

async def deposit_funds(
    db: AsyncSession,
    account_id: UUID,
    amount_cents: int,
    idempotency_key: str,
    description: str | None = None
) -> LedgerTransaction:
    q = select(LedgerTransaction).where(LedgerTransaction.idempotency_key == idempotency_key)
    res = await db.execute(q)
    existing = res.scalars().first()
    if existing:
        return existing

    q_acc = select(Account).where(Account.id == account_id).with_for_update()
    res_acc = await db.execute(q_acc)
    acc = res_acc.scalars().first()
    if not acc:
        raise HTTPException(status_code=404, detail="Conta não encontrada para depósito.")

    acc.balance_cents += amount_cents

    tx = LedgerTransaction(
        idempotency_key=idempotency_key,
        destination_account_id=account_id,
        amount_cents=amount_cents,
        transaction_type=TransactionType.DEPOSIT.value,
        status=TransactionStatus.COMPLETED.value,
        description=description or "Depósito em Conta"
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx

async def transfer_funds(
    db: AsyncSession,
    source_account_id: UUID,
    destination_account_id: UUID,
    amount_cents: int,
    idempotency_key: str,
    description: str | None = None
) -> LedgerTransaction:
    if source_account_id == destination_account_id:
        raise HTTPException(status_code=400, detail="Não é possível transferir para a própria conta.")

    q = select(LedgerTransaction).where(LedgerTransaction.idempotency_key == idempotency_key)
    res = await db.execute(q)
    existing = res.scalars().first()
    if existing:
        return existing

    # Travar as duas contas em ordem determinística para prevenir deadlock
    first_id, second_id = sorted([source_account_id, destination_account_id])
    q1 = select(Account).where(Account.id == first_id).with_for_update()
    q2 = select(Account).where(Account.id == second_id).with_for_update()

    r1 = await db.execute(q1)
    r2 = await db.execute(q2)
    acc1 = r1.scalars().first()
    acc2 = r2.scalars().first()

    accounts = {acc1.id: acc1, acc2.id: acc2} if acc1 and acc2 else {}
    source_acc = accounts.get(source_account_id)
    dest_acc = accounts.get(destination_account_id)

    if not source_acc or not dest_acc:
        raise HTTPException(status_code=404, detail="Conta de origem ou destino não encontrada.")

    if source_acc.balance_cents < amount_cents:
        raise HTTPException(status_code=400, detail="Saldo insuficiente para transferência Pix.")

    source_acc.balance_cents -= amount_cents
    dest_acc.balance_cents += amount_cents

    tx = LedgerTransaction(
        idempotency_key=idempotency_key,
        source_account_id=source_account_id,
        destination_account_id=destination_account_id,
        amount_cents=amount_cents,
        transaction_type=TransactionType.TRANSFER.value,
        status=TransactionStatus.COMPLETED.value,
        description=description or "Transferência Pix BankCore"
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx
