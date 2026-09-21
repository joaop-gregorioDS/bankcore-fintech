"""Single disposable entry point for the P5 observability evidence chain."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SURFACE_TOKENS = (
    "authorization", "bearer ", "password", "secret", "connection_string",
    "cpf", "cnpj", "pix_key",
)
STAGES = (
    ("structured logs, correlation and traces", "scripts/p5-tracing.py"),
    ("metrics and operational fault scenarios", "scripts/p5-metrics.py"),
    ("Grafana provisioning and dashboard bindings", "scripts/p5-grafana.py"),
    ("Prometheus alert lifecycle", "scripts/p5-alerts.py"),
    ("financial Kafka/outbox/Audit recovery", "scripts/p3-e2e.py"),
    ("observability backend outage tolerance", "scripts/p5-observability-dependency-failure.py"),
)


def validate_observability_surfaces() -> None:
    paths = [
        ROOT / "infra" / "grafana",
        ROOT / "infra" / "prometheus" / "rules",
        ROOT / "infra" / "otel",
    ]
    for root in paths:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8").lower()
            leaked = [token for token in FORBIDDEN_SURFACE_TOKENS if token in content]
            if leaked:
                raise RuntimeError(f"Potential sensitive value/token in {path}: {', '.join(leaked)}")

    rules = (ROOT / "infra" / "prometheus" / "rules" / "bankcore-alerts.yml").read_text(encoding="utf-8")
    labels = re.findall(r"^\s{10}([a-zA-Z_][a-zA-Z0-9_]*):", rules, re.MULTILINE)
    forbidden_labels = {"request_id", "trace_id", "correlation_id", "transaction_id", "event_id", "user_id", "account_id"}
    leaked_labels = sorted(set(labels) & forbidden_labels)
    if leaked_labels:
        raise RuntimeError(f"High-cardinality alert labels found: {', '.join(leaked_labels)}")


def run_stage(label: str, script: str) -> None:
    print(f"\n=== P5-G: {label} ===")
    result = subprocess.run([sys.executable, script], cwd=ROOT, check=False)
    if result.returncode:
        raise RuntimeError(f"P5-G stage failed ({result.returncode}): {label}")
    print(f"P5-G stage PASS: {label}")


def main() -> int:
    validate_observability_surfaces()
    if len(sys.argv) > 1 and sys.argv[1] == "--static-only":
        print("P5-H OBSERVABILITY QUALITY PASS: static redaction and cardinality guards")
        return 0
    for label, script in STAGES:
        run_stage(label, script)
    print("P5-G OBSERVABILITY E2E PASS: logs/traces, metrics, dashboards and alerts agree across disposable validations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
