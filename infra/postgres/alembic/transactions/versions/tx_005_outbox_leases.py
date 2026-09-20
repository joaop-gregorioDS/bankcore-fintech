"""Add short-lived publisher leases to outbox events."""

from alembic import op
import sqlalchemy as sa


revision = "tx_005_outbox_leases"
down_revision = "tx_004_transactional_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column("locked_by", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "outbox_events",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_outbox_claimable",
        "outbox_events",
        ["published_at", "locked_until", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_outbox_claimable", table_name="outbox_events")
    op.drop_column("outbox_events", "locked_until")
    op.drop_column("outbox_events", "locked_by")
