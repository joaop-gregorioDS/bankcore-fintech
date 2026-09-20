import os
import secrets
import subprocess
import tempfile
import uuid
from pathlib import Path

from e2e import generate_keys


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILES = (
    "-f",
    "docker-compose.yml",
    "-f",
    "docker-compose.e2e.yml",
    "-f",
    "docker-compose.p3-e2e.yml",
)


def compose(project: str, environment: dict[str, str], *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "-p", project, *COMPOSE_FILES, *arguments],
        cwd=ROOT,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def require(project: str, environment: dict[str, str], *arguments: str) -> str:
    result = compose(project, environment, *arguments)
    if result.returncode:
        raise RuntimeError(
            f"Compose step failed ({result.returncode}): {' '.join(arguments)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result.stdout


def main() -> int:
    project = f"bankcore-p4d-no-redis-{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory(prefix="bankcore-p4d-no-redis-") as temporary_root:
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
                "E2E_GATEWAY_PORT": "18082",
                "DEMO_MODE": "false",
            }
        )
        exit_code = 1
        try:
            require(project, environment, "build")
            require(project, environment, "up", "-d", "--wait", "postgres", "kafka")

            running = require(project, environment, "ps", "--services", "--status", "running").splitlines()
            if "redis" in running:
                raise RuntimeError("Redis must not be running in the Transactions no-Redis smoke test.")

            require(project, environment, "run", "--rm", "migrate-auth")
            for migration in ("migrate-transactions", "migrate-risk", "migrate-audit"):
                require(project, environment, "run", "--rm", migration)

            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "ensure-topics")
            require(
                project,
                environment,
                "up",
                "-d",
                "--wait",
                "auth-service",
                "transactions-service",
                "risk-service",
                "nginx",
            )
            require(project, environment, "up", "-d", "outbox-publisher", "audit-consumer")
            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "happy")
            exit_code = 0
        except Exception:
            diagnostic = compose(
                project,
                environment,
                "logs",
                "--no-color",
                "auth-service",
                "transactions-service",
                "risk-service",
            )
            print(diagnostic.stdout)
            print(diagnostic.stderr)
            raise
        finally:
            teardown = compose(project, environment, "down", "-v", "--remove-orphans")
            if teardown.returncode and exit_code == 0:
                print(teardown.stdout)
                print(teardown.stderr)
                exit_code = teardown.returncode
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
