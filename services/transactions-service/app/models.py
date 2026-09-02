import uuid
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.database import Base

class TransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    TRANSFER = "TRANSFER"
    PIX = "PIX"

class TransactionStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    account_number = Column(String(20), unique=True, index=True, nullable=False)
    balance_cents = Column(BigInteger, default=0, nullable=False) # Saldo em centavos
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key = Column(String(64), unique=True, index=True, nullable=False)
    source_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    destination_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    transaction_type = Column(String(20), nullable=False)
    status = Column(String(20), default=TransactionStatus.COMPLETED)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
