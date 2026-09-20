"""link ledger transactions to their risk assessment decision."""

from alembic import op
import sqlalchemy as sa


revision = "tx_003_risk_audit_linkage"
down_revision = "tx_002_idempotency_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ledger_transactions",
        sa.Column("risk_assessment_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "ledger_transactions",
        sa.Column("risk_decision", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "ledger_transactions",
        sa.Column("risk_rules_version", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_ledger_transactions_risk_assessment_id",
        "ledger_transactions",
        ["risk_assessment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ledger_transactions_risk_assessment_id",
        table_name="ledger_transactions",
    )
    op.drop_column("ledger_transactions", "risk_rules_version")
    op.drop_column("ledger_transactions", "risk_decision")
    op.drop_column("ledger_transactions", "risk_assessment_id")
