import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from audit_app.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String(100), nullable=False)
    event_version = Column(Integer, nullable=False)
    transaction_id = Column(UUID(as_uuid=True), nullable=False)
    payload = Column(JSONB, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    consumer_version = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("event_id", name="uq_audit_events_event_id"),
        Index("idx_audit_events_transaction_id", "transaction_id"),
        Index("idx_audit_events_occurred_at", "occurred_at"),
    )
