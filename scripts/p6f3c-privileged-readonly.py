#!/usr/bin/env python3
"""Close P6-F3B observation gaps with an allowlisted privileged read-only probe.

This program intentionally uses ``sudo -n`` only for exact inspection commands.
It has no shell mode, no interactive sudo, no file writes, no Docker lifecycle,
and never opens private keys, environment files, or database dumps.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Iterable


EXPECTED = {
    "public_tcp_ports": [80, 443],
    "ssh_tcp_port": 22,
    "internal_tcp_ports": [5432, 6379, 8080, 9092, 9093, 3000, 4317, 4318, 8889, 13133],
    "secrets_policy": "presence/metadata only; never read values",
    "backup_policy": "metadata only; never open dumps",
    "change_policy": "inventory only; no mutations",
}

SUDO_PREFIX = ("sudo", "-n")
READ_ONLY_PROGRAMS = {
    "crontab",
    "docker",
    "find",
    "getent",
    "ip6tables",
    "iptables",
    "nft",
    "nginx",
    "openssl",
    "ss",
    "systemctl",
    "ufw",
}
FORBIDDEN_TOKENS = {
    ";",
    "&&",
    "||",
    "|",
    ">",
    ">>",
    "<",
    "-c",
    "--command",
    "--shell",
    "apply",
    "chgrp",
    "chmod",
    "chown",
    "compose-up",
    "create",
    "down",
    "enable",
    "exec",
    "install",
    "kill",
    "mkdir",
    "mv",
    "reload",
    "remove",
    "restart",
    "rm",
    "run",
    "start",
    "stop",
    "useradd",
    "write",
}
METADATA_FORMAT = "%p\\t%u\\t%g\\t%m\\t%s\\n"
DOCKER_INSPECT_FORMAT = (
    "{{.Name}}\\t{{.Config.Image}}\\t{{.HostConfig.RestartPolicy.Name}}\\t"
    "{{range .Mounts}}{{.Source}}:{{.Destination}}:{{.RW}};{{end}}\\t"
    "{{range $p, $bindings := .HostConfig.PortBindings}}{{$p}}={{$bindings}};{{end}}"
)
ALLOWED_METADATA_ROOTS = {
    "/etc/bankcore",
    "/etc/letsencrypt",
    "/etc/nginx",
    "/home/bankcore",
    "/opt/bankcore",
    "/opt/bankcore/backups",
    "/srv/backups",
    "/var/backups",
}
CERT_ROOT = "/etc/letsencrypt/live"
SENSITIVE_LINE = re.compile(
    r"(?i)(authorization|bearer|password|passwd|secret|private[_ -]?key|token|jwt|database_url|connection_string)"
)
ENV_ASSIGNMENT = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*=\s*.*$")
URI_CREDENTIALS = re.compile(r"(://[^:/\s]+:)[^@\s]+(@)")
PEM_BLOCK = re.compile(r"-----BEGIN [^-]+-----.*?-----END [^-]+-----", re.DOTALL)


@dataclass
class Probe:
    name: str
    command: str
    status: str
    returncode: int | None
    output: str


def sanitize(text: str, *, limit: int = 3500) -> str:
    """Redact values before they can reach stdout or a report."""

    text = PEM_BLOCK.sub("<redacted-pem>", text)
    text = URI_CREDENTIALS.sub(r"\1<redacted>\2", text)
    lines: list[str] = []
    for line in text.splitlines():
        if SENSITIVE_LINE.search(line):
            lines.append(f"{line.split('=', 1)[0]}=<redacted>" if "=" in line else "<redacted-sensitive-line>")
        elif ENV_ASSIGNMENT.match(line):
            lines.append(f"{line.split('=', 1)[0]}=<present>")
        else:
            lines.append(line)
    cleaned = "\n".join(lines).strip()
    return cleaned if len(cleaned) <= limit else cleaned[:limit] + "\n<truncated>"


def _under_allowed_root(path: str, roots: set[str] = ALLOWED_METADATA_ROOTS) -> bool:
    candidate = PurePosixPath(path)
    return any(candidate == PurePosixPath(root) or PurePosixPath(root) in candidate.parents for root in roots)


def _under_cert_root(path: str) -> bool:
    candidate = PurePosixPath(path)
    return PurePosixPath(CERT_ROOT) in candidate.parents and candidate.name in {"fullchain.pem", "cert.pem"}


def validate_privileged_command(argv: list[str]) -> None:
    """Accept only exact, non-mutating inspection command shapes."""

    if len(argv) < 3 or tuple(argv[:2]) != SUDO_PREFIX:
        raise ValueError("privileged probes require exactly sudo -n")
    if any(token in FORBIDDEN_TOKENS or any(char in token for char in ";&|<>$") for token in argv):
        raise ValueError(f"forbidden token or shell syntax: {argv}")
    command = argv[2:]
    if command[0] not in READ_ONLY_PROGRAMS:
        raise ValueError(f"program is not allowlisted: {command[0]}")

    if command == ["ss", "-lntup"]:
        return
    if command in (
        ["ufw", "status", "verbose"],
        ["nft", "list", "ruleset"],
        ["iptables", "-S"],
        ["iptables", "-t", "nat", "-S"],
        ["ip6tables", "-S"],
        ["ip6tables", "-t", "nat", "-S"],
        ["nginx", "-T"],
        ["nginx", "-V"],
        ["crontab", "-l"],
        ["systemctl", "list-timers", "--all", "--no-legend", "--no-pager"],
        ["systemctl", "list-units", "--type=service", "--all", "--no-legend", "--no-pager"],
    ):
        return
    if command[:3] == ["systemctl", "is-active", "--quiet"] and len(command) == 4:
        return
    if command[:2] == ["getent", "passwd"] and len(command) == 3:
        return
    if command[:2] == ["getent", "group"] and len(command) == 3:
        return
    if command[:2] == ["docker", "info"] and command[2:] == ["--format", "{{.DockerRootDir}}\\t{{.ServerVersion}}\\t{{json .SecurityOptions}}"]:
        return
    if command[:2] == ["docker", "ps"] and command[2:] == ["-a", "--format", "{{.Names}}\\t{{.Image}}\\t{{.Status}}"]:
        return
    if command[:2] == ["docker", "inspect"] and command[2:4] == ["--format", DOCKER_INSPECT_FORMAT] and len(command) == 5:
        return
    if command[:2] == ["find", "-"]:
        raise ValueError("find requires explicit absolute metadata roots")
    if command[0] == "find":
        roots: list[str] = []
        for token in command[1:]:
            if token.startswith("/"):
                roots.append(token)
        if not roots or any(not _under_allowed_root(root) for root in roots):
            raise ValueError("find root is outside the metadata allowlist")
        if "-printf" not in command or command[-1] != METADATA_FORMAT:
            raise ValueError("find is limited to metadata-only printf format")
        if any(token in {"-delete", "-exec", "-execdir", "-fprint", "-fprintf", "-fls"} for token in command):
            raise ValueError("find content/write operation rejected")
        return
    if command[0] == "openssl" and command[:2] == ["openssl", "x509"]:
        if len(command) < 4 or command[2] != "-in" or not _under_cert_root(command[3]):
            raise ValueError("openssl is limited to public certificate metadata")
        if command[4:] != ["-noout", "-subject", "-issuer", "-dates", "-ext", "subjectAltName"]:
            raise ValueError("openssl output is limited to certificate metadata")
        return
    raise ValueError(f"command shape is not allowlisted: {argv}")


def probe(name: str, argv: list[str], *, timeout: int = 20) -> Probe:
    validate_privileged_command(argv)
    try:
        result = subprocess.run(argv, shell=False, check=False, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return Probe(name, " ".join(argv), "unavailable", None, "program not installed")
    except subprocess.TimeoutExpired:
        return Probe(name, " ".join(argv), "timeout", None, "probe timed out")
    output = sanitize((result.stdout or "") + (result.stderr or ""))
    return Probe(name, " ".join(argv), "ok" if result.returncode == 0 else "unavailable", result.returncode, output)


def _find_command(*roots: str) -> list[str]:
    return ["sudo", "-n", "find", *roots, "-maxdepth", "4", "-type", "f", "-printf", METADATA_FORMAT]


def collect() -> tuple[dict, list[Probe]]:
    probes: list[Probe] = []

    def add(name: str, argv: list[str], *, timeout: int = 20) -> Probe:
        item = probe(name, argv, timeout=timeout)
        probes.append(item)
        return item

    listening = add("privileged_listening_ports", ["sudo", "-n", "ss", "-lntup"])
    firewall = [
        add("ufw_rules", ["sudo", "-n", "ufw", "status", "verbose"]),
        add("nftables_rules", ["sudo", "-n", "nft", "list", "ruleset"]),
        add("iptables_filter", ["sudo", "-n", "iptables", "-S"]),
        add("iptables_nat", ["sudo", "-n", "iptables", "-t", "nat", "-S"]),
        add("ip6tables_filter", ["sudo", "-n", "ip6tables", "-S"]),
        add("ip6tables_nat", ["sudo", "-n", "ip6tables", "-t", "nat", "-S"]),
    ]
    nginx = add("nginx_effective_config", ["sudo", "-n", "nginx", "-T"], timeout=30)
    tls_paths = add("tls_certificate_metadata", _find_command("/etc/letsencrypt", "/etc/nginx"), timeout=30)
    tls_certs: list[Probe] = []
    for line in tls_paths.output.splitlines():
        path = line.split("\t", 1)[0]
        if _under_cert_root(path):
            tls_certs.append(add(f"certificate:{path}", ["sudo", "-n", "openssl", "x509", "-in", path, "-noout", "-subject", "-issuer", "-dates", "-ext", "subjectAltName"]))

    docker_info = add("docker_rootful_contract", ["sudo", "-n", "docker", "info", "--format", "{{.DockerRootDir}}\\t{{.ServerVersion}}\\t{{json .SecurityOptions}}"], timeout=30)
    containers = add("docker_container_bindings", ["sudo", "-n", "docker", "ps", "-a", "--format", "{{.Names}}\\t{{.Image}}\\t{{.Status}}"], timeout=30)
    for line in containers.output.splitlines():
        name = line.split("\t", 1)[0].strip()
        if name and re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            add(f"docker_inspect:{name}", ["sudo", "-n", "docker", "inspect", "--format", DOCKER_INSPECT_FORMAT, name], timeout=30)

    backups = [
        add("backup_metadata:/opt/bankcore/backups", _find_command("/opt/bankcore/backups"), timeout=30),
        add("backup_metadata:/var/backups", _find_command("/var/backups"), timeout=30),
        add("backup_metadata:/srv/backups", _find_command("/srv/backups"), timeout=30),
    ]
    config = [
        add("config_metadata:/opt/bankcore/config", _find_command("/opt/bankcore/config"), timeout=30),
        add("secret_metadata:/opt/bankcore/secrets", _find_command("/opt/bankcore/secrets"), timeout=30),
        add("config_metadata:/etc/bankcore", _find_command("/etc/bankcore"), timeout=30),
    ]
    root_cron = add("root_crontab", ["sudo", "-n", "crontab", "-l"])
    timers = add("systemd_timers", ["sudo", "-n", "systemctl", "list-timers", "--all", "--no-legend", "--no-pager"])
    services = add("systemd_services", ["sudo", "-n", "systemctl", "list-units", "--type=service", "--all", "--no-legend", "--no-pager"])

    return {
        "privileged_listening_ports": listening.output,
        "firewall_probes": [item.status for item in firewall],
        "nginx_effective_config": "collected/sanitized" if nginx.status == "ok" else nginx.status,
        "tls_certificate_metadata": "collected without private-key reads" if tls_paths.status == "ok" else tls_paths.status,
        "certificate_metadata_probes": len(tls_certs),
        "docker_contract": "collected" if docker_info.status == "ok" else docker_info.status,
        "docker_bindings": "collected" if containers.status == "ok" else containers.status,
        "backup_metadata": [item.status for item in backups],
        "config_secret_metadata": [item.status for item in config],
        "root_crontab": root_cron.status,
        "systemd_timers": timers.status,
        "systemd_services": services.status,
        "secret_values": "never queried",
        "private_keys": "never queried",
        "database_dumps": "never opened",
    }, probes


def build_report(observed: dict, probes: list[Probe]) -> dict:
    drift: list[str] = []
    proposed: list[str] = []
    risk: list[str] = []
    rollback: list[str] = []
    listening_output = next((item.output for item in probes if item.name == "privileged_listening_ports"), "")
    if ":9090" in listening_output or "*:9090" in listening_output:
        drift.append("TCP/9090 is listening and requires service ownership classification")
        proposed.append("Identify the 9090 owner and intended exposure before any firewall plan")
        risk.append("Unknown telemetry or application exposure may bypass the gateway boundary")
        rollback.append("Leave firewall and listener state unchanged until ownership is documented")
    if any(status != "ok" for status in observed["firewall_probes"]):
        drift.append("One or more privileged firewall probes were unavailable")
        proposed.append("Use the first approved host mutation plan to make firewall evidence reproducible")
        risk.append("Network exposure remains unverified")
        rollback.append("Do not modify firewall rules until a read-only baseline is complete")
    if observed["nginx_effective_config"] != "collected/sanitized":
        drift.append("Effective Nginx configuration was not fully readable")
        proposed.append("Review Nginx read permissions or collect the config through an approved operator path")
        risk.append("Proxy/TLS routing remains partially unverified")
        rollback.append("Do not change Nginx or TLS configuration")
    if any(status != "ok" for status in observed["backup_metadata"]):
        drift.append("One or more backup metadata roots were unavailable")
        proposed.append("Inventory the approved backup locations and schedules before deployment")
        risk.append("Restore readiness cannot be established")
        rollback.append("Do not cut over a new release until backup evidence exists")
    return {
        "schema": "bankcore.p6f3c.privileged-readonly-gap-closure.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "privileged read-only; sudo -n allowlist only",
        "observed": observed,
        "expected": EXPECTED,
        "drift": drift or ["No drift detected by available privileged probes; unavailable probes remain unverified"],
        "proposed_change": proposed or ["No mutation proposed by this read-only probe"],
        "risk": risk or ["No immediate contract risk detected; this is not a production readiness decision"],
        "rollback": rollback or ["No rollback action; this program performs no mutation"],
        "unverified_probes": [item.name for item in probes if item.status != "ok"],
        "probes": [asdict(item) for item in probes],
        "safety": {
            "shell": False,
            "interactive_sudo": False,
            "sudo_only_for_exact_reads": True,
            "filesystem_writes": False,
            "docker_lifecycle": False,
            "firewall_changes": False,
            "systemd_changes": False,
            "nginx_tls_changes": False,
            "secret_values_read": False,
            "private_keys_read": False,
            "database_dumps_opened": False,
        },
    }


def markdown(report: dict) -> str:
    lines = [
        "# P6-F3C — Privileged Read-only Gap Closure Report",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Generated: `{report['generated_at']}`",
        f"- Mode: **{report['mode']}**",
        "",
        "## Observed",
        "",
        "```json",
        json.dumps(report["observed"], indent=2, ensure_ascii=False),
        "```",
        "",
        "## Expected",
        "",
        "```json",
        json.dumps(report["expected"], indent=2, ensure_ascii=False),
        "```",
        "",
        "## Drift",
    ]
    lines.extend(f"- {item}" for item in report["drift"])
    lines.extend(["", "## Proposed change", ""])
    lines.extend(f"- {item}" for item in report["proposed_change"])
    lines.extend(["", "## Risk", ""])
    lines.extend(f"- {item}" for item in report["risk"])
    lines.extend(["", "## Rollback", ""])
    lines.extend(f"- {item}" for item in report["rollback"])
    lines.extend(["", "## Probe status", ""])
    lines.extend(f"- `{item['name']}`: **{item['status']}** — `{item['command']}`" for item in report["probes"])
    lines.extend(["", "## Safety assertions", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in report["safety"].items())
    return "\n".join(lines) + "\n"


def self_test() -> int:
    allowed = ["sudo", "-n", "ss", "-lntup"]
    validate_privileged_command(allowed)
    for rejected in (
        ["sudo", "-n", "rm", "-rf", "/"],
        ["sudo", "-n", "systemctl", "restart", "nginx"],
        ["sudo", "-n", "docker", "compose", "up", "-d"],
        ["sudo", "-n", "sh", "-c", "id"],
        ["sudo", "-n", "find", "/", "-exec", "cat", "{}", ";", "-printf", METADATA_FORMAT],
        ["sudo", "-n", "openssl", "x509", "-in", "/etc/letsencrypt/live/example/privkey.pem", "-noout"],
    ):
        try:
            validate_privileged_command(rejected)
        except ValueError:
            continue
        print(f"P6F3C SELF-TEST FAILED: accepted {rejected}", file=sys.stderr)
        return 1
    if "<redacted>" not in sanitize("Authorization: Bearer abc\nPASSWORD=xyz"):
        print("P6F3C SELF-TEST FAILED: redaction", file=sys.stderr)
        return 1
    print("P6F3C SELF-TEST PASS: privileged read-only guardrails enforced")
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.self_test:
        return self_test()
    observed, probes = collect()
    report = build_report(observed, probes)
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
