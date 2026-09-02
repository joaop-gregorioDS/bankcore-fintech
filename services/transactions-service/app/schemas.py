from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional

class AccountCreateRequest(BaseModel):
    user_id: UUID

class DepositRequest(BaseModel):
    account_id: UUID
    amount_reais: float = Field(..., gt=0, description="Valor do depósito em Reais (ex: 150.50)")
    idempotency_key: str = Field(..., description="Chave única da transação para evitar duplicidade")

class TransferRequest(BaseModel):
    source_account_id: UUID
    destination_account_id: UUID
    amount_reais: float = Field(..., gt=0, description="Valor da transferência em Reais")
    idempotency_key: str = Field(..., description="Chave única de idempotência")
    description: Optional[str] = "Transferência Pix BankCore"

class AccountResponse(BaseModel):
    id: UUID
    user_id: UUID
    account_number: str
    balance_reais: float
    is_active: bool

class TransactionResponse(BaseModel):
    transaction_id: UUID
    idempotency_key: str
    amount_reais: float
    transaction_type: str
    status: str
    created_at: datetime
    description: Optional[str]
