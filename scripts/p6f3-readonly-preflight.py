#!/usr/bin/env python3
"""Generate a strictly read-only Linux host preflight report.

The probe runner intentionally has no shell mode, no privilege escalation, no
filesystem writes, and no lifecycle commands. It is suitable for a later
read-only SSH session, but this phase only validates it locally.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Iterable


EXPECTED = {
    "deploy_user": "bankcore (non-root)",
    "docker_mode": "rootless",
    "release_root": "/opt/bankcore",
    "public_tcp_ports": [80, 443],
    "internal_tcp_ports": [5432, 6379, 8080, 9092, 9093, 3000, 4317, 4318, 8889, 13133],
    "secrets_policy": "presence/metadata only; no secret values",
    "change_policy": "inventory only; no mutations",
}

READ_ONLY_PROGRAMS = {
    "cat",
    "command",
    "crontab",
    "df",
    "docker",
    "find",
    "findmnt",
    "free",
    "getconf",
    "getent",
    "id",
    "iptables",
    "ls",
    "mountpoint",
    "nft",
    "nginx",
    "nproc",
    "openssl",
    "ps",
    "service",
    "sshd",
    "ss",
    "stat",
    "systemctl",
    "uname",
    "ufw",
}

FORBIDDEN_TOKENS = {
    "apply",
    "chgrp",
    "chmod",
    "chown",
    "compose-up",
    "create",
    "down",
    "enable",
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
    "systemctl-enable",
    "ufw-allow",
    "ufw-deny",
    "useradd",
}

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


def sanitize(text: str, *, limit: int = 2500) -> str:
    """Redact values before they can reach a report or terminal."""

    text = PEM_BLOCK.sub("<redacted-pem>", text)
    text = URI_CREDENTIALS.sub(r"\1<redacted>\2", text)
    lines: list[str] = []
    for line in text.splitlines():
        if SENSITIVE_LINE.search(line):
            if "=" in line:
                lines.append(f"{line.split('=', 1)[0]}=<redacted>")
            else:
                lines.append("<redacted-sensitive-line>")
        elif ENV_ASSIGNMENT.match(line):
            lines.append(f"{line.split('=', 1)[0]}=<present>")
        else:
            lines.append(line)
    cleaned = "\n".join(lines).strip()
    if len(cleaned) > limit:
        return cleaned[:limit] + "\n<truncated>"
    return cleaned


def validate_read_only_command(argv: list[str]) -> None:
    """Reject anything outside the deliberately small inspection vocabulary."""

    if not argv or argv[0] not in READ_ONLY_PROGRAMS:
        raise ValueError(f"program is not allowlisted: {argv[0] if argv else '<empty>'}")
    if any(token in FORBIDDEN_TOKENS for token in argv):
        raise ValueError(f"mutating token rejected: {argv}")
    if any(token in {"-c", "--command", "--shell"} for token in argv[1:]):
        raise ValueError("shell command execution is forbidden")


def probe(name: str, argv: list[str], *, timeout: int = 15) -> Probe:
    validate_read_only_command(argv)
    command = " ".join(argv)
    try:
        result = subprocess.run(
            argv,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return Probe(name, command, "unavailable", None, "program not installed")
    except subprocess.TimeoutExpired:
        return Probe(name, command, "timeout", None, "probe timed out")
    output = sanitize((result.stdout or "") + (result.stderr or ""))
    status = "ok" if result.returncode == 0 else "unavailable"
    return Probe(name, command, status, result.returncode, output)


def first_line(probe_result: Probe) -> str:
    return next((line for line in probe_result.output.splitlines() if line.strip()), "unavailable")


def parse_ports(text: str) -> list[int]:
    ports: set[int] = set()
    for match in re.finditer(r"(?::|\s)(\d{1,5})(?:\s|$)", text):
        port = int(match.group(1))
        if 1 <= port <= 65535:
            ports.add(port)
    return sorted(ports)


def collect() -> tuple[dict, list[Probe]]:
    probes: list[Probe] = []

    def add(name: str, argv: list[str], *, timeout: int = 15) -> Probe:
        item = probe(name, argv, timeout=timeout)
        probes.append(item)
        return item

    os_release = add("os_release", ["cat", "/etc/os-release"])
    kernel = add("kernel", ["uname", "-a"])
    architecture = add("architecture", ["uname", "-m"])
    cpu = add("cpu_count", ["nproc"])
    memory = add("memory", ["free", "-b"])
    disk = add("disk", ["df", "-P", "-B1", "/", "/opt"])
    bankcore_user = add("bankcore_user", ["getent", "passwd", "bankcore"])
    bankcore_id = add("bankcore_identity", ["id", "bankcore"])
    groups = add("relevant_groups", ["getent", "group", "docker"])
    ssh = add("ssh_effective_config", ["sshd", "-T"])
    docker_info = add("docker_info", ["docker", "info"], timeout=30)
    docker_version = add("docker_version", ["docker", "version"], timeout=30)
    compose_version = add("compose_version", ["docker", "compose", "version"], timeout=30)
    containers = add("docker_containers", ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"], timeout=30)
    images = add("docker_images", ["docker", "image", "ls", "--digests", "--format", "{{.Repository}}\t{{.Tag}}\t{{.Digest}}"], timeout=30)
    networks = add("docker_networks", ["docker", "network", "ls", "--format", "{{.Name}}\t{{.Driver}}"], timeout=30)
    volumes = add("docker_volumes", ["docker", "volume", "ls", "--format", "{{.Name}}\t{{.Driver}}"], timeout=30)
    listening = add("listening_ports", ["ss", "-lntup"])
    nginx_version = add("nginx_version", ["nginx", "-V"], timeout=15)
    nginx_config = add("nginx_config_metadata", ["nginx", "-T"], timeout=20)
    tls_files = add("tls_certificate_paths", ["find", "/etc/letsencrypt", "/etc/nginx", "-maxdepth", "4", "-type", "f", "-printf", "%p\t%u\t%g\t%m\n"], timeout=20)
    ufw = add("ufw_status", ["ufw", "status", "verbose"])
    nft = add("nftables", ["nft", "list", "ruleset"], timeout=20)
    iptables = add("iptables", ["iptables", "-S"])
    filesystem = add("bankcore_paths", ["find", "/opt/bankcore", "/home/bankcore", "-maxdepth", "3", "-printf", "%p\t%u\t%g\t%m\n"], timeout=20)
    mounts = add("mounts", ["findmnt", "-rn", "-o", "TARGET,SOURCE,FSTYPE,OPTIONS"])
    services = add("systemd_services", ["systemctl", "list-units", "--type=service", "--all", "--no-legend", "--no-pager"])
    timers = add("systemd_timers", ["systemctl", "list-timers", "--all", "--no-legend", "--no-pager"])
    cron = add("system_cron_paths", ["find", "/etc/cron.d", "/etc/cron.daily", "/etc/cron.hourly", "/etc/cron.monthly", "/etc/cron.weekly", "-maxdepth", "2", "-type", "f", "-printf", "%p\t%u\t%g\t%m\n"], timeout=20)
    user_cron = add("bankcore_user_cron", ["crontab", "-l"])
    process_services = add("service_processes", ["ps", "-eo", "user,pid,comm,args", "--sort=comm"])
    service_state = add("database_cache_broker_services", ["systemctl", "is-active", "postgresql", "redis-server", "kafka"])
    persistence = add("persistence_mounts", ["cat", "/etc/fstab"])
    backups = add("backup_paths", ["find", "/opt/bankcore/backups", "-maxdepth", "3", "-mindepth", "1", "-printf", "%p\t%u\t%g\t%m\n"], timeout=20)
    config_names = add("config_and_secret_metadata", ["find", "/opt/bankcore/config", "/opt/bankcore/secrets", "-maxdepth", "3", "-type", "f", "-printf", "%p\t%u\t%g\t%m\n"], timeout=20)

    observed_ports = parse_ports(listening.output)
    observed = {
        "os": first_line(os_release),
        "kernel": first_line(kernel),
        "architecture": first_line(architecture),
        "cpu": first_line(cpu),
        "memory": first_line(memory),
        "disk": first_line(disk),
        "bankcore_user": "present" if bankcore_user.status == "ok" else "not observed",
        "bankcore_identity": first_line(bankcore_id),
        "docker_group": "present" if groups.status == "ok" else "not observed",
        "ssh_effective_config": "available" if ssh.status == "ok" else ssh.status,
        "docker_info": "available" if docker_info.status == "ok" else docker_info.status,
        "docker_version": first_line(docker_version),
        "compose_version": first_line(compose_version),
        "docker_rootless_signal": "rootless mentioned" if "rootless" in docker_info.output.lower() else "not observed",
        "containers": "inventory collected" if containers.status == "ok" else containers.status,
        "images": "inventory collected" if images.status == "ok" else images.status,
        "networks": "inventory collected" if networks.status == "ok" else networks.status,
        "volumes": "inventory collected" if volumes.status == "ok" else volumes.status,
        "listening_ports": observed_ports,
        "nginx": "available" if nginx_version.status == "ok" else nginx_version.status,
        "nginx_config": "metadata collected" if nginx_config.status == "ok" else nginx_config.status,
        "tls_certificate_metadata": "paths/metadata collected" if tls_files.status == "ok" else tls_files.status,
        "firewall": {
            "ufw": ufw.status,
            "nftables": nft.status,
            "iptables": iptables.status,
        },
        "filesystem_ownership": "metadata collected" if filesystem.status == "ok" else filesystem.status,
        "mounts": "collected" if mounts.status == "ok" else mounts.status,
        "systemd_services": "collected" if services.status == "ok" else services.status,
        "systemd_timers": "collected" if timers.status == "ok" else timers.status,
        "cron": "collected" if cron.status == "ok" else cron.status,
        "bankcore_user_cron": "collected" if user_cron.status == "ok" else user_cron.status,
        "service_processes": "collected" if process_services.status == "ok" else process_services.status,
        "database_cache_broker_services": "collected" if service_state.status == "ok" else service_state.status,
        "persistence": "collected" if persistence.status == "ok" else persistence.status,
        "backups": "metadata collected" if backups.status == "ok" else backups.status,
        "config_secret_values": "not read; names/metadata only",
        "config_secret_metadata": "collected" if config_names.status == "ok" else config_names.status,
    }
    return observed, probes


def build_report(observed: dict, probes: list[Probe]) -> dict:
    ports = set(observed.get("listening_ports", []))
    public_expected = set(EXPECTED["public_tcp_ports"])
    internal_expected = set(EXPECTED["internal_tcp_ports"])
    drift: list[str] = []
    proposals: list[str] = []
    risks: list[str] = []
    rollback: list[str] = []

    if observed.get("bankcore_user") != "present":
        drift.append("bankcore deploy user was not observed")
        proposals.append("Review creation of the non-root bankcore user before any mutation")
        risks.append("Deploy cannot be safely isolated from root")
        rollback.append("Do not proceed; no remote mutation has been authorized")
    if observed.get("docker_rootless_signal") != "rootless mentioned":
        drift.append("rootless Docker was not confirmed by read-only output")
        proposals.append("Verify rootless Docker and Compose contract during the reviewed change plan")
        risks.append("Rootful Docker would expand blast radius")
        rollback.append("Keep deployment blocked until rootless mode is proven")
    unexpected_public = sorted(ports - public_expected)
    if unexpected_public:
        drift.append(f"listening-port inventory includes ports outside expected public set: {unexpected_public}")
        proposals.append("Classify each listener and close or bind internal services privately")
        risks.append("Unexpected exposure may bypass the intended gateway boundary")
        rollback.append("Do not alter firewall remotely in this phase; prepare an explicit reviewed rule change")
    if not public_expected.issubset(ports):
        drift.append("one or more expected public ports were not observed")
        proposals.append("Confirm whether the gateway is intentionally absent or bound elsewhere")
        risks.append("Changing listeners without service ownership could interrupt access")
        rollback.append("Preserve the existing listener set until a tested gateway plan exists")
    if observed.get("config_secret_values") != "not read; names/metadata only":
        drift.append("secret-value read guard failed")
        proposals.append("Stop and fix the preflight before any host access")
        risks.append("Secret disclosure")
        rollback.append("Discard the report and rotate any exposed credential")

    unavailable = [item.name for item in probes if item.status != "ok"]
    return {
        "schema": "bankcore.p6f3.readonly-preflight.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read-only",
        "observed": observed,
        "expected": EXPECTED,
        "drift": drift or ["No contract drift detected by available probes; unavailable probes remain unverified"],
        "proposed_change": proposals or ["No mutation proposed by this read-only preflight"],
        "risk": risks or ["No immediate contract risk detected; this is not a production readiness decision"],
        "rollback": rollback or ["No rollback action; this script performs no mutation"],
        "unverified_probes": unavailable,
        "probes": [asdict(item) for item in probes],
        "safety": {
            "shell": False,
            "privilege_escalation": False,
            "filesystem_writes": False,
            "docker_lifecycle": False,
            "firewall_changes": False,
            "service_changes": False,
            "secret_values_read": False,
        },
    }


def markdown(report: dict) -> str:
    lines = [
        "# P6-F3A — VPS Read-only Preflight Report",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Generated: `{report['generated_at']}`",
        "- Mode: **read-only**",
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
        "",
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


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    parser.add_argument("--self-test", action="store_true", help="run only local safety assertions")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.self_test:
        validate_read_only_command(["uname", "-a"])
        try:
            validate_read_only_command(["rm", "-rf", "/"])
        except ValueError:
            print("P6F3 SELF-TEST PASS: mutating command rejected")
            return 0
        print("P6F3 SELF-TEST FAILED: mutating command accepted", file=sys.stderr)
        return 1
    observed, probes = collect()
    report = build_report(observed, probes)
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else markdown(report), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
