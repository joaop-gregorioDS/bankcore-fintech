import unittest
import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_PATH = ROOT / "infra/postgres/preflight.py"
PREFLIGHT_SPEC = importlib.util.spec_from_file_location("bankcore_preflight", PREFLIGHT_PATH)
PREFLIGHT = importlib.util.module_from_spec(PREFLIGHT_SPEC)
assert PREFLIGHT_SPEC and PREFLIGHT_SPEC.loader
try:
    import sqlalchemy  # noqa: F401
except ModuleNotFoundError:
    sqlalchemy_stub = types.ModuleType("sqlalchemy")
    sqlalchemy_stub.inspect = lambda connection: None
    sqlalchemy_stub.text = lambda statement: statement
    sqlalchemy_ext_stub = types.ModuleType("sqlalchemy.ext")
    sqlalchemy_asyncio_stub = types.ModuleType("sqlalchemy.ext.asyncio")
    sqlalchemy_asyncio_stub.create_async_engine = lambda *args, **kwargs: None
    sqlalchemy_ext_stub.asyncio = sqlalchemy_asyncio_stub
    sys.modules["sqlalchemy"] = sqlalchemy_stub
    sys.modules["sqlalchemy.ext"] = sqlalchemy_ext_stub
    sys.modules["sqlalchemy.ext.asyncio"] = sqlalchemy_asyncio_stub
PREFLIGHT_SPEC.loader.exec_module(PREFLIGHT)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)


class FakeConnection:
    def __init__(self, versions):
        self.versions = versions

    def execute(self, statement):
        return FakeResult([(version,) for version in self.versions])


class FakeInspector:
    def __init__(self, columns, indexes=None, unique_constraints=None, include_alembic_version=False):
        self.columns = columns
        self.indexes = indexes or {}
        self.unique_constraints = unique_constraints or {}
        self.include_alembic_version = include_alembic_version

    def get_table_names(self):
        tables = list(self.columns)
        if self.include_alembic_version:
            tables.append("alembic_version")
        return tables

    def get_columns(self, table):
        return [{"name": column} for column in self.columns[table]]

    def get_indexes(self, table):
        return self.indexes.get(table, [])

    def get_unique_constraints(self, table):
        return self.unique_constraints.get(table, [])


def fake_transactions_schema(revision, *, include_alembic_version=False):
    base = {"accounts", "ledger_transactions", "ledger_entries"}
    current = base | {"idempotency_records"}
    columns = {table: set(PREFLIGHT.TX_COLUMNS[table]) for table in current}
    if revision == "tx_001_initial_schema":
        columns.pop("idempotency_records")
    if revision in {"tx_003_risk_audit_linkage", "tx_004_transactional_outbox", "tx_005_outbox_leases"}:
        columns["ledger_transactions"] |= PREFLIGHT.TX_RISK_COLUMNS
    if revision in {"tx_004_transactional_outbox", "tx_005_outbox_leases"}:
        columns["outbox_events"] = set(PREFLIGHT.OUTBOX_COLUMNS)
    if revision == "tx_005_outbox_leases":
        columns["outbox_events"] |= PREFLIGHT.OUTBOX_LEASE_COLUMNS

    indexes = {
        "idempotency_records": [{"name": "uq_idempotency_scope", "column_names": ["user_id", "account_id", "operation_type", "idempotency_key"], "unique": True}],
    }
    unique_constraints = {}
    if revision == "tx_001_initial_schema":
        unique_constraints["ledger_transactions"] = [{"name": "ledger_transactions_idempotency_key_key", "column_names": ["idempotency_key"]}]
    if revision in {"tx_003_risk_audit_linkage", "tx_004_transactional_outbox", "tx_005_outbox_leases"}:
        indexes.setdefault("ledger_transactions", []).append({"name": "ix_ledger_transactions_risk_assessment_id", "column_names": ["risk_assessment_id"], "unique": False})
    if revision in {"tx_004_transactional_outbox", "tx_005_outbox_leases"}:
        unique_constraints["outbox_events"] = [{"name": "uq_outbox_aggregate_event_version", "column_names": ["aggregate_id", "event_type", "event_version"]}]
        indexes["outbox_events"] = [{"name": "idx_outbox_pending", "column_names": ["published_at", "occurred_at", "attempts"], "unique": False}]
    if revision == "tx_005_outbox_leases":
        indexes["outbox_events"].append({"name": "idx_outbox_claimable", "column_names": ["published_at", "locked_until", "occurred_at"], "unique": False})
    return FakeInspector(columns, indexes, unique_constraints, include_alembic_version)


