import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict

from app.models import LedgerTransaction, TransactionType


TRANSACTION_COMPLETED_EVENT_TYPE = "transaction.completed"
TRANSACTION_COMPLETED_EVENT_VERSION = 1
TRANSACTION_COMPLETED_PRODUCER = "transactions-service"
TRANSACTION_COMPLETED_NAMESPACE = UUID("3d1f92b3-7f61-4d90-9fa2-4c4a6ac7a7e1")


class TransactionCompletedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: UUID
    source_account_id: UUID
    destination_account_id: UUID
    amount_cents: int
    operation_type: Literal["PIX"]
    risk_assessment_id: UUID
    risk_rules_version: str


class TransactionCompletedV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_type: Literal["transaction.completed"]
    event_version: Literal[1]
    occurred_at: datetime
    producer: Literal["transactions-service"]
    correlation_id: UUID
    data: TransactionCompletedData

    def payload(self) -> dict:
        return json.loads(self.canonical_json())

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_transaction_completed_v1(
    transaction: LedgerTransaction,
) -> TransactionCompletedV1:
    if transaction.transaction_type != TransactionType.TRANSFER.value:
        raise ValueError("Only PIX transfers have a transaction.completed.v1 event.")
    if transaction.source_account_id is None or transaction.destination_account_id is None:
        raise ValueError("A completed PIX transfer requires both account identifiers.")
    if transaction.risk_assessment_id is None or not transaction.risk_rules_version:
        raise ValueError("A completed PIX transfer requires risk audit data.")

    event_id = uuid5(
        TRANSACTION_COMPLETED_NAMESPACE,
        f"{transaction.id}:{TRANSACTION_COMPLETED_EVENT_TYPE}:{TRANSACTION_COMPLETED_EVENT_VERSION}",
    )
    return TransactionCompletedV1(
        event_id=event_id,
        event_type=TRANSACTION_COMPLETED_EVENT_TYPE,
        event_version=TRANSACTION_COMPLETED_EVENT_VERSION,
        occurred_at=_as_utc(transaction.created_at),
        producer=TRANSACTION_COMPLETED_PRODUCER,
        correlation_id=transaction.id,
        data=TransactionCompletedData(
            transaction_id=transaction.id,
            source_account_id=transaction.source_account_id,
            destination_account_id=transaction.destination_account_id,
            amount_cents=transaction.amount_cents,
            operation_type="PIX",
            risk_assessment_id=transaction.risk_assessment_id,
            risk_rules_version=transaction.risk_rules_version,
        ),
    )
