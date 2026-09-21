import os
import secrets
import subprocess
import tempfile
import uuid
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


ROOT = Path(__file__).resolve().parents[1]


def generate_keys(
    directory: Path,
    *,
    kid: str = "e2e",
    private_filename: str | Path = "jwt-private.pem",
) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    (directory / "jwt-public").mkdir()
    private_path = directory / private_filename
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (directory / "jwt-public" / f"{kid}.pem").write_bytes(
        private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def compose(project: str, environment: dict[str, str], *arguments: str) -> int:
    return subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            project,
            "-f",
            "docker-compose.yml",
            "-f",
            "docker-compose.e2e.yml",
            *arguments,
        ],
        cwd=ROOT,
        env=environment,
        check=False,
    ).returncode


def main() -> int:
    project = f"bankcore-e2e-{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory(prefix="bankcore-e2e-") as temporary_root:
        key_dir = Path(temporary_root)
        generate_keys(key_dir)
        environment = os.environ.copy()
        environment.update(
            {
                "POSTGRES_PASSWORD": secrets.token_urlsafe(24),
                "AUTH_SERVICE_TOKEN": secrets.token_urlsafe(32),
                "RATE_LIMIT_KEY_SECRET": secrets.token_urlsafe(32),
                "JWT_ACTIVE_KID": "e2e",
                "JWT_PRIVATE_KEY_FILE": (key_dir / "jwt-private.pem").as_posix(),
                "JWT_PUBLIC_KEYS_HOST_DIR": (key_dir / "jwt-public").as_posix(),
                "GATEWAY_PORT": "18080",
                "DEMO_MODE": "false",
            }
        )
        exit_code = 0
        try:
            for arguments in (
                ("build",),
                ("up", "-d", "--wait", "postgres", "redis"),
                ("run", "--rm", "migrate-auth"),
                ("run", "--rm", "migrate-transactions"),
                ("run", "--rm", "migrate-risk"),
                ("up", "-d", "--wait", "auth-service", "transactions-service", "risk-service", "nginx"),
                ("run", "--rm", "e2e-runner"),
            ):
                exit_code = compose(project, environment, *arguments)
                if exit_code:
                    break
        finally:
            teardown_code = compose(project, environment, "down", "-v", "--remove-orphans")
            if exit_code == 0:
                exit_code = teardown_code
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
