import argparse
import asyncio
import json
import os
from dataclasses import asdict, dataclass
from enum import Enum

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine


class SchemaState(str, Enum):
    EMPTY = "empty"
    LEGACY_PRE_P0 = "legacy_pre_p0"
    CURRENT_P0 = "current_p0"
    ALEMBIC_MANAGED = "alembic_managed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PreflightResult:
    service: str
    state: str
    tables: tuple[str, ...]
    alembic_versions: tuple[str, ...]
    reason: str


AUTH_COLUMNS = {"id", "tax_id", "full_name", "email", "hashed_password", "is_active", "created_at"}
TX_COLUMNS = {
    "accounts": {"id", "user_id", "account_number", "balance_cents", "is_active", "created_at"},
    "ledger_transactions": {
        "id", "idempotency_key", "source_account_id", "destination_account_id",
        "amount_cents", "transaction_type", "status", "description", "created_at",
    },
    "ledger_entries": {"id", "transaction_id", "account_id", "side", "amount_cents", "created_at"},
    "idempotency_records": {
        "id", "idempotency_key", "user_id", "account_id", "operation_type",
        "request_fingerprint", "transaction_id", "status", "created_at",
    },
}

TX_ALEMBIC_REVISIONS = (
    "tx_001_initial_schema",
    "tx_002_idempotency_ownership",
    "tx_003_risk_audit_linkage",
    "tx_004_transactional_outbox",
    "tx_005_outbox_leases",
)
TX_RISK_COLUMNS = {"risk_assessment_id", "risk_decision", "risk_rules_version"}
OUTBOX_COLUMNS = {
    "id", "aggregate_type", "aggregate_id", "event_type", "event_version",
    "message_key", "payload", "occurred_at", "published_at", "attempts",
    "last_error", "created_at",
}
OUTBOX_LEASE_COLUMNS = {"locked_by", "locked_until"}


