from uuid import UUID, uuid4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models import Account, IdempotencyRecord, LedgerTransaction, LedgerEntry, OutboxEvent, TransactionType, TransactionStatus
from app.money import BIGINT_MAX_CENTS
from app.idempotency import build_request_fingerprint
from app.seed import SETTLEMENT_ACCOUNT_ID, is_settlement
from app.events import build_transaction_completed_v1

IDEM_PROCESSING = "PROCESSING"
IDEM_COMPLETED = "COMPLETED"
DEBIT = "DEBIT"
CREDIT = "CREDIT"


def _validate_amount_cents(amount_cents: int) -> None:
    if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
        raise HTTPException(status_code=400, detail="Valor deve ser informado em centavos inteiros.")
    if amount_cents > BIGINT_MAX_CENTS:
        raise HTTPException(status_code=400, detail="Valor excede o limite de BIGINT.")


def _balanced(entries: list[tuple[Account, str, int]]) -> None:
    total_debit = sum(amount for _, side, amount in entries if side == DEBIT)
    total_credit = sum(amount for _, side, amount in entries if side == CREDIT)
    if total_debit != total_credit:
        raise HTTPException(status_code=500, detail="Lançamento contábil desbalanceado.")
    if total_debit <= 0:
        raise HTTPException(status_code=400, detail="Valor da operação deve ser positivo.")


async def _load_idempotency_record(
    db: AsyncSession,
    *,
    user_id: UUID,
    account_id: UUID,
    operation_type: str,
    idempotency_key: str,
) -> IdempotencyRecord | None:
    query = select(IdempotencyRecord).where(
        IdempotencyRecord.user_id == user_id,
        IdempotencyRecord.account_id == account_id,
        IdempotencyRecord.operation_type == operation_type,
        IdempotencyRecord.idempotency_key == idempotency_key,
    )
    return (await db.execute(query)).scalars().first()


async def _resolve_existing_idempotency(
    db: AsyncSession,
    record: IdempotencyRecord,
    fingerprint: str,
) -> LedgerTransaction:
    if record.request_fingerprint != fingerprint:
        raise HTTPException(status_code=409, detail="Chave de idempotência reutilizada com payload diferente.")
    if record.status == IDEM_PROCESSING:
        raise HTTPException(status_code=409, detail="Transação em processamento. Tente novamente.")
    if record.status != IDEM_COMPLETED or record.transaction_id is None:
        raise HTTPException(status_code=500, detail="Registro de idempotência inconsistente.")

    transaction = await db.get(LedgerTransaction, record.transaction_id)
    if transaction is None:
        raise HTTPException(status_code=500, detail="Transação idempotente não encontrada.")
    return transaction


async def _claim_idempotency(
    db: AsyncSession,
    *,
    user_id: UUID,
    account_id: UUID,
    operation_type: str,
    idempotency_key: str,
    fingerprint: str,
) -> tuple[LedgerTransaction | None, IdempotencyRecord]:
    existing_record = await _load_idempotency_record(
        db,
        user_id=user_id,
        account_id=account_id,
        operation_type=operation_type,
        idempotency_key=idempotency_key,
    )
    if existing_record:
        return await _resolve_existing_idempotency(db, existing_record, fingerprint), existing_record

    record = IdempotencyRecord(
        idempotency_key=idempotency_key,
        user_id=user_id,
        account_id=account_id,
        operation_type=operation_type,
        request_fingerprint=fingerprint,
        status=IDEM_PROCESSING,
    )
    db.add(record)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        existing_record = await _load_idempotency_record(
            db,
            user_id=user_id,
            account_id=account_id,
            operation_type=operation_type,
            idempotency_key=idempotency_key,
        )
        if existing_record is None:
            raise HTTPException(status_code=409, detail="Chave de idempotência já utilizada.")
        return await _resolve_existing_idempotency(db, existing_record, fingerprint), existing_record
    return None, record


def _complete_idempotency(record: IdempotencyRecord, transaction: LedgerTransaction) -> None:
    record.transaction_id = transaction.id
    record.status = IDEM_COMPLETED


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
    user_id: UUID,
    account_id: UUID,
    amount_cents: int,
    idempotency_key: str,
    description: str | None = None,
) -> LedgerTransaction:
    _validate_amount_cents(amount_cents)
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Valor do depósito deve ser positivo.")

    try:
        fingerprint = build_request_fingerprint(
            user_id=user_id,
            account_id=account_id,
            operation_type=TransactionType.DEPOSIT.value,
            idempotency_key=idempotency_key,
            amount_cents=amount_cents,
            description=description or "Depósito em Conta",
        )
        existing, record = await _claim_idempotency(
            db,
            user_id=user_id,
            account_id=account_id,
            operation_type=TransactionType.DEPOSIT.value,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
        if existing:
            return existing

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
        _complete_idempotency(record, tx)
        await db.commit()
        await db.refresh(tx)
        return tx
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Chave de idempotência já utilizada.")
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise


async def transfer_funds(
    db: AsyncSession,
    user_id: UUID,
    source_account_id: UUID,
    destination_account_id: UUID,
    amount_cents: int,
    idempotency_key: str,
    description: str | None = None,
    transaction_id: UUID | None = None,
    risk_assessment_id: UUID | None = None,
    risk_decision: str | None = None,
    risk_rules_version: str | None = None,
) -> LedgerTransaction:
    _validate_amount_cents(amount_cents)
    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Valor da transferência deve ser positivo.")
    if source_account_id == destination_account_id:
        raise HTTPException(status_code=400, detail="Não é possível transferir para a própria conta.")

    try:
        normalized_description = description or "Transferência Pix BankCore"
        fingerprint = build_request_fingerprint(
            user_id=user_id,
            account_id=source_account_id,
            operation_type=TransactionType.TRANSFER.value,
            idempotency_key=idempotency_key,
            amount_cents=amount_cents,
            destination_account_id=destination_account_id,
            description=normalized_description,
        )
        existing, record = await _claim_idempotency(
            db,
            user_id=user_id,
            account_id=source_account_id,
            operation_type=TransactionType.TRANSFER.value,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
        if existing:
            return existing

        stable_transaction_id = transaction_id or uuid4()
        if risk_assessment_id is None or risk_decision != "APPROVED" or not risk_rules_version:
            raise HTTPException(status_code=503, detail="RISK_UNAVAILABLE")

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
            id=stable_transaction_id,
            idempotency_key=idempotency_key,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount_cents=amount_cents,
            transaction_type=TransactionType.TRANSFER.value,
            status=TransactionStatus.COMPLETED.value,
            description=normalized_description,
            risk_assessment_id=risk_assessment_id,
            risk_decision=risk_decision,
            risk_rules_version=risk_rules_version,
        )
        db.add(tx)
        await db.flush()
        _apply_entries(db, tx, [
            (source_acc, DEBIT, amount_cents),
            (dest_acc, CREDIT, amount_cents),
        ])
        event = build_transaction_completed_v1(tx)
        db.add(
            OutboxEvent(
                id=event.event_id,
                aggregate_type="transaction",
                aggregate_id=tx.id,
                event_type=event.event_type,
                event_version=event.event_version,
                message_key=str(tx.id),
                payload=event.payload(),
                occurred_at=event.occurred_at,
            )
        )
        _complete_idempotency(record, tx)
        await db.commit()
        await db.refresh(tx)
        return tx
    except IntegrityError:
        await db.rollback()
        if transaction_id:
            replay = await db.get(LedgerTransaction, transaction_id)
            if replay is not None:
                return replay
        raise HTTPException(status_code=409, detail="Chave de idempotência já utilizada.")
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise
