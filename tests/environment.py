import os
from urllib.parse import urlsplit


ALLOWED_TEST_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres-test"}
ALLOWED_SCHEMES = {"postgresql", "postgresql+asyncpg"}


def validate_test_database_url(database_url: str | None) -> str:
    if os.getenv("BANKCORE_TESTING", "").lower() != "true":
        raise RuntimeError("BANKCORE_TESTING=true is required for database integration tests.")
    if not database_url:
        raise RuntimeError("BANKCORE_TEST_DATABASE_URL is required for database integration tests.")

    parsed = urlsplit(database_url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise RuntimeError("Test database URL must use PostgreSQL.")
    if parsed.hostname not in ALLOWED_TEST_HOSTS:
        raise RuntimeError("Test database host is not an approved local test host.")
    if parsed.port not in (None, 5432):
        raise RuntimeError("Test database port is not approved.")
    if not parsed.path or not parsed.path.lstrip("/").startswith("bankcore_test_"):
        raise RuntimeError("Test database name must start with bankcore_test_.")
    return database_url
