from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")
BIGINT_MAX_CENTS = (1 << 63) - 1
MAX_AMOUNT_CENTS = 99_999_999_999_999


def reais_to_cents(amount: Decimal) -> int:
    if not isinstance(amount, Decimal):
        raise TypeError("Valor monetário deve ser Decimal.")
    if not amount.is_finite() or amount <= 0:
        raise ValueError("Valor monetário deve ser finito e positivo.")

    normalized = amount.quantize(CENT, rounding=ROUND_HALF_UP)
    if normalized != amount:
        raise ValueError("Valor monetário deve ter no máximo duas casas decimais.")
    cents = int(normalized * 100)
    if cents > MAX_AMOUNT_CENTS:
        raise ValueError("Valor monetário excede o limite de negócio.")
    if cents > BIGINT_MAX_CENTS:
        raise OverflowError("Valor monetário excede o limite de BIGINT.")
    return cents


def cents_to_reais(amount_cents: int) -> Decimal:
    if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
        raise TypeError("Centavos devem ser um inteiro.")
    return (Decimal(amount_cents) / Decimal(100)).quantize(CENT)
