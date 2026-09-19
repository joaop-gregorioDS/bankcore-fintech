import asyncio
import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config


config = context.config
database_url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
if not database_url:
    raise RuntimeError("DATABASE_URL is required for Transactions migrations.")
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
os.environ.setdefault("DATABASE_URL", database_url)
os.environ.setdefault("REDIS_URL", "redis://unused")
os.environ.setdefault("JWT_ACTIVE_KID", "migration")
os.environ.setdefault("AUTH_SERVICE_TOKEN", "migration")

service_root = next(
    (
        candidate / "services/transactions-service"
        for candidate in Path(__file__).resolve().parents
        if (candidate / "services/transactions-service").exists()
    ),
    Path("/app"),
)
sys.path.insert(0, str(service_root))

from app.database import Base  # noqa: E402
from app import models  # noqa: F401,E402


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
