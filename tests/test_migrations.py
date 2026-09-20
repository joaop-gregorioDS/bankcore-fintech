import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()
