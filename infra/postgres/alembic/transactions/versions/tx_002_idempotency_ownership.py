"""Move idempotency ownership into a scoped record.

Revision ID: tx_002_idempotency_ownership
Revises: tx_001_initial_schema
"""

import hashlib

from alembic import op
import sqlalchemy as sa


revision = "tx_002_idempotency_ownership"
down_revision = "tx_001_initial_schema"
branch_labels = None
depends_on = None


def _legacy_transactions(bind):
    rows = bind.execute(
        sa.text(
            """
            SELECT
                lt.id,
                lt.idempotency_key,
                lt.transaction_type,
                lt.status,
                lt.source_account_id,
                lt.destination_account_id,
                CASE
                    WHEN lt.transaction_type = 'DEPOSIT' THEN dst.user_id
                    ELSE src.user_id
                END AS user_id,
                CASE
                    WHEN lt.transaction_type = 'DEPOSIT' THEN lt.destination_account_id
                    ELSE lt.source_account_id
                END AS account_id
            FROM ledger_transactions lt
            LEFT JOIN accounts src ON src.id = lt.source_account_id
            LEFT JOIN accounts dst ON dst.id = lt.destination_account_id
            ORDER BY lt.id
            """
        )
    ).mappings().all()

    seen = set()
    for row in rows:
        scope = (
            row["user_id"],
            row["account_id"],
            row["transaction_type"],
            row["idempotency_key"],
        )
        valid_type = row["transaction_type"] in {"DEPOSIT", "TRANSFER", "WITHDRAWAL"}
        if (
            not valid_type
            or row["status"] != "COMPLETED"
            or row["user_id"] is None
            or row["account_id"] is None
            or scope in seen
        ):
            raise RuntimeError(
                "Ambiguous legacy idempotency context; migration aborted without changes."
            )
        seen.add(scope)
    return rows


def upgrade() -> None:
    bind = op.get_bind()
    legacy_rows = _legacy_transactions(bind)

    bind.execute(
        sa.text(
            "ALTER TABLE ledger_transactions "
            "DROP CONSTRAINT IF EXISTS ledger_transactions_idempotency_key_key"
        )
    )
    bind.execute(
        sa.text(
            "DROP INDEX IF EXISTS idx_ledger_idempotency_key"
        )
    )

    inspector = sa.inspect(bind)
    if "idempotency_records" not in inspector.get_table_names():
        op.create_table(
            "idempotency_records",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("idempotency_key", sa.String(length=100), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("account_id", sa.Uuid(), nullable=False),
            sa.Column("operation_type", sa.String(length=20), nullable=False),
            sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
            sa.Column("transaction_id", sa.Uuid(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["transaction_id"], ["ledger_transactions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "account_id",
                "operation_type",
                "idempotency_key",
                name="uq_idempotency_scope",
            ),
        )

    for index_name, column_name in (
        ("ix_idempotency_records_user_id", "user_id"),
        ("ix_idempotency_records_account_id", "account_id"),
    ):
        bind.execute(
            sa.text(
                f"CREATE INDEX IF NOT EXISTS {index_name} "
                f"ON idempotency_records ({column_name})"
            )
        )
    bind.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_idempotency_transaction "
            "ON idempotency_records (transaction_id)"
        )
    )

    # Original request payloads are not recoverable from the legacy ledger.
    # Historical operations are sealed with a deterministic marker, never guessed.
    for row in legacy_rows:
        marker = hashlib.sha256(f"legacy:{row['id']}".encode("utf-8")).hexdigest()
        bind.execute(
            sa.text(
                """
                INSERT INTO idempotency_records
                    (id, idempotency_key, user_id, account_id, operation_type,
                     request_fingerprint, transaction_id, status, created_at)
                VALUES
                    (:id, :idempotency_key, :user_id, :account_id, :operation_type,
                     :request_fingerprint, :transaction_id, 'COMPLETED',
                     CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, account_id, operation_type, idempotency_key)
                DO NOTHING
                """
            ),
            {
                "id": row["id"],
                "idempotency_key": row["idempotency_key"],
                "user_id": row["user_id"],
                "account_id": row["account_id"],
                "operation_type": row["transaction_type"],
                "request_fingerprint": marker,
                "transaction_id": row["id"],
            },
        )


def downgrade() -> None:
    op.drop_index("idx_idempotency_transaction", table_name="idempotency_records")
    op.drop_index("ix_idempotency_records_account_id", table_name="idempotency_records")
    op.drop_index("ix_idempotency_records_user_id", table_name="idempotency_records")
    op.drop_constraint("uq_idempotency_scope", table_name="idempotency_records", type_="unique")
    op.drop_table("idempotency_records")
    op.create_unique_constraint(
        "ledger_transactions_idempotency_key_key",
        "ledger_transactions",
        ["idempotency_key"],
    )
