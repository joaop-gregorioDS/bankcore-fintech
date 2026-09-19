import importlib.util
import unittest
from decimal import Decimal
from datetime import datetime
from pathlib import Path

from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from uuid import UUID


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

    def test_business_limit_stays_below_bigint_and_rejects_next_cent(self):
        maximum = Decimal("999999999999.99")
        self.assertEqual(self.money.reais_to_cents(maximum), 99_999_999_999_999)
        self.assertLessEqual(self.money.MAX_AMOUNT_CENTS, self.money.BIGINT_MAX_CENTS)
        with self.assertRaises(ValueError):
            self.money.reais_to_cents(Decimal("1000000000000.00"))

        request = self.schemas.DepositRequest(
            account_id="00000000-0000-0000-0000-000000000001",
            amount_reais="999999999999.99",
            idempotency_key="maximum-input",
        )
        self.assertEqual(self.money.reais_to_cents(request.amount_reais), 99_999_999_999_999)

    def test_scientific_notation_is_normalized_when_scale_is_valid(self):
        request = self.schemas.DepositRequest(
            account_id="00000000-0000-0000-0000-000000000001",
            amount_reais="1e2",
            idempotency_key="scientific-input",
        )
        self.assertEqual(self.money.reais_to_cents(request.amount_reais), 10_000)

        with self.assertRaises(ValidationError):
            self.schemas.DepositRequest(
                account_id="00000000-0000-0000-0000-000000000001",
                amount_reais="1e-3",
                idempotency_key="scientific-too-precise",
            )

    def test_schema_rejects_invalid_scale_and_non_finite_values(self):
        base = {
            "account_id": "00000000-0000-0000-0000-000000000001",
            "idempotency_key": "money-test",
        }
        for value in ("0", "-0.00", "0.001", "NaN", "Infinity", "-1"):
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

    def test_numeric_response_preserves_cent_precision_at_http_edge(self):
        values = (Decimal("0.10"), Decimal("10.10"), Decimal("999999.99"), Decimal("999999999999.99"))
        for value in values:
            with self.subTest(value=value):
                response = self.schemas.TransactionResponse(
                    transaction_id=UUID("00000000-0000-0000-0000-000000000001"),
                    idempotency_key="response-test",
                    amount_reais=float(value),
                    transaction_type="TRANSFER",
                    direction="DEBIT",
                    status="COMPLETED",
                    created_at=datetime(2026, 1, 1),
                )
                encoded = jsonable_encoder(response)["amount_reais"]
                self.assertIsInstance(encoded, float)
                self.assertEqual(
                    Decimal(str(encoded)).quantize(Decimal("0.01")),
                    value,
                )


if __name__ == "__main__":
    unittest.main()
