import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User
from app.security import hash_password

JOAO_USER_ID = uuid.UUID("0f2dba40-cad0-45ab-9901-eaf9ecd72f5e")
MARIA_USER_ID = uuid.UUID("a7b8c9d0-e1f2-4a3b-9c4d-5e6f708192a3")

DEMO_USERS = [
    {
        "id": JOAO_USER_ID,
        "tax_id": "33548376835",
        "full_name": "João Paulo Gregorio de Souza",
        "email": "joao.paulo@vortexsoftware.com.br",
        "password": "teste123456",
    },
    {
        "id": MARIA_USER_ID,
        "tax_id": "12345678900",
        "full_name": "Maria Silva Santos",
        "email": "maria.silva@vortexsoftware.com.br",
        "password": "teste123456",
    },
]


def normalize_tax_id(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


async def seed_demo_users(db: AsyncSession) -> None:
    for spec in DEMO_USERS:
        result = await db.execute(select(User).where(User.tax_id == spec["tax_id"]))
        if result.scalars().first():
            continue
        db.add(
            User(
                id=spec["id"],
                tax_id=spec["tax_id"],
                full_name=spec["full_name"],
                email=spec["email"],
                hashed_password=hash_password(spec["password"]),
            )
        )
    await db.commit()
