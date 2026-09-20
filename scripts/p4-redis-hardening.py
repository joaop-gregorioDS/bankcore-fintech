import os
import secrets
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from e2e import generate_keys


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILES = ("-f", "docker-compose.yml", "-f", "docker-compose.p4-rate-limit-test.yml")


def compose(project: str, environment: dict[str, str], *arguments: str) -> int:
    return subprocess.run(
        ["docker", "compose", "-p", project, *COMPOSE_FILES, *arguments],
        cwd=ROOT,
        env=environment,
        check=False,
    ).returncode


def require(project: str, environment: dict[str, str], *arguments: str) -> None:
    code = compose(project, environment, *arguments)
    if code:
        raise RuntimeError(f"Compose step failed ({code}): {' '.join(arguments)}")


def run_runner(project: str, environment: dict[str, str], command: str) -> None:
    require(
        project,
        environment,
        "run",
        "--rm",
        "--no-deps",
        "p4-rate-limit-runner",
        "python",
        "tests/p4_redis_hardening_smoke.py",
        command,
    )


def main() -> int:
    project = f"bankcore-p4-redis-hardening-{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory(prefix="bankcore-p4-redis-hardening-") as temporary_root:
        key_dir = Path(temporary_root)
        generate_keys(key_dir)
        environment = os.environ.copy()
        environment.update(
            {
                "POSTGRES_PASSWORD": secrets.token_urlsafe(24),
                "AUTH_SERVICE_TOKEN": secrets.token_urlsafe(32),
                "RATE_LIMIT_KEY_SECRET": secrets.token_urlsafe(32),
                "RATE_LIMIT_MAX_ATTEMPTS": "5",
                "RATE_LIMIT_WINDOW_SECONDS": "900",
                "RATE_LIMIT_REDIS_TIMEOUT_SECONDS": "0.2",
                "REDIS_MAXMEMORY": "64mb",
                "JWT_ACTIVE_KID": "e2e",
                "JWT_PRIVATE_KEY_FILE": (key_dir / "jwt-private.pem").as_posix(),
                "JWT_PUBLIC_KEYS_HOST_DIR": (key_dir / "jwt-public").as_posix(),
            }
        )
        exit_code = 1
        try:
            require(project, environment, "build", "auth-a", "auth-b", "auth-migrate-p4", "p4-rate-limit-runner")
            require(project, environment, "up", "-d", "--wait", "postgres", "redis")
            require(project, environment, "run", "--rm", "auth-migrate-p4")
            require(project, environment, "up", "-d", "--wait", "auth-a", "auth-b")
            time.sleep(3)
            run_runner(project, environment, "healthy")
            run_runner(project, environment, "memory")
            require(project, environment, "stop", "redis")
            run_runner(project, environment, "offline")
            require(project, environment, "up", "-d", "--wait", "redis")
            run_runner(project, environment, "recovered")
            exit_code = 0
        except Exception:
            compose(project, environment, "ps")
            compose(project, environment, "logs", "--no-color", "redis", "auth-a", "auth-b")
            raise
        finally:
            teardown = compose(project, environment, "down", "-v", "--remove-orphans")
            if exit_code == 0:
                exit_code = teardown
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