class MigrationContractTests(unittest.TestCase):
    def test_application_and_postgres_tests_do_not_create_schema(self):
        sources = [
            ROOT / "services/auth-service/app/main.py",
            ROOT / "services/transactions-service/app/main.py",
            ROOT / "tests/test_idempotency_postgres.py",
        ]
        for source in sources:
            self.assertNotIn("create_all", source.read_text(encoding="utf-8"))

    def test_two_independent_alembic_contexts_exist(self):
        auth = ROOT / "infra/postgres/alembic/auth"
        transactions = ROOT / "infra/postgres/alembic/transactions"
        self.assertTrue((auth / "env.py").exists())
        self.assertTrue((auth / "versions/auth_001_initial_users.py").exists())
        self.assertTrue((transactions / "env.py").exists())
        self.assertTrue((transactions / "versions/tx_001_initial_schema.py").exists())
        self.assertTrue((transactions / "versions/tx_002_idempotency_ownership.py").exists())
        self.assertTrue((transactions / "versions/tx_003_risk_audit_linkage.py").exists())
        self.assertTrue((transactions / "versions/tx_004_transactional_outbox.py").exists())
        self.assertTrue((transactions / "versions/tx_005_outbox_leases.py").exists())
        audit = ROOT / "infra/postgres/alembic/audit"
        self.assertTrue((audit / "env.py").exists())
        self.assertTrue((audit / "versions/audit_001_audit_events.py").exists())

    def test_manual_migration_is_no_longer_active_source_of_truth(self):
        self.assertFalse((ROOT / "infra/postgres/migrations/001_idempotency_ownership.sql").exists())
        migration = (ROOT / "infra/postgres/alembic/transactions/versions/tx_002_idempotency_ownership.py").read_text(encoding="utf-8")
        self.assertIn("Ambiguous legacy idempotency context", migration)
        self.assertIn("uq_idempotency_scope", migration)

    def test_compose_exposes_explicit_migration_commands(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("migrate-auth:", compose)
        self.assertIn("migrate-transactions:", compose)
        self.assertIn('profiles: ["migration"]', compose)
        self.assertIn("schema is not migrated", (ROOT / "services/auth-service/app/main.py").read_text(encoding="utf-8"))
        self.assertIn("schema is not migrated", (ROOT / "services/transactions-service/app/main.py").read_text(encoding="utf-8"))

    def test_transactions_preflight_accepts_each_known_alembic_revision(self):
        original_inspect = PREFLIGHT.inspect
        try:
            for revision in PREFLIGHT.TX_ALEMBIC_REVISIONS:
                inspector = fake_transactions_schema(revision, include_alembic_version=True)
                PREFLIGHT.inspect = lambda connection, inspector=inspector: inspector
                result = PREFLIGHT._inspect_sync(FakeConnection([revision]), "transactions")
                self.assertEqual(result.state, PREFLIGHT.SchemaState.ALEMBIC_MANAGED.value, revision)
        finally:
            PREFLIGHT.inspect = original_inspect

    def test_transactions_preflight_accepts_p0_without_alembic_version(self):
        inspector = fake_transactions_schema("tx_002_idempotency_ownership")
        original_inspect = PREFLIGHT.inspect
        try:
            PREFLIGHT.inspect = lambda connection: inspector
            result = PREFLIGHT._inspect_sync(FakeConnection([]), "transactions")
            self.assertEqual(result.state, PREFLIGHT.SchemaState.CURRENT_P0.value)
        finally:
            PREFLIGHT.inspect = original_inspect

    def test_transactions_preflight_rejects_unknown_revision(self):
        inspector = fake_transactions_schema("tx_005_outbox_leases", include_alembic_version=True)
        original_inspect = PREFLIGHT.inspect
        try:
            PREFLIGHT.inspect = lambda connection: inspector
            result = PREFLIGHT._inspect_sync(FakeConnection(["tx_999_unknown"]), "transactions")
            self.assertEqual(result.state, PREFLIGHT.SchemaState.UNKNOWN.value)
        finally:
            PREFLIGHT.inspect = original_inspect

    def test_transactions_preflight_rejects_inconsistent_tx005_schema(self):
        inspector = fake_transactions_schema("tx_005_outbox_leases", include_alembic_version=True)
        inspector.columns["outbox_events"].remove("locked_until")
        original_inspect = PREFLIGHT.inspect
        try:
            PREFLIGHT.inspect = lambda connection: inspector
            result = PREFLIGHT._inspect_sync(FakeConnection(["tx_005_outbox_leases"]), "transactions")
            self.assertEqual(result.state, PREFLIGHT.SchemaState.UNKNOWN.value)
        finally:
            PREFLIGHT.inspect = original_inspect


if __name__ == "__main__":
    unittest.main()
