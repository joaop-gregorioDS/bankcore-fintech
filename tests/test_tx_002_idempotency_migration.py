import importlib.util
import sys
import types
import unittest
from pathlib import Path
from uuid import UUID


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = ROOT / "infra/postgres/alembic/transactions/versions/tx_002_idempotency_ownership.py"


def load_migration():
    sqlalchemy_stub = types.ModuleType("sqlalchemy")
    sqlalchemy_stub.text = lambda statement: statement
    alembic_stub = types.ModuleType("alembic")
    alembic_stub.op = types.SimpleNamespace()
    previous_sqlalchemy = sys.modules.get("sqlalchemy")
    previous_alembic = sys.modules.get("alembic")
    sys.modules["sqlalchemy"] = sqlalchemy_stub
    sys.modules["alembic"] = alembic_stub
    try:
        spec = importlib.util.spec_from_file_location("tx_002_idempotency_migration", MIGRATION_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_sqlalchemy is None:
            sys.modules.pop("sqlalchemy", None)
        else:
            sys.modules["sqlalchemy"] = previous_sqlalchemy
        if previous_alembic is None:
            sys.modules.pop("alembic", None)
        else:
            sys.modules["alembic"] = previous_alembic


class LegacyIdempotencyMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.migration = load_migration()

    def legacy_row(self, **overrides):
        row = {
            "id": UUID("00000000-0000-0000-0000-000000000001"),
            "idempotency_key": "legacy-key",
            "transaction_type": "PIX",
            "status": "COMPLETED",
            "source_account_id": UUID("00000000-0000-0000-0000-000000000002"),
            "destination_account_id": UUID("00000000-0000-0000-0000-000000000003"),
            "user_id": UUID("00000000-0000-0000-0000-000000000004"),
            "account_id": UUID("00000000-0000-0000-0000-000000000002"),
        }
        row.update(overrides)
        return row

    def test_legacy_pix_maps_to_current_transfer_idempotency_operation(self):
        row = self.legacy_row()
        seen = set()

        self.migration._validate_legacy_row(row, seen)

        self.assertEqual(self.migration._legacy_operation_type(row["transaction_type"]), "TRANSFER")

    def test_pix_and_transfer_with_same_scope_remain_ambiguous(self):
        pix = self.legacy_row()
        transfer = self.legacy_row(
            id=UUID("00000000-0000-0000-0000-000000000005"),
            transaction_type="TRANSFER",
        )
        seen = set()

        self.migration._validate_legacy_row(pix, seen)
        with self.assertRaisesRegex(RuntimeError, "Ambiguous legacy idempotency context"):
            self.migration._validate_legacy_row(transfer, seen)

    def test_pix_without_distinct_source_and_destination_remains_ambiguous(self):
        source = UUID("00000000-0000-0000-0000-000000000002")
        row = self.legacy_row(destination_account_id=source)

        with self.assertRaisesRegex(RuntimeError, "Ambiguous legacy idempotency context"):
            self.migration._validate_legacy_row(row, set())

    def test_pix_without_source_remains_ambiguous(self):
        row = self.legacy_row(source_account_id=None, account_id=None, user_id=None)

        with self.assertRaisesRegex(RuntimeError, "Ambiguous legacy idempotency context"):
            self.migration._validate_legacy_row(row, set())

    def test_pix_without_destination_remains_ambiguous(self):
        row = self.legacy_row(destination_account_id=None)

        with self.assertRaisesRegex(RuntimeError, "Ambiguous legacy idempotency context"):
            self.migration._validate_legacy_row(row, set())

    def test_unknown_type_remains_fail_closed(self):
        row = self.legacy_row(transaction_type="UNKNOWN")

        with self.assertRaisesRegex(RuntimeError, "Ambiguous legacy idempotency context"):
            self.migration._validate_legacy_row(row, set())


if __name__ == "__main__":
    unittest.main()
