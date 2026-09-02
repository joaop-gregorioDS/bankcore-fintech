from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class AccountCreateRequest(BaseModel):
    user_id: UUID

class AccountResponse(BaseModel):
    id: UUID
    user_id: UUID
    account_number: str
    balance_reais: float
    is_active: bool

class DepositRequest(BaseModel):
    account_id: UUID
    amount_reais: float = Field(..., gt=0)
    idempotency_key: str

class TransferRequest(BaseModel):
    source_account_id: UUID
    destination_account_id: UUID
    amount_reais: float = Field(..., gt=0)
    idempotency_key: str
    description: str | None = None

class PixTransferRequest(BaseModel):
    source_account_id: UUID
    destination_key: str
    amount_reais: float = Field(..., gt=0)
    idempotency_key: str
    description: str | None = None

class TransactionResponse(BaseModel):
    transaction_id: UUID
    idempotency_key: str
    source_account_id: UUID | None = None
    destination_account_id: UUID | None = None
    amount_reais: float
    transaction_type: str
    direction: str  # "CREDIT" ou "DEBIT"
    status: str
    created_at: datetime
    description: str | None = None
