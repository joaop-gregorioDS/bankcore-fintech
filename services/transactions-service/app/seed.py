import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Account

SETTLEMENT_ACCOUNT_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
SETTLEMENT_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000000")
SETTLEMENT_ACCOUNT_NUMBER = "00000-0"

JOAO_USER_ID = uuid.UUID("0f2dba40-cad0-45ab-9901-eaf9ecd72f5e")
MARIA_USER_ID = uuid.UUID("a7b8c9d0-e1f2-4a3b-9c4d-5e6f708192a3")

DEMO_WELCOME_CENTS = {
    "33548376835": 1_845_080,
    "12345678900": 1_287_040,
}

DEFAULT_WELCOME_CENTS = 1_000_000


def is_settlement(account: Account) -> bool:
    return account.id == SETTLEMENT_ACCOUNT_ID or account.account_number == SETTLEMENT_ACCOUNT_NUMBER


def welcome_balance_cents(tax_id: str | None) -> int:
    if not tax_id:
        return DEFAULT_WELCOME_CENTS
    digits = "".join(ch for ch in tax_id if ch.isdigit())
    return DEMO_WELCOME_CENTS.get(digits, DEFAULT_WELCOME_CENTS)


async def seed_settlement_account(db: AsyncSession) -> Account:
    result = await db.execute(select(Account).where(Account.id == SETTLEMENT_ACCOUNT_ID))
    existing = result.scalars().first()
    if existing:
        return existing

    by_number = await db.execute(select(Account).where(Account.account_number == SETTLEMENT_ACCOUNT_NUMBER))
    existing_number = by_number.scalars().first()
    if existing_number:
        return existing_number

    acc = Account(
        id=SETTLEMENT_ACCOUNT_ID,
        user_id=SETTLEMENT_USER_ID,
        account_number=SETTLEMENT_ACCOUNT_NUMBER,
        balance_cents=0,
        is_active=True,
    )
    db.add(acc)
    await db.commit()
    await db.refresh(acc)
    return acc


async def seed_demo_accounts(db: AsyncSession) -> None:
    await seed_settlement_account(db)

    specs = [
        (JOAO_USER_ID, "77412-7", DEMO_WELCOME_CENTS["33548376835"]),
        (MARIA_USER_ID, "88921-3", DEMO_WELCOME_CENTS["12345678900"]),
    ]
    for user_id, acc_num, cents in specs:
        result = await db.execute(
            select(Account).where(Account.user_id == user_id).order_by(Account.created_at.asc())
        )
        if result.scalars().first():
            continue
        taken = await db.execute(select(Account).where(Account.account_number == acc_num))
        number = acc_num if not taken.scalars().first() else None
        acc = Account(
            user_id=user_id,
            account_number=number or f"{user_id.hex[:5]}-{user_id.hex[5]}",
            balance_cents=cents,
            is_active=True,
        )
        db.add(acc)
    await db.commit()
