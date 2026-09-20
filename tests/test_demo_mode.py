import ast
import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DemoModePolicyTests(unittest.TestCase):
    def test_config_defaults_to_false_and_accepts_explicit_true(self):
        base_env = {
            "DATABASE_URL": "postgresql+asyncpg://test",
            "REDIS_URL": "redis://test",
            "JWT_ACTIVE_KID": "test-key",
            "AUTH_SERVICE_TOKEN": "test-service-token",
            "RATE_LIMIT_KEY_SECRET": "test-rate-limit-key",
        }
        with patch.dict(os.environ, base_env, clear=False):
            os.environ.pop("DEMO_MODE", None)
            auth_config = load_module(
                "auth_config_default",
                ROOT / "services/auth-service/app/config.py",
            )
            self.assertFalse(auth_config.settings.DEMO_MODE)

            os.environ["DEMO_MODE"] = "true"
            transactions_config = load_module(
                "transactions_config_true",
                ROOT / "services/transactions-service/app/config.py",
            )
            self.assertTrue(transactions_config.settings.DEMO_MODE)

    def test_demo_mode_is_strictly_opt_in(self):
        auth_policy = load_module(
            "auth_demo_mode",
            ROOT / "services/auth-service/app/demo_mode.py",
        )
        transactions_policy = load_module(
            "transactions_demo_mode",
            ROOT / "services/transactions-service/app/demo_mode.py",
        )

        self.assertFalse(auth_policy.is_demo_mode_enabled(False))
        self.assertTrue(auth_policy.is_demo_mode_enabled(True))
        self.assertFalse(transactions_policy.is_demo_mode_enabled(False))
        self.assertTrue(transactions_policy.is_demo_mode_enabled(True))

    def test_deposit_is_hidden_outside_demo_mode(self):
        transactions_policy = load_module(
            "transactions_demo_mode_for_deposit",
            ROOT / "services/transactions-service/app/demo_mode.py",
        )

        with self.assertRaises(transactions_policy.HTTPException) as context:
            transactions_policy.require_demo_mode(False)
        self.assertEqual(context.exception.status_code, 404)
        self.assertIsNone(transactions_policy.require_demo_mode(True))

    def test_startup_and_account_paths_use_the_guardrail(self):
        auth_main = (ROOT / "services/auth-service/app/main.py").read_text(encoding="utf-8")
        transactions_main = (ROOT / "services/transactions-service/app/main.py").read_text(encoding="utf-8")
        transactions_route = (ROOT / "services/transactions-service/app/routes/transactions.py").read_text(encoding="utf-8")
        accounts_route = (ROOT / "services/transactions-service/app/routes/accounts.py").read_text(encoding="utf-8")

        for source in (auth_main, transactions_main):
            ast.parse(source)
            self.assertIn("if is_demo_mode_enabled(settings.DEMO_MODE):", source)
        self.assertIn("require_demo_mode(settings.DEMO_MODE)", transactions_route)
        self.assertIn("dependencies=[Depends(require_demo_deposit_mode)]", transactions_route)
        self.assertIn("if settings.DEMO_MODE", accounts_route)


if __name__ == "__main__":
    unittest.main()
