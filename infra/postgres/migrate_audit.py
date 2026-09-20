import os
from pathlib import Path

from alembic import command
from alembic.config import Config


database_url = os.environ.get("AUDIT_DATABASE_URL")
if not database_url:
    raise SystemExit("AUDIT_DATABASE_URL is required")

config_path = Path(__file__).resolve().parent / "alembic" / "audit" / "alembic.ini"
config = Config(str(config_path))
config.set_main_option("script_location", str(config_path.parent).replace("%", "%%"))
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
command.upgrade(config, "head")
print("preflight: audit=empty (explicit disposable test migration)")
