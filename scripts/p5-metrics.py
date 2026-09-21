"""Disposable P5-D metrics, Prometheus and failure-mode validation."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from e2e import generate_keys


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILES = (
    "-f", "docker-compose.yml", "-f", "docker-compose.e2e.yml",
    "-f", "docker-compose.p3-e2e.yml", "-f", "docker-compose.p5-tracing.yml",
    "-f", "docker-compose.p5-metrics.yml",
)


def compose(project: str, environment: dict[str, str], *arguments: str, capture: bool = False):
    return subprocess.run(
        ["docker", "compose", "-p", project, *COMPOSE_FILES, *arguments],
        cwd=ROOT,
        env=environment,
        check=False,
        text=True,
        capture_output=capture,
    )


def require(project: str, environment: dict[str, str], *arguments: str) -> None:
    result = compose(project, environment, *arguments, capture=True)
    if result.returncode:
        details = (result.stdout or "") + (result.stderr or "")
        raise RuntimeError(f"Compose step failed ({result.returncode}): {' '.join(arguments)}\n{details[-12000:]}")


def wait_for_prometheus(port: str) -> None:
    url = f"http://127.0.0.1:{port}/-/ready"
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(1)
    raise RuntimeError("Prometheus did not become ready")


def query_prometheus(port: str, query: str) -> dict:
    encoded = urllib.parse.urlencode({"query": query})
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/query?{encoded}", timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("status") != "success":
        raise RuntimeError(f"Prometheus query failed: {query}")
    return payload["data"]


def list_metric_names(port: str) -> set[str]:
    with urllib.request.urlopen(
        f"http://127.0.0.1:{port}/api/v1/label/__name__/values", timeout=5
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("status") != "success":
        raise RuntimeError("Prometheus metric name query failed")
    return set(payload["data"])


def wait_for_metrics(port: str, required: set[str], timeout: int = 30) -> set[str]:
    deadline = time.monotonic() + timeout
    last_missing = sorted(required)
    while time.monotonic() < deadline:
        available_names = list_metric_names(port)
        last_missing = sorted(
            name for name in required
            if name not in available_names and f"{name}_total" not in available_names
        )
        if not last_missing:
            return available_names
        time.sleep(2)
    raise RuntimeError(
        f"Prometheus metrics did not become available within {timeout}s: {', '.join(last_missing)}"
    )


def assert_metrics(port: str) -> None:
    required = {
        "bankcore_auth_login_attempts",
        "bankcore_auth_login_results",
        "bankcore_auth_rate_limit_decisions",
        "bankcore_auth_redis_failures",
        "bankcore_auth_redis_recoveries",
        "bankcore_transactions_service_http_requests",
        "bankcore_transactions_risk_requests",
        "bankcore_transactions_ledger_commits",
        "bankcore_transactions_outbox_events_created",
        "bankcore_outbox_publish",
        "bankcore_outbox_pending",
        "bankcore_outbox_oldest_age_seconds",
        "bankcore_risk_assessments",
        "bankcore_audit_events_received",
        "bankcore_audit_events_persisted",
        "bankcore_kafka_retries",
        "bankcore_kafka_dlq",
    }
    available_names = wait_for_metrics(port, required)
    for metric in ("bankcore_outbox_publish", "bankcore_risk_assessments", "bankcore_kafka_retries"):
        exported_name = metric if metric in available_names else f"{metric}_total"
        result = query_prometheus(port, exported_name).get("result", [])
        if not result or not any(float(item["value"][1]) > 0 for item in result):
            raise RuntimeError(f"Prometheus metric has no positive observation: {exported_name}")

    series = query_prometheus(port, '{__name__=~"bankcore_.*"}')
    forbidden = {"request_id", "correlation_id", "trace_id", "transaction_id", "event_id", "user_id", "account_id"}
    leaked = sorted({label for item in series.get("result", []) for label in item.get("metric", {}) if label in forbidden})
    if leaked:
        raise RuntimeError(f"High-cardinality labels exposed: {', '.join(leaked)}")


def main() -> int:
    project = f"bankcore-p5-metrics-{uuid.uuid4().hex[:8]}"
    prometheus_port = os.environ.get("PROMETHEUS_PORT", "19090")
    with tempfile.TemporaryDirectory(prefix="bankcore-p5-metrics-") as temporary_root:
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
            "GATEWAY_PORT": "18083",
            "PROMETHEUS_PORT": prometheus_port,
            "DEMO_MODE": "false",
        })
        exit_code = 1
        try:
            require(project, environment, "config", "--quiet")
            require(project, environment, "build")
            require(project, environment, "up", "-d", "--wait", "postgres", "redis", "kafka", "otel-collector", "prometheus")
            for migration in ("migrate-auth", "migrate-transactions", "migrate-risk", "migrate-audit"):
                require(project, environment, "run", "--rm", migration)
            require(project, environment, "run", "--rm", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "ensure-topics")
            require(project, environment, "up", "-d", "--wait", "auth-service", "transactions-service", "risk-service", "nginx")
            require(project, environment, "up", "-d", "outbox-publisher", "audit-consumer")
            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "happy")
            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "risk-rejected")
            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "poison")
            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p5_metrics_e2e.py", "kafka-retry")
            require(project, environment, "stop", "outbox-publisher", "kafka")
            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "create-pending")
            require(project, environment, "up", "-d", "--wait", "kafka")
            require(project, environment, "up", "-d", "outbox-publisher")
            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "verify-recovery")
            require(project, environment, "stop", "redis")
            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p5_metrics_e2e.py", "redis-fallback")
            require(project, environment, "up", "-d", "redis")
            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p5_metrics_e2e.py", "redis-fallback")
            wait_for_prometheus(prometheus_port)
            assert_metrics(prometheus_port)
            print("P5-D METRICS PASS: bounded Prometheus series, success/failure/recovery scenarios verified")
            exit_code = 0
        finally:
            if exit_code:
                diagnostics = compose(project, environment, "logs", "--no-color", "auth-service", "transactions-service", "risk-service", "outbox-publisher", "audit-consumer", capture=True)
                print(diagnostics.stdout or "", file=sys.stderr)
                print(diagnostics.stderr or "", file=sys.stderr)
            teardown = compose(project, environment, "down", "-v", "--remove-orphans")
            if exit_code == 0:
                exit_code = teardown.returncode
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
