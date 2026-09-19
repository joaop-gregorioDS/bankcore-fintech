import argparse
import asyncio
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from preflight import SchemaState, classify


ROOT = Path(__file__).resolve().parent


def _config(service: str) -> Config:
    config_path = ROOT / "alembic" / service / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("script_location", str(config_path.parent).replace("%", "%%"))
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"].replace("%", "%%"))
    return config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", choices=("auth", "transactions"), required=True)
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    result = asyncio.run(classify(database_url, args.service))
    print(f"preflight: {result.service}={result.state} ({result.reason})")
    if result.state == SchemaState.UNKNOWN.value:
        raise SystemExit("Migration aborted: unknown or inconsistent schema.")

    config = _config(args.service)
    if args.service == "auth":
        initial = "auth_001_initial_users"
    else:
        initial = "tx_001_initial_schema"

    if result.state == SchemaState.EMPTY.value:
        command.upgrade(config, "head")
    elif result.state == SchemaState.LEGACY_PRE_P0.value:
        if result.alembic_versions and set(result.alembic_versions) != {initial}:
            raise SystemExit("Migration aborted: legacy schema has an unexpected Alembic version.")
        if not result.alembic_versions:
            command.stamp(config, initial)
        command.upgrade(config, "head")
    elif result.state == SchemaState.CURRENT_P0.value:
        expected = {"auth": "auth_001_initial_users", "transactions": "tx_002_idempotency_ownership"}[args.service]
        if result.alembic_versions and set(result.alembic_versions) != {expected}:
            raise SystemExit("Migration aborted: current schema has an unexpected Alembic version.")
        if not result.alembic_versions:
            command.stamp(config, expected)
        else:
            command.upgrade(config, "head")
    else:  # pragma: no cover
        raise SystemExit("Migration aborted.")


if __name__ == "__main__":
    main()
