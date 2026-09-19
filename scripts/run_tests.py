import os
import sys
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_test_keys(root: Path) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path = root / "jwt-private.pem"
    public_dir = root / "jwt-public"
    public_dir.mkdir()
    private_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (public_dir / "test-runner.pem").write_bytes(
        private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    os.environ.update(
        {
            "JWT_ALGORITHM": "RS256",
            "JWT_ACTIVE_KID": "test-runner",
            "JWT_PRIVATE_KEY_PATH": str(private_path),
            "JWT_PUBLIC_KEYS_DIR": str(public_dir),
        }
    )


def validate_migrations(database_url: str) -> None:
    root = Path(__file__).resolve().parents[1]
    for service, database_name in (
        ("auth", "bankcore_test_auth"),
        ("transactions", "bankcore_test_transactions"),
    ):
        for module_name in list(sys.modules):
            if module_name == "app" or module_name.startswith("app."):
                del sys.modules[module_name]
        config_path = root / "infra" / "postgres" / "alembic" / service / "alembic.ini"
        config = Config(str(config_path))
        config.set_main_option("script_location", str(config_path.parent).replace("%", "%%"))
        service_url = database_url.rsplit("/", 1)[0] + "/" + database_name
        config.set_main_option("sqlalchemy.url", service_url.replace("%", "%%"))
        os.environ["DATABASE_URL"] = service_url
        command.check(config)
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]


def main() -> int:
    selector = os.getenv("TEST_SUITE", "all")
    with tempfile.TemporaryDirectory(prefix="bankcore-test-keys-") as temporary_root:
        generate_test_keys(Path(temporary_root))
        if os.getenv("TEST_FORCE_FAILURE", "").lower() == "true":
            return 97
        if os.getenv("TEST_VALIDATE_MIGRATIONS", "").lower() == "true":
            validate_migrations(os.environ["BANKCORE_TEST_DATABASE_URL"])
        args = ["-q"]
        if selector != "all":
            args.extend(["-m", selector])
        return pytest.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
