import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, BigInteger, Integer, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base

class TransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"

class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    account_number = Column(String(20), unique=True, nullable=False, index=True)
    balance_cents = Column(BigInteger, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key = Column(String(100), nullable=False, index=True)
    source_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    destination_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    amount_cents = Column(BigInteger, nullable=False)
    transaction_type = Column(String(20), nullable=False)
    status = Column(String(20), default="COMPLETED", nullable=False)
    description = Column(String(255), nullable=True)
    risk_assessment_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    risk_decision = Column(String(16), nullable=True)
    risk_rules_version = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_ledger_accounts", "source_account_id", "destination_account_id"),
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key = Column(String(100), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    operation_type = Column(String(20), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("ledger_transactions.id"), nullable=True)
    status = Column(String(20), nullable=False, default="PROCESSING")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "account_id",
            "operation_type",
            "idempotency_key",
            name="uq_idempotency_scope",
        ),
        Index("idx_idempotency_transaction", "transaction_id"),
    )

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("ledger_transactions.id"), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    side = Column(String(6), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_type = Column(String(50), nullable=False)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String(100), nullable=False)
    event_version = Column(Integer, nullable=False)
    message_key = Column(String(255), nullable=False)
    payload = Column(JSONB, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(String(2000), nullable=True)
    locked_by = Column(String(100), nullable=True)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "aggregate_id",
            "event_type",
            "event_version",
            name="uq_outbox_aggregate_event_version",
        ),
        Index(
            "idx_outbox_pending",
            "published_at",
            "occurred_at",
            "attempts",
        ),
    )
