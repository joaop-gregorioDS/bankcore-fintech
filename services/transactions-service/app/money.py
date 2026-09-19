from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def reais_to_cents(amount: Decimal) -> int:
    if not isinstance(amount, Decimal):
        raise TypeError("Valor monetário deve ser Decimal.")
    if not amount.is_finite() or amount <= 0:
        raise ValueError("Valor monetário deve ser finito e positivo.")

    normalized = amount.quantize(CENT, rounding=ROUND_HALF_UP)
    if normalized != amount:
        raise ValueError("Valor monetário deve ter no máximo duas casas decimais.")
    return int(normalized * 100)


def cents_to_reais(amount_cents: int) -> Decimal:
    if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
        raise TypeError("Centavos devem ser um inteiro.")
    return (Decimal(amount_cents) / Decimal(100)).quantize(CENT)
