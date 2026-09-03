from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models import Account, LedgerTransaction, LedgerEntry, TransactionType, TransactionStatus
from app.seed import SETTLEMENT_ACCOUNT_ID, is_settlement

IDEM_TTL_SECONDS = 86400
DEBIT = "DEBIT"
CREDIT = "CREDIT"


def _balanced(entries: list[tuple[Account, str, int]]) -> None:
    total_debit = sum(amount for _, side, amount in entries if side == DEBIT)
    total_credit = sum(amount for _, side, amount in entries if side == CREDIT)
    if total_debit != total_credit:
        raise HTTPException(status_code=500, detail="Lançamento contábil desbalanceado.")
    if total_debit <= 0:
        raise HTTPException(status_code=400, detail="Valor da operação deve ser positivo.")


async def _load_existing(db: AsyncSession, idempotency_key: str) -> LedgerTransaction | None:
    q = select(LedgerTransaction).where(LedgerTransaction.idempotency_key == idempotency_key)
    return (await db.execute(q)).scalars().first()


async def _claim_idempotency(redis, db: AsyncSession, idempotency_key: str) -> LedgerTransaction | None:
    existing = await _load_existing(db, idempotency_key)
    if existing:
        return existing
    if redis is None:
        return None
    try:
        acquired = await redis.set(f"idem:{idempotency_key}", "pending", nx=True, ex=IDEM_TTL_SECONDS)
    except Exception:
        return None
    if acquired:
        return None
    existing = await _load_existing(db, idempotency_key)
    if existing:
        return existing
    raise HTTPException(status_code=409, detail="Transação em processamento. Tente novamente.")


async def _release_idempotency(redis, idempotency_key: str) -> None:
    if redis is None:
        return
    try:
        await redis.delete(f"idem:{idempotency_key}")
    except Exception:
        return


async def _lock_accounts(db: AsyncSession, *account_ids: UUID) -> dict[UUID, Account]:
    unique_ids = sorted({aid for aid in account_ids if aid is not None})
    locked: dict[UUID, Account] = {}
    for aid in unique_ids:
        result = await db.execute(select(Account).where(Account.id == aid).with_for_update())
        acc = result.scalars().first()
        if acc:
            locked[aid] = acc
    return locked


def _apply_entries(db: AsyncSession, tx: LedgerTransaction, entries: list[tuple[Account, str, int]]) -> None:
    _balanced(entries)
    for acc, side, amount in entries:
        db.add(
            LedgerEntry(
                transaction_id=tx.id,
                account_id=acc.id,
                side=side,
                amount_cents=amount,
            )
        )
        if side == CREDIT:
            acc.balance_cents += amount
        else:
            acc.balance_cents -= amount
            if acc.balance_cents < 0 and not is_settlement(acc):
                raise HTTPException(status_code=400, detail="Saldo insuficiente para a operação.")


async def deposit_funds(
    db: AsyncSession,
    account_id: UUID,
    amount_cents: int,
    idempotency_key: str,
    description: str | None = None,
    redis=None,
) -> LedgerTransaction:
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Valor do depósito deve ser positivo.")

    existing = await _claim_idempotency(redis, db, idempotency_key)
    if existing:
        return existing

    try:
        locked = await _lock_accounts(db, account_id, SETTLEMENT_ACCOUNT_ID)
        dest = locked.get(account_id)
        settlement = locked.get(SETTLEMENT_ACCOUNT_ID)
        if not dest:
            raise HTTPException(status_code=404, detail="Conta não encontrada para depósito.")
        if not settlement:
            raise HTTPException(status_code=500, detail="Conta de liquidação interna indisponível.")
        if is_settlement(dest):
            raise HTTPException(status_code=400, detail="Não é permitido depositar na conta de liquidação.")

        tx = LedgerTransaction(
            idempotency_key=idempotency_key,
            destination_account_id=account_id,
            amount_cents=amount_cents,
            transaction_type=TransactionType.DEPOSIT.value,
            status=TransactionStatus.COMPLETED.value,
            description=description or "Depósito em Conta",
        )
        db.add(tx)
        await db.flush()
        _apply_entries(db, tx, [
            (settlement, DEBIT, amount_cents),
            (dest, CREDIT, amount_cents),
        ])
        await db.commit()
        await db.refresh(tx)
        return tx
    except IntegrityError:
        await db.rollback()
        existing = await _load_existing(db, idempotency_key)
        if existing:
            return existing
        raise HTTPException(status_code=409, detail="Chave de idempotência já utilizada.")
    except HTTPException:
        await db.rollback()
        await _release_idempotency(redis, idempotency_key)
        raise
    except Exception:
        await db.rollback()
        await _release_idempotency(redis, idempotency_key)
        raise


async def transfer_funds(
    db: AsyncSession,
    source_account_id: UUID,
    destination_account_id: UUID,
    amount_cents: int,
    idempotency_key: str,
    description: str | None = None,
    redis=None,
) -> LedgerTransaction:
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Valor da transferência deve ser positivo.")
    if source_account_id == destination_account_id:
        raise HTTPException(status_code=400, detail="Não é possível transferir para a própria conta.")

    existing = await _claim_idempotency(redis, db, idempotency_key)
    if existing:
        return existing

    try:
        locked = await _lock_accounts(db, source_account_id, destination_account_id)
        source_acc = locked.get(source_account_id)
        dest_acc = locked.get(destination_account_id)
        if not source_acc or not dest_acc:
            raise HTTPException(status_code=404, detail="Conta de origem ou destino não encontrada.")
        if is_settlement(source_acc) or is_settlement(dest_acc):
            raise HTTPException(status_code=400, detail="Conta de liquidação não participa de Pix.")
        if source_acc.balance_cents < amount_cents:
            raise HTTPException(status_code=400, detail="Saldo insuficiente para transferência Pix.")

        tx = LedgerTransaction(
            idempotency_key=idempotency_key,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount_cents=amount_cents,
            transaction_type=TransactionType.TRANSFER.value,
            status=TransactionStatus.COMPLETED.value,
            description=description or "Transferência Pix BankCore",
        )
        db.add(tx)
        await db.flush()
        _apply_entries(db, tx, [
            (source_acc, DEBIT, amount_cents),
            (dest_acc, CREDIT, amount_cents),
        ])
        await db.commit()
        await db.refresh(tx)
        return tx
    except IntegrityError:
        await db.rollback()
        existing = await _load_existing(db, idempotency_key)
        if existing:
            return existing
        raise HTTPException(status_code=409, detail="Chave de idempotência já utilizada.")
    except HTTPException:
        await db.rollback()
        await _release_idempotency(redis, idempotency_key)
        raise
    except Exception:
        await db.rollback()
        await _release_idempotency(redis, idempotency_key)
        raise
