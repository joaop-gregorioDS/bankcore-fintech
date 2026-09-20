"""Disposable P5-E Grafana provisioning and dashboard validation."""

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
    "-f", "docker-compose.p5-metrics.yml", "-f", "docker-compose.p5-grafana.yml",
)
EXPECTED_DASHBOARDS = {
    "bankcore-overview": "BankCore Overview",
    "bankcore-financial-flow": "Financial Flow",
    "bankcore-async": "Async / Kafka / Outbox",
    "bankcore-auth-redis": "Auth / Redis Resilience",
}
FORBIDDEN_TOKENS = (
    "request_id", "trace_id", "correlation_id", "transaction_id", "event_id",
    "user_id", "account_id", "cpf", "cnpj", "pix_key", "authorization",
)


def compose(project: str, environment: dict[str, str], *arguments: str, capture: bool = False):
    return subprocess.run(
        ["docker", "compose", "-p", project, *COMPOSE_FILES, *arguments],
        cwd=ROOT, env=environment, check=False, text=True, capture_output=capture,
    )


def require(project: str, environment: dict[str, str], *arguments: str) -> None:
    result = compose(project, environment, *arguments, capture=True)
    if result.returncode:
        details = (result.stdout or "") + (result.stderr or "")
        raise RuntimeError(f"Compose step failed ({result.returncode}): {' '.join(arguments)}\n{details[-12000:]}")


def get_json(url: str) -> dict | list:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_http(url: str, timeout: int = 45) -> dict:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            payload = get_json(url)
            return payload if isinstance(payload, dict) else {"data": payload}
        except Exception as error:
            last_error = error
            time.sleep(1)
    raise RuntimeError(f"Endpoint did not become ready: {url}: {last_error}")


def validate_dashboard_files() -> None:
    dashboard_dir = ROOT / "infra" / "grafana" / "dashboards"
    files = sorted(dashboard_dir.glob("*.json"))
    if len(files) != len(EXPECTED_DASHBOARDS):
        raise RuntimeError(f"Expected {len(EXPECTED_DASHBOARDS)} dashboard files, found {len(files)}")
    for path in files:
        content = path.read_text(encoding="utf-8")
        lowered = content.lower()
        leaked = [token for token in FORBIDDEN_TOKENS if token in lowered]
        if leaked:
            raise RuntimeError(f"Forbidden identifier in dashboard {path.name}: {', '.join(leaked)}")
        dashboard = json.loads(content)
        if dashboard.get("uid") not in EXPECTED_DASHBOARDS or not dashboard.get("panels"):
            raise RuntimeError(f"Invalid dashboard file: {path.name}")
        if "alert" in lowered:
            raise RuntimeError(f"Alerting configuration found in dashboard {path.name}")


def validate_grafana(grafana_port: str) -> None:
    health = wait_for_http(f"http://127.0.0.1:{grafana_port}/api/health")
    if health.get("database") != "ok":
        raise RuntimeError(f"Grafana database is not healthy: {health}")
    datasource = wait_for_http(f"http://127.0.0.1:{grafana_port}/api/datasources/uid/prometheus/health")
    if datasource.get("status") != "OK":
        raise RuntimeError(f"Prometheus datasource is not healthy: {datasource}")
    search = wait_for_http(
        f"http://127.0.0.1:{grafana_port}/api/search?{urllib.parse.urlencode({'type': 'dash-db'})}"
    )
    dashboards = search.get("data", search)
    found = {item.get("uid"): item.get("title") for item in dashboards if isinstance(item, dict)}
    if any(found.get(uid) != title for uid, title in EXPECTED_DASHBOARDS.items()):
        raise RuntimeError(f"Provisioned dashboards mismatch: {found}")
    for uid, title in EXPECTED_DASHBOARDS.items():
        payload = wait_for_http(f"http://127.0.0.1:{grafana_port}/api/dashboards/uid/{uid}")
        dashboard = payload.get("dashboard", {})
        if dashboard.get("title") != title or not dashboard.get("panels"):
            raise RuntimeError(f"Dashboard failed validation: {uid}")
        for panel in dashboard["panels"]:
            if panel.get("datasource", {}).get("uid") != "prometheus":
                raise RuntimeError(f"Dashboard panel is not bound to Prometheus: {uid}")


def main() -> int:
    validate_dashboard_files()
    project = f"bankcore-p5-grafana-{uuid.uuid4().hex[:8]}"
    grafana_port = os.environ.get("GRAFANA_PORT", "13000")
    with tempfile.TemporaryDirectory(prefix="bankcore-p5-grafana-") as temporary_root:
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
            "GATEWAY_PORT": "18084", "PROMETHEUS_PORT": "19091", "GRAFANA_PORT": grafana_port,
            "DEMO_MODE": "false",
        })
        exit_code = 1
        try:
            require(project, environment, "config", "--quiet")
            require(project, environment, "build")
            require(project, environment, "up", "-d", "--wait", "postgres", "redis", "kafka", "otel-collector", "prometheus", "grafana")
            for migration in ("migrate-auth", "migrate-transactions", "migrate-risk", "migrate-audit"):
                require(project, environment, "run", "--rm", migration)
            require(project, environment, "run", "--rm", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "ensure-topics")
            require(project, environment, "up", "-d", "--wait", "auth-service", "transactions-service", "risk-service", "nginx")
            require(project, environment, "up", "-d", "outbox-publisher", "audit-consumer")
            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "happy")
            require(project, environment, "run", "--rm", "--no-deps", "p3-e2e-runner", "python", "tests/p3g_e2e.py", "risk-rejected")
            validate_grafana(grafana_port)
            print("P5-E GRAFANA PASS: datasource healthy and four dashboards provisioned")
            exit_code = 0
        finally:
            if exit_code:
                diagnostics = compose(project, environment, "logs", "--no-color", "grafana", "prometheus", capture=True)
                print(diagnostics.stdout or "", file=sys.stderr)
                print(diagnostics.stderr or "", file=sys.stderr)
            teardown = compose(project, environment, "down", "-v", "--remove-orphans")
            if exit_code == 0:
                exit_code = teardown.returncode
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
