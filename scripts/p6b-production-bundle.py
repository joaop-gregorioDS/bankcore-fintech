import json
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
    "docker-compose.production.yml",
    "-f",
    "docker-compose.production.local.yml",
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


def redacted_output(output: str, environment: dict[str, str]) -> str:
    redacted = output
    for name in (
        "POSTGRES_PASSWORD",
        "AUTH_SERVICE_TOKEN",
        "RATE_LIMIT_KEY_SECRET",
        "GRAFANA_ADMIN_PASSWORD",
    ):
        value = environment.get(name)
        if value:
            redacted = redacted.replace(value, "[REDACTED]")
    return redacted[-4000:]


def require(project: str, environment: dict[str, str], *arguments: str) -> str:
    result = compose(project, environment, *arguments)
    if result.returncode:
        diagnostic = redacted_output(result.stderr or result.stdout, environment)
        raise RuntimeError(
            f"Compose step failed ({result.returncode}): {' '.join(arguments)}\n{diagnostic}"
        )
    return result.stdout


def require_docker() -> None:
    result = subprocess.run(
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Docker Engine is not available for the disposable production-bundle test.")


def compose_records(project: str, environment: dict[str, str]) -> list[dict[str, object]]:
    output = require(project, environment, "ps", "-a", "--format", "json")
    if output.lstrip().startswith("["):
        return list(json.loads(output))
    records: list[dict[str, object]] = []
    for line in output.splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def verify_startup_contract(project: str, environment: dict[str, str]) -> None:
    records = {str(record.get("Service")): record for record in compose_records(project, environment)}
    required_running = {
        "postgres",
        "audit-postgres",
        "redis",
        "kafka",
        "otel-collector",
        "prometheus",
        "grafana",
        "auth-service",
        "transactions-service",
        "risk-service",
        "outbox-publisher",
        "audit-consumer",
        "nginx",
    }
    missing = sorted(service for service in required_running if service not in records)
    if missing:
        raise RuntimeError(f"Production bundle did not create required services: {', '.join(missing)}")

    not_running = sorted(
        service
        for service in required_running
        if str(records[service].get("State", "")).lower() != "running"
    )
    if not_running:
        raise RuntimeError(f"Production bundle services are not running: {', '.join(not_running)}")

    for migration in ("migrate-auth", "migrate-transactions", "migrate-risk", "migrate-audit", "kafka-init"):
        record = records.get(migration)
        if record is None or str(record.get("State", "")).lower() != "exited":
            raise RuntimeError(f"Finite release step did not exit successfully: {migration}")
        if int(record.get("ExitCode", 1)) != 0:
            raise RuntimeError(f"Finite release step failed: {migration}")


def verify_no_project_residue(project: str, environment: dict[str, str]) -> None:
    remaining_containers = compose(project, environment, "ps", "-aq").stdout.strip()
    remaining_volumes = subprocess.run(
        [
            "docker",
            "volume",
            "ls",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    if remaining_containers or remaining_volumes:
        raise RuntimeError("Disposable production-bundle teardown left Docker resources behind.")


def main() -> int:
    require_docker()
    project = f"bankcore-p6b-{uuid.uuid4().hex[:8]}"
    with tempfile.TemporaryDirectory(prefix="bankcore-p6b-") as temporary_root:
        key_dir = Path(temporary_root)
        generate_keys(key_dir)
        environment = os.environ.copy()
        environment.update(
            {
                "POSTGRES_PASSWORD": secrets.token_urlsafe(24),
                "AUTH_SERVICE_TOKEN": secrets.token_urlsafe(32),
                "RATE_LIMIT_KEY_SECRET": secrets.token_urlsafe(32),
                "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(24),
                "JWT_ACTIVE_KID": "e2e",
                "JWT_PRIVATE_KEY_FILE": (key_dir / "jwt-private.pem").as_posix(),
                "JWT_PUBLIC_KEYS_HOST_DIR": (key_dir / "jwt-public").as_posix(),
                "BANKCORE_IMAGE_REGISTRY": "bankcore.local",
                "BANKCORE_RELEASE_VERSION": f"local-{uuid.uuid4().hex[:12]}",
                "GATEWAY_PORT": os.environ.get("P6B_GATEWAY_PORT", "18086"),
                "PROMETHEUS_PORT": os.environ.get("P6B_PROMETHEUS_PORT", "19096"),
                "GRAFANA_PORT": os.environ.get("P6B_GRAFANA_PORT", "13006"),
                "DEMO_MODE": "false",
            }
        )
        exit_code = 1
        try:
            require(project, environment, "--profile", "verification", "config", "--quiet")
            require(
                project,
                environment,
                "--profile",
                "verification",
                "build",
                "auth-service",
                "transactions-service",
                "risk-service",
                "migrate-audit",
                "p6b-e2e-runner",
            )
            require(project, environment, "up", "-d", "--wait")
            verify_startup_contract(project, environment)
            require(
                project,
                environment,
                "--profile",
                "verification",
                "run",
                "--rm",
                "--no-deps",
                "p6b-e2e-runner",
                "python",
                "tests/p3g_e2e.py",
                "happy",
            )

            # Core financial readiness is independent from telemetry availability.
            require(project, environment, "stop", "otel-collector", "prometheus", "grafana")
            require(
                project,
                environment,
                "--profile",
                "verification",
                "run",
                "--rm",
                "--no-deps",
                "p6b-e2e-runner",
                "python",
                "tests/p3g_e2e.py",
                "happy",
            )
            exit_code = 0
        except Exception:
            diagnostics = compose(
                project,
                environment,
                "logs",
                "--no-color",
                "auth-service",
                "transactions-service",
                "risk-service",
                "migrate-auth",
                "migrate-transactions",
                "migrate-risk",
                "migrate-audit",
            )
            if diagnostics.stdout or diagnostics.stderr:
                print(redacted_output(diagnostics.stdout + diagnostics.stderr, environment))
            raise
        finally:
            teardown = compose(project, environment, "down", "-v", "--remove-orphans")
            if teardown.returncode and exit_code == 0:
                exit_code = teardown.returncode
            if teardown.returncode == 0:
                verify_no_project_residue(project, environment)
        if exit_code == 0:
            print(
                "P6B PRODUCTION BUNDLE PASS: ordered migrations, readiness, "
                "PIX-to-Audit E2E, observability-down financial flow, teardown"
            )
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
