"""Validate the P6-F1 host/IaC contract without contacting a remote host."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ANSIBLE = ROOT / "infra" / "ansible"
PRODUCTION_COMPOSE = ROOT / "docker-compose.production.yml"
SENSITIVE_PATTERNS = (
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    re.compile(r"(?i)(?:password|token|secret|private[_-]?key)\s*[:=]\s*[^$\{\n][^\n]*"),
)
REQUIRED_DIRS = {
    "/opt/bankcore",
    "/opt/bankcore/releases",
    "/opt/bankcore/config",
    "/opt/bankcore/secrets",
    "/opt/bankcore/backups",
    "/opt/bankcore/logs",
    "/opt/bankcore/run",
}


def load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise SystemExit(f"P6F1 VALIDATION FAILED: {message}")


def assert_file(path: Path) -> None:
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(ROOT)}")


def validate_ansible_contract() -> None:
    required = (
        ANSIBLE / "ansible.cfg",
        ANSIBLE / "inventory" / "disposable.yml",
        ANSIBLE / "group_vars" / "all.yml",
        ANSIBLE / "site.yml",
        ANSIBLE / "roles" / "bankcore_host" / "defaults" / "main.yml",
        ANSIBLE / "roles" / "bankcore_host" / "tasks" / "main.yml",
    )
    for path in required:
        assert_file(path)

    inventory = load_yaml(ANSIBLE / "inventory" / "disposable.yml")
    disposable = inventory["all"]["children"]["bankcore_staging"]["hosts"]["disposable"]
    if disposable.get("ansible_connection") != "local" or disposable.get("ansible_host") != "localhost":
        fail("disposable inventory is not local-only")

    variables = load_yaml(ANSIBLE / "group_vars" / "all.yml")
    if variables.get("bankcore_environment") != "disposable":
        fail("disposable inventory must default to bankcore_environment=disposable")
    if variables.get("bankcore_docker_mode") != "rootless":
        fail("host contract must default to rootless Docker")

    paths = {
        item["path"].replace("{{ bankcore_root }}", str(variables["bankcore_root"]))
        for item in variables.get("bankcore_host_directories", [])
    }
    if not REQUIRED_DIRS.issubset(paths):
        fail(f"host layout is missing: {sorted(REQUIRED_DIRS - paths)}")
    modes = {
        item["path"].replace("{{ bankcore_root }}", str(variables["bankcore_root"])): item["mode"]
        for item in variables["bankcore_host_directories"]
    }
    if modes.get("/opt/bankcore/secrets") != "0700":
        fail("secrets directory must be mode 0700")

    site = load_yaml(ANSIBLE / "site.yml")
    if not isinstance(site, list) or site[0].get("hosts") != "bankcore_staging":
        fail("site playbook must target only bankcore_staging")
    if site[0].get("roles") != ["bankcore_host"]:
        fail("site playbook must use the bankcore_host role")


def validate_production_compose() -> None:
    compose = load_yaml(PRODUCTION_COMPOSE)
    services = compose.get("services", {})
    if not services:
        fail("production Compose contains no services")
    exposed = set()
    for service_name, service in services.items():
        for binding in service.get("ports", []) or []:
            binding_text = str(binding)
            exposed.add(service_name)
            if service_name in {"prometheus", "grafana"} and not binding_text.startswith("127.0.0.1:"):
                fail(f"{service_name} must remain loopback-only: {binding_text}")
    if exposed - {"nginx", "prometheus", "grafana"}:
        fail(f"unexpected publicly bound production services: {sorted(exposed - {'nginx', 'prometheus', 'grafana'})}")
    for name in ("postgres", "audit-postgres", "redis", "kafka", "risk-service", "audit-consumer"):
        if name not in services:
            fail(f"production Compose is missing required service: {name}")
    for name, service in services.items():
        if name in {"auth-service", "transactions-service", "risk-service", "outbox-publisher", "audit-consumer", "migrate-auth", "migrate-transactions", "migrate-risk", "migrate-audit"}:
            if "cap_drop" not in service or "ALL" not in service["cap_drop"]:
                fail(f"{name} is missing cap_drop ALL")
            if "security_opt" not in service or "no-new-privileges:true" not in service["security_opt"]:
                fail(f"{name} is missing no-new-privileges")


def validate_no_secrets() -> None:
    files = list(ANSIBLE.rglob("*.yml")) + list(ANSIBLE.rglob("*.cfg"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern in SENSITIVE_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(0)
                if "${" not in value and "{{" not in value and "required" not in value.lower():
                    fail(f"possible secret value in {path.relative_to(ROOT)}")


def validate_with_ansible(require_ansible: bool) -> None:
    executable = shutil.which("ansible-playbook")
    if not executable:
        message = "SKIP: ansible-playbook is not installed; YAML/static contract validation completed"
        if require_ansible:
            fail(message)
        print(message)
        return
    command = [
        executable,
        "--syntax-check",
        "-i",
        str(ANSIBLE / "inventory" / "disposable.yml"),
        str(ANSIBLE / "site.yml"),
    ]
    result = subprocess.run(command, cwd=ANSIBLE, text=True, capture_output=True, check=False)
    if result.returncode:
        fail(f"ansible syntax check failed: {(result.stderr or result.stdout).strip()}")
    print("PASS: ansible-playbook syntax check")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ansible", action="store_true")
    args = parser.parse_args()
    validate_ansible_contract()
    validate_production_compose()
    validate_no_secrets()
    validate_with_ansible(args.require_ansible)
    print("P6F1 VALIDATION PASS: host layout, rootless Docker contract, production exposure and secret boundary")
    return 0


if __name__ == "__main__":
    sys.exit(main())
