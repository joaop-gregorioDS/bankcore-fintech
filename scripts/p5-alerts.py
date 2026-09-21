"""Validate versioned Prometheus alert rules with disposable promtool tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
import os
import secrets
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
PROMETHEUS_IMAGE = "prom/prometheus:v2.55.1"
RULES = "/work/infra/prometheus/rules/bankcore-alerts.yml"
TESTS = "/work/infra/prometheus/tests/bankcore-alerts.test.yml"
CONFIG = "/work/infra/prometheus/prometheus.yml"
RULE_FILE = ROOT / "infra" / "prometheus" / "rules" / "bankcore-alerts.yml"
FORBIDDEN_TOKENS = (
    "request_id", "trace_id", "correlation_id", "transaction_id", "event_id",
    "user_id", "account_id", "cpf", "cnpj", "pix_key", "authorization",
)
EXPECTED_ALERTS = (
    "RedisFallbackActive", "OutboxBacklogGrowing", "OutboxOldestEventTooOld",
    "KafkaRetriesDetected", "KafkaDLQDetected", "AuditPersistenceFailures",
    "RiskServiceErrors", "HttpServerErrorRateHigh", "ObservabilityTargetDown",
)
COMPOSE_FILES = (
    "-f", "docker-compose.yml", "-f", "docker-compose.p3-e2e.yml",
    "-f", "docker-compose.p5-tracing.yml", "-f", "docker-compose.p5-metrics.yml",
    "-f", "docker-compose.p5-alerts.yml",
)


def run_promtool(*arguments: str) -> None:
    command = [
        "docker", "run", "--rm",
        "--mount", f"type=bind,source={ROOT},target=/work,readonly",
        "--entrypoint", "promtool", PROMETHEUS_IMAGE, *arguments,
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode:
        details = (result.stdout or "") + (result.stderr or "")
        raise RuntimeError(f"promtool failed ({result.returncode}): {' '.join(arguments)}\n{details[-12000:]}")
    if result.stdout:
        print(result.stdout, end="")


def validate_rule_contract() -> None:
    content = RULE_FILE.read_text(encoding="utf-8").lower()
    leaked = [token for token in FORBIDDEN_TOKENS if token in content]
    if leaked:
        raise RuntimeError(f"Forbidden identifier in alert rules: {', '.join(leaked)}")
    missing = [name for name in EXPECTED_ALERTS if f"alert: {name.lower()}" not in content]
    if missing:
        raise RuntimeError(f"Missing expected alerts: {', '.join(missing)}")


def validate_compose() -> None:
    environment = os.environ.copy()
    environment.update({
        "POSTGRES_PASSWORD": secrets.token_urlsafe(16),
        "JWT_ACTIVE_KID": "p5-alerts",
        "AUTH_SERVICE_TOKEN": secrets.token_urlsafe(24),
        "RATE_LIMIT_KEY_SECRET": secrets.token_urlsafe(24),
    })
    command = [
        "docker", "compose",
        "-f", "docker-compose.yml",
        "-f", "docker-compose.p3-e2e.yml",
        "-f", "docker-compose.p5-tracing.yml",
        "-f", "docker-compose.p5-metrics.yml",
        "-f", "docker-compose.p5-alerts.yml",
        "config", "--quiet",
    ]
    result = subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True, check=False)
    if result.returncode:
        details = (result.stdout or "") + (result.stderr or "")
        raise RuntimeError(f"Compose validation failed ({result.returncode}):\n{details[-12000:]}")


def validate_live_rules() -> None:
    project = f"bankcore-p5-alerts-{uuid.uuid4().hex[:8]}"
    port = os.environ.get("PROMETHEUS_PORT", "19092")
    environment = os.environ.copy()
    environment.update({
        "POSTGRES_PASSWORD": secrets.token_urlsafe(16),
        "JWT_ACTIVE_KID": "p5-alerts",
        "AUTH_SERVICE_TOKEN": secrets.token_urlsafe(24),
        "RATE_LIMIT_KEY_SECRET": secrets.token_urlsafe(24),
        "PROMETHEUS_PORT": port,
    })
    command = ["docker", "compose", "-p", project, *COMPOSE_FILES]
    exit_code = 1
    try:
        started = subprocess.run(
            [*command, "up", "-d", "--wait", "prometheus"],
            cwd=ROOT, env=environment, text=True, capture_output=True, check=False,
        )
        if started.returncode:
            details = (started.stdout or "") + (started.stderr or "")
            raise RuntimeError(f"Prometheus startup failed:\n{details[-12000:]}")
        deadline = time.monotonic() + 45
        payload: dict | None = None
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/v1/rules?type=alert", timeout=5
                ) as response:
                    candidate = json.loads(response.read().decode("utf-8"))
                if candidate.get("status") == "success":
                    payload = candidate
                    break
            except Exception as error:
                last_error = error
            time.sleep(1)
        if payload is None:
            raise RuntimeError(f"Prometheus rules API did not become ready: {last_error}")
        loaded = {
            rule["name"]
            for group in payload.get("data", {}).get("groups", [])
            for rule in group.get("rules", [])
            if rule.get("type") == "alerting"
        }
        missing = sorted(set(EXPECTED_ALERTS) - loaded)
        if missing:
            raise RuntimeError(f"Prometheus did not load expected alert rules: {', '.join(missing)}")
        print(f"Prometheus runtime loaded {len(loaded)} alert rules")
        exit_code = 0
    finally:
        teardown = subprocess.run(
            [*command, "down", "-v", "--remove-orphans"],
            cwd=ROOT, env=environment, text=True, capture_output=True, check=False,
        )
        if exit_code == 0 and teardown.returncode:
            exit_code = teardown.returncode
    if exit_code:
        raise RuntimeError("Prometheus live rule validation failed")


def main() -> int:
    validate_rule_contract()
    validate_compose()
    run_promtool("check", "config", CONFIG)
    run_promtool("check", "rules", RULES)
    run_promtool("test", "rules", TESTS)
    validate_live_rules()
    print("P5-F ALERTS PASS: all rules validated through pending, firing and recovery states")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
