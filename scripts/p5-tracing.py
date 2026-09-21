import os
import secrets
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from e2e import generate_keys

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILES = (
    "-f", "docker-compose.yml", "-f", "docker-compose.e2e.yml",
    "-f", "docker-compose.p3-e2e.yml", "-f", "docker-compose.p5-tracing.yml",
)


def compose(project: str, environment: dict[str, str], *arguments: str, capture: bool = False):
    return subprocess.run(
        ["docker", "compose", "-p", project, *COMPOSE_FILES, *arguments,
         ], cwd=ROOT, env=environment, check=False, text=True, capture_output=capture
    )


def require(project: str, environment: dict[str, str], *arguments: str) -> None:
    result = compose(project, environment, *arguments, capture=True)
    if result.returncode:
        details = (result.stdout or "") + (result.stderr or "")
        raise RuntimeError(
            f"Compose step failed ({result.returncode}): {' '.join(arguments)}\n{details[-12000:]}"
        )


def main() -> int:
    project = f"bankcore-p5-tracing-{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory(prefix="bankcore-p5-tracing-") as temporary_root:
        key_dir = Path(temporary_root)
        generate_keys(key_dir)
        environment = os.environ.copy()
        environment.update({
            "POSTGRES_PASSWORD": secrets.token_urlsafe(24),
            "AUTH_SERVICE_TOKEN": secrets.token_urlsafe(32),
            "RATE_LIMIT_KEY_SECRET": secrets.token_urlsafe(32),
            "JWT_ACTIVE_KID": "e2e",
            "JWT_PRIVATE_KEY_FILE": (key_dir / "jwt-private.pem").as_posix(),
            "JWT_PUBLIC_KEYS_HOST_DIR": (key_dir / "jwt-public").as_posix(),
            "GATEWAY_PORT": "18082",
            "DEMO_MODE": "false",
        })
        exit_code = 1
        try:
            require(project, environment, "config", "--quiet")
            require(project, environment, "build")
            require(project, environment, "up", "-d", "--wait", "postgres", "redis", "kafka", "otel-collector")
            for migration in ("migrate-auth", "migrate-transactions", "migrate-risk", "migrate-audit"):
                require(project, environment, "run", "--rm", migration)
            require(project, environment, "run", "--rm", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "ensure-topics")
            require(project, environment, "up", "-d", "--wait", "auth-service", "transactions-service", "risk-service", "nginx")
            require(project, environment, "up", "-d", "outbox-publisher", "audit-consumer")
            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "happy")
            time.sleep(3)
            logs = compose(project, environment, "logs", "--no-color", "otel-collector", capture=True)
            if logs.returncode:
                raise RuntimeError("Could not read OpenTelemetry Collector output.")
            required_spans = (
                "risk.assess", "ledger.commit", "outbox.persist",
                "kafka.produce transaction.completed.v1",
                "kafka.consume transaction.completed.v1", "audit.persist",
            )
            missing = [span for span in required_spans if span not in logs.stdout]
            if missing:
                raise RuntimeError(f"Collector did not expose required spans: {', '.join(missing)}")
            forbidden = ("Authorization", "Bearer ", "password", "cpf", "cnpj", "pix_key", "secret")
            leaked = [value for value in forbidden if value.lower() in logs.stdout.lower()]
            if leaked:
                raise RuntimeError(f"Forbidden values appeared in Collector output: {', '.join(leaked)}")
            exit_code = 0
        finally:
            if exit_code:
                diagnostics = compose(
                    project,
                    environment,
                    "logs",
                    "--no-color",
                    "auth-service",
                    "transactions-service",
                    "risk-service",
                    "outbox-publisher",
                    "audit-consumer",
                    capture=True,
                )
                print(diagnostics.stdout or "", file=sys.stderr)
                print(diagnostics.stderr or "", file=sys.stderr)
            teardown = compose(project, environment, "down", "-v", "--remove-orphans")
            if exit_code == 0:
                exit_code = teardown.returncode
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
