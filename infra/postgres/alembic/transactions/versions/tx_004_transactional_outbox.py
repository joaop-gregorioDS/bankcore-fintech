"""Create the transactional outbox for completed PIX events."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "tx_004_transactional_outbox"
down_revision = "tx_003_risk_audit_linkage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_type", sa.String(length=50), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("message_key", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "aggregate_id",
            "event_type",
            "event_version",
            name="uq_outbox_aggregate_event_version",
        ),
    )
    op.create_index(
        "idx_outbox_pending",
        "outbox_events",
        ["published_at", "occurred_at", "attempts"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_outbox_pending", table_name="outbox_events")
    op.drop_table("outbox_events")
