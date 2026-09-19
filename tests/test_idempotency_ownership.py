import importlib.util
import unittest
from pathlib import Path
from uuid import UUID


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "services/transactions-service/app"
USER_ID = UUID("00000000-0000-0000-0000-000000000001")
ACCOUNT_ID = UUID("00000000-0000-0000-0000-000000000002")
DESTINATION_ID = UUID("00000000-0000-0000-0000-000000000003")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class IdempotencyOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_module("idempotency_policy", APP / "idempotency.py")

    def _fingerprint(self, **overrides):
        values = {
            "user_id": USER_ID,
            "account_id": ACCOUNT_ID,
            "operation_type": "TRANSFER",
            "idempotency_key": "ABC123",
            "amount_cents": 10_000,
            "destination_account_id": DESTINATION_ID,
            "description": "Transferência Pix BankCore",
        }
        values.update(overrides)
        return self.policy.build_request_fingerprint(**values)

    def test_fingerprint_is_stable_for_same_logical_payload(self):
        self.assertEqual(self._fingerprint(), self._fingerprint())

    def test_payload_changes_are_detected(self):
        baseline = self._fingerprint()
        for field, value in (
            ("amount_cents", 50_000),
            ("destination_account_id", UUID("00000000-0000-0000-0000-000000000004")),
            ("description", "Outro payload"),
        ):
            with self.subTest(field=field):
                self.assertNotEqual(baseline, self._fingerprint(**{field: value}))

    def test_scope_changes_are_detected(self):
        baseline = self._fingerprint()
        for field, value in (
            ("user_id", UUID("00000000-0000-0000-0000-000000000010")),
            ("account_id", UUID("00000000-0000-0000-0000-000000000011")),
            ("operation_type", "DEPOSIT"),
            ("idempotency_key", "OTHER-KEY"),
        ):
            with self.subTest(field=field):
                self.assertNotEqual(baseline, self._fingerprint(**{field: value}))

    def test_server_owns_scope_and_database_defines_unique_boundary(self):
        route_source = (APP / "routes/transactions.py").read_text(encoding="utf-8")
        model_source = (APP / "models.py").read_text(encoding="utf-8")
        migration_source = (ROOT / "infra/postgres/alembic/transactions/versions/tx_002_idempotency_ownership.py").read_text(encoding="utf-8")

        self.assertIn('user_id = UUID(current_user["sub"])', route_source)
        self.assertIn("user_id=user_id", route_source)
        self.assertIn('UniqueConstraint(\n            "user_id",\n            "account_id",\n            "operation_type",\n            "idempotency_key"', model_source)
        self.assertIn("uq_idempotency_scope", migration_source)

    def test_ledger_uses_idempotency_record_and_fingerprint(self):
        ledger_source = (APP / "services/ledger.py").read_text(encoding="utf-8")
        self.assertIn("IdempotencyRecord", ledger_source)
        self.assertIn("build_request_fingerprint", ledger_source)
        self.assertIn("_complete_idempotency(record, tx)", ledger_source)
        self.assertIn("Chave de idempotência reutilizada com payload diferente", ledger_source)


if __name__ == "__main__":
    unittest.main()