def _columns(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def _has_legacy_unique(inspector) -> bool:
    unique_constraint = any(
        set(constraint.get("column_names") or []) == {"idempotency_key"}
        for constraint in inspector.get_unique_constraints("ledger_transactions")
    )
    unique_index = any(
        index.get("unique") is True
        and set(index.get("column_names") or []) == {"idempotency_key"}
        for index in inspector.get_indexes("ledger_transactions")
    )
    return unique_constraint or unique_index


def _has_auth_unique_indexes(inspector) -> bool:
    indexes = {
        index["name"]: index
        for index in inspector.get_indexes("users")
    }
    return all(
        indexes.get(name, {}).get("unique") is True
        and set(indexes[name].get("column_names") or []) == {column}
        for name, column in (("ix_users_email", "email"), ("ix_users_tax_id", "tax_id"))
    )


def _has_scoped_unique(inspector) -> bool:
    target = {"user_id", "account_id", "operation_type", "idempotency_key"}
    unique_constraints = inspector.get_unique_constraints("idempotency_records")
    unique_indexes = inspector.get_indexes("idempotency_records")
    return any(
        set(item.get("column_names") or []) == target
        for item in unique_constraints + unique_indexes
        if item.get("unique", True)
    )


def _has_index(inspector, table: str, name: str, columns: set[str]) -> bool:
    return any(
        index.get("name") == name
        and set(index.get("column_names") or []) == columns
        for index in inspector.get_indexes(table)
    )


def _has_outbox_unique(inspector) -> bool:
    target = {"aggregate_id", "event_type", "event_version"}
    return any(
        set(constraint.get("column_names") or []) == target
        for constraint in inspector.get_unique_constraints("outbox_events")
    )


def _classify_alembic_transactions(inspector, tables: tuple[str, ...], versions: tuple[str, ...]) -> PreflightResult:
    if len(versions) != 1 or versions[0] not in TX_ALEMBIC_REVISIONS:
        return PreflightResult(
            "transactions", SchemaState.UNKNOWN.value, tables, versions,
            "unknown or ambiguous Alembic revision",
        )

    revision = versions[0]
    base = {"accounts", "ledger_transactions", "ledger_entries"}
    current = base | {"idempotency_records"}
    expected_tables = base if revision == "tx_001_initial_schema" else current
    if revision in {"tx_004_transactional_outbox", "tx_005_outbox_leases"}:
        expected_tables = current | {"outbox_events"}
    if set(tables) != expected_tables:
        return PreflightResult(
            "transactions", SchemaState.UNKNOWN.value, tables, versions,
            f"schema tables are incompatible with {revision}",
        )

    expected_columns = dict(TX_COLUMNS)
    if revision == "tx_001_initial_schema":
        expected_columns = {table: TX_COLUMNS[table] for table in base}
    elif revision in {"tx_003_risk_audit_linkage", "tx_004_transactional_outbox", "tx_005_outbox_leases"}:
        expected_columns["ledger_transactions"] = TX_COLUMNS["ledger_transactions"] | TX_RISK_COLUMNS
    if revision in {"tx_004_transactional_outbox", "tx_005_outbox_leases"}:
        expected_columns["outbox_events"] = OUTBOX_COLUMNS | (
            OUTBOX_LEASE_COLUMNS if revision == "tx_005_outbox_leases" else set()
        )
    if any(_columns(inspector, table) != columns for table, columns in expected_columns.items()):
        return PreflightResult(
            "transactions", SchemaState.UNKNOWN.value, tables, versions,
            f"schema columns are incompatible with {revision}",
        )

    if revision == "tx_001_initial_schema" and not _has_legacy_unique(inspector):
        return PreflightResult(
            "transactions", SchemaState.UNKNOWN.value, tables, versions,
            "tx_001 idempotency constraint is missing",
        )
    if revision in TX_ALEMBIC_REVISIONS[1:] and (_has_legacy_unique(inspector) or not _has_scoped_unique(inspector)):
        return PreflightResult(
            "transactions", SchemaState.UNKNOWN.value, tables, versions,
            "scoped idempotency constraint is incompatible",
        )
    if revision == "tx_003_risk_audit_linkage" and not _has_index(
        inspector, "ledger_transactions", "ix_ledger_transactions_risk_assessment_id", {"risk_assessment_id"}
    ):
        return PreflightResult(
            "transactions", SchemaState.UNKNOWN.value, tables, versions,
            "Risk linkage index is missing",
        )
    if revision in {"tx_004_transactional_outbox", "tx_005_outbox_leases"}:
        if not _has_outbox_unique(inspector) or not _has_index(
            inspector, "outbox_events", "idx_outbox_pending", {"published_at", "occurred_at", "attempts"}
        ):
            return PreflightResult(
                "transactions", SchemaState.UNKNOWN.value, tables, versions,
                "transactional outbox invariants are missing",
            )
    if revision == "tx_005_outbox_leases" and not _has_index(
        inspector, "outbox_events", "idx_outbox_claimable", {"published_at", "locked_until", "occurred_at"}
    ):
        return PreflightResult(
            "transactions", SchemaState.UNKNOWN.value, tables, versions,
            "outbox lease invariant is missing",
        )

    return PreflightResult(
        "transactions", SchemaState.ALEMBIC_MANAGED.value, tables, versions,
        f"schema is compatible with {revision}",
    )


def _inspect_sync(connection, service: str) -> PreflightResult:
    inspector = inspect(connection)
    all_tables = set(inspector.get_table_names())
    tables = tuple(sorted(all_tables - {"alembic_version"}))
    versions = tuple(
        row[0]
        for row in connection.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num"))
    ) if "alembic_version" in all_tables else ()

    if service == "auth":
        if not tables:
            return PreflightResult(service, SchemaState.EMPTY.value, tables, versions, "no application tables")
        if (
            set(tables) == {"users"}
            and _columns(inspector, "users") == AUTH_COLUMNS
            and _has_auth_unique_indexes(inspector)
        ):
            return PreflightResult(service, SchemaState.CURRENT_P0.value, tables, versions, "users schema is compatible")
        return PreflightResult(service, SchemaState.UNKNOWN.value, tables, versions, "unexpected Auth tables or columns")

    if versions:
        return _classify_alembic_transactions(inspector, tables, versions)

    base = {"accounts", "ledger_transactions", "ledger_entries"}
    current = base | {"idempotency_records"}
    if not tables:
        return PreflightResult(service, SchemaState.EMPTY.value, tables, versions, "no application tables")
    if set(tables) == base and all(_columns(inspector, table) == TX_COLUMNS[table] for table in base):
        if _has_legacy_unique(inspector):
            return PreflightResult(service, SchemaState.LEGACY_PRE_P0.value, tables, versions, "pre-P0 global idempotency key")
        return PreflightResult(service, SchemaState.UNKNOWN.value, tables, versions, "legacy tables without expected unique key")
    if set(tables) == current and all(_columns(inspector, table) == TX_COLUMNS[table] for table in current):
        if not _has_scoped_unique(inspector) or _has_legacy_unique(inspector):
            return PreflightResult(service, SchemaState.UNKNOWN.value, tables, versions, "idempotency constraints are incompatible")
        return PreflightResult(service, SchemaState.CURRENT_P0.value, tables, versions, "post-P0 schema is compatible")
    return PreflightResult(service, SchemaState.UNKNOWN.value, tables, versions, "unexpected Transactions tables or columns")


async def classify(database_url: str, service: str) -> PreflightResult:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(_inspect_sync, service)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", choices=("auth", "transactions"), required=True)
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    result = asyncio.run(classify(database_url, args.service))
    print(json.dumps(asdict(result), ensure_ascii=False))
    if result.state == SchemaState.UNKNOWN.value:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
