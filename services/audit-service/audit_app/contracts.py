from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InvalidAuditEvent(ValueError):
    """Raised when a Kafka payload is not a valid transaction.completed.v1 event."""


class TransactionCompletedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: UUID
    source_account_id: UUID
    destination_account_id: UUID
    amount_cents: int = Field(gt=0)
    operation_type: Literal["PIX"]
    risk_assessment_id: UUID
    risk_rules_version: str = Field(min_length=1, max_length=64)


class TransactionCompletedV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_type: Literal["transaction.completed"]
    event_version: Literal[1]
    occurred_at: datetime
    producer: Literal["transactions-service"]
    correlation_id: UUID
    data: TransactionCompletedData


def validate_transaction_completed(payload: dict) -> TransactionCompletedV1:
    try:
        return TransactionCompletedV1.model_validate(payload)
    except Exception as error:
        raise InvalidAuditEvent("Invalid transaction.completed.v1 payload") from error
