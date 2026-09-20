"""Create the audit consumer's idempotent event store."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "audit_001_audit_events"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumer_version", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_audit_events_event_id"),
    )
    op.create_index("idx_audit_events_transaction_id", "audit_events", ["transaction_id"])
    op.create_index("idx_audit_events_occurred_at", "audit_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_events_occurred_at", table_name="audit_events")
    op.drop_index("idx_audit_events_transaction_id", table_name="audit_events")
    op.drop_table("audit_events")
