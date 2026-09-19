import importlib.util
import unittest
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
SERVICE_APP = ROOT / "services/transactions-service/app"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MonetaryCorrectnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.money = load_module("money_policy", SERVICE_APP / "money.py")
        cls.schemas = load_module("money_schemas", SERVICE_APP / "schemas.py")

    def test_decimal_values_convert_exactly_to_cents(self):
        self.assertEqual(self.money.reais_to_cents(Decimal("10.10")), 1010)
        self.assertEqual(self.money.reais_to_cents(Decimal("0.01")), 1)
        self.assertEqual(self.money.cents_to_reais(1010), Decimal("10.10"))

        request = self.schemas.DepositRequest(
            account_id="00000000-0000-0000-0000-000000000001",
            amount_reais=10.10,
            idempotency_key="numeric-input",
        )
        self.assertEqual(self.money.reais_to_cents(request.amount_reais), 1010)

    def test_schema_rejects_invalid_scale_and_non_finite_values(self):
        base = {
            "account_id": "00000000-0000-0000-0000-000000000001",
            "idempotency_key": "money-test",
        }
        for value in ("0", "0.001", "NaN", "Infinity", "-1"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    self.schemas.DepositRequest(**base, amount_reais=value)

    def test_conversion_rejects_non_decimal_and_excess_precision(self):
        with self.assertRaises(TypeError):
            self.money.reais_to_cents(10.10)
        with self.assertRaises(ValueError):
            self.money.reais_to_cents(Decimal("0.001"))

    def test_one_thousand_operations_have_no_binary_float_drift(self):
        total_cents = sum(
            self.money.reais_to_cents(Decimal("0.01"))
            for _ in range(1000)
        )
        self.assertEqual(total_cents, 1000)


if __name__ == "__main__":
    unittest.main()
