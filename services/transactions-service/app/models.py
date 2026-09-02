import uuid
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    account_number = Column(String(20), unique=True, nullable=False, index=True)
    balance_cents = Column(BigInteger, default=1000000, nullable=False) # R$ 10.000 inicial
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key = Column(String(100), unique=True, nullable=False, index=True)
    source_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    destination_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    amount_cents = Column(BigInteger, nullable=False)
    transaction_type = Column(String(20), nullable=False)
    status = Column(String(20), default="COMPLETED", nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_ledger_accounts", "source_account_id", "destination_account_id"),
    )
