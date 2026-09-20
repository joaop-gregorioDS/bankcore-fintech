import os
import secrets
import subprocess
import tempfile
import time
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


def compose(project: str, environment: dict[str, str], *arguments: str) -> int:
    return subprocess.run(
        ["docker", "compose", "-p", project, *COMPOSE_FILES, *arguments],
        cwd=ROOT,
        env=environment,
        check=False,
    ).returncode


def require_compose(project, environment, *arguments):
    code = compose(project, environment, *arguments)
    if code:
        raise RuntimeError(f"Compose step failed ({code}): {' '.join(arguments)}")


def run_expected_failure(project, environment, *arguments):
    code = compose(project, environment, *arguments)
    if code == 0:
        raise RuntimeError(f"Expected fault-injection failure did not occur: {' '.join(arguments)}")
    return code


def runner(project, environment, command):
    require_compose(
        project,
        environment,
        "run",
        "--rm",
        "--no-deps",
        "p3-e2e-runner",
        "python",
        "tests/p3g_e2e.py",
        command,
    )


def main() -> int:
    project = f"bankcore-p3-e2e-{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory(prefix="bankcore-p3-e2e-") as temporary_root:
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
                "GATEWAY_PORT": "18081",
                "DEMO_MODE": "false",
            }
        )
        exit_code = 1
        try:
            require_compose(project, environment, "build")
            require_compose(project, environment, "up", "-d", "--wait", "postgres", "redis", "kafka")
            require_compose(project, environment, "run", "--rm", "migrate-auth")
            require_compose(project, environment, "run", "--rm", "migrate-transactions")
            require_compose(project, environment, "run", "--rm", "migrate-risk")
            require_compose(project, environment, "run", "--rm", "migrate-audit")
            runner(project, environment, "ensure-topics")
            require_compose(
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
            require_compose(project, environment, "up", "-d", "outbox-publisher", "audit-consumer")

            runner(project, environment, "happy")

            require_compose(project, environment, "stop", "outbox-publisher", "audit-consumer", "kafka")
            runner(project, environment, "create-pending")
            require_compose(project, environment, "up", "-d", "--wait", "kafka")
            require_compose(project, environment, "up", "-d", "outbox-publisher", "audit-consumer")
            runner(project, environment, "verify-recovery")

            require_compose(project, environment, "stop", "outbox-publisher")
            runner(project, environment, "create-pending")
            run_expected_failure(project, environment, "run", "--rm", "--no-deps", "publisher-crash")
            time.sleep(4)
            require_compose(project, environment, "up", "-d", "outbox-publisher")
            runner(project, environment, "verify-recovery")

            require_compose(project, environment, "stop", "audit-consumer")
            runner(project, environment, "create-published")
            run_expected_failure(project, environment, "run", "--rm", "--no-deps", "audit-consumer-crash")
            require_compose(project, environment, "up", "-d", "audit-consumer")
            runner(project, environment, "verify-recovery")

            require_compose(project, environment, "stop", "audit-consumer")
            runner(project, environment, "create-published")
            require_compose(project, environment, "stop", "outbox-publisher")
            require_compose(project, environment, "stop", "postgres")
            time.sleep(1)
            require_compose(project, environment, "up", "-d", "--wait", "postgres")
            require_compose(project, environment, "up", "-d", "outbox-publisher", "audit-consumer")
            runner(project, environment, "verify-recovery")

            runner(project, environment, "idempotency")
            runner(project, environment, "risk-rejected")
            runner(project, environment, "poison")
            exit_code = 0
        except Exception:
            compose(project, environment, "ps")
            compose(
                project,
                environment,
                "logs",
                "--no-color",
                "auth-service",
                "transactions-service",
                "risk-service",
                "outbox-publisher",
                "audit-consumer",
            )
            raise
        finally:
            teardown_code = compose(project, environment, "down", "-v", "--remove-orphans")
            if exit_code == 0:
                exit_code = teardown_code
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
