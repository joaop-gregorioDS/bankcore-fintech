#!/usr/bin/env python3
"""Fail-closed, read-only admission check for the F5C-4 native host."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

EXPECTED_CPUS = 4
MIN_MEMORY_BYTES = 14 * 1024**3
MAX_MEMORY_BYTES = 18 * 1024**3


class NativePreflightError(ValueError):
    pass


def _run_readonly(argv: list[str], timeout: int = 8) -> str:
    if not argv or argv[0] not in {"docker", "uname"}:
        raise NativePreflightError("command is outside the read-only allowlist")
    try:
        result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=timeout, check=False, shell=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NativePreflightError(f"read-only probe unavailable: {argv[0]}") from exc
    if result.returncode:
        raise NativePreflightError(f"read-only probe failed: {argv[0]}")
    return result.stdout.strip()


def _mem_total() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _filesystem(path: str) -> dict[str, int] | None:
    try:
        value = os.statvfs(path)
        unit = value.f_frsize or value.f_bsize
        return {"total_bytes": value.f_blocks * unit, "available_bytes": value.f_bavail * unit,
                "total_inodes": value.f_files, "available_inodes": value.f_favail}
    except OSError:
        return None


def _compose_available() -> bool:
    try:
        _run_readonly(["docker", "compose", "version"])
    except NativePreflightError:
        return False
    return True


def _docker_facts() -> dict[str, Any]:
    if shutil.which("docker") is None:
        raise NativePreflightError("docker is not installed")
    if os.environ.get("DOCKER_HOST"):
        raise NativePreflightError("remote DOCKER_HOST is forbidden")
    if _run_readonly(["docker", "context", "show"]) != "default":
        raise NativePreflightError("non-default or remote Docker context is forbidden")
    try:
        data = json.loads(_run_readonly(["docker", "info", "--format", "{{json .}}"]))
    except json.JSONDecodeError as exc:
        raise NativePreflightError("docker info was not parseable") from exc
    return {"server_version": data.get("ServerVersion"), "operating_system": data.get("OperatingSystem"),
            "kernel_version_present": bool(data.get("KernelVersion")), "cpus": data.get("NCPU"),
            "memory_total_bytes": data.get("MemTotal"), "storage_driver": data.get("Driver"),
            "compose_available": _compose_available()}


def validate_report(report: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if report.get("os") != "Linux": reasons.append("host_os_not_linux")
    if report.get("architecture") not in {"x86_64", "amd64"}: reasons.append("host_architecture_not_x86_64")
    if report.get("logical_cpus") != EXPECTED_CPUS: reasons.append("logical_cpu_profile_mismatch")
    memory = report.get("memory_total_bytes")
    if not isinstance(memory, int) or not MIN_MEMORY_BYTES <= memory <= MAX_MEMORY_BYTES:
        reasons.append("memory_profile_outside_14_to_18_gib")
    if not (report.get("docker") or {}).get("compose_available"): reasons.append("docker_compose_unavailable")
    if report.get("remote_engine_detected"): reasons.append("remote_engine_detected")
    if not report.get("docker_root_filesystem"): reasons.append("docker_root_filesystem_unknown")
    return reasons


def collect() -> dict[str, Any]:
    if not sys.platform.startswith("linux"):
        raise NativePreflightError("F5C-4 preflight must run on native Linux")
    report: dict[str, Any] = {"schema": "bankcore-p6f5c-native-preflight-v1", "os": platform.system(),
        "architecture": platform.machine(), "logical_cpus": os.cpu_count(), "memory_total_bytes": _mem_total(),
        "docker": _docker_facts(), "remote_engine_detected": bool(os.environ.get("DOCKER_HOST")),
        "docker_root_filesystem": _filesystem("/"), "persistent_filesystem": _filesystem("/var/lib"),
        "mutations_performed": False}
    report["admission"] = "PASS" if not validate_report(report) else "FAIL"
    report["reasons"] = validate_report(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only F5C-4 native host admission check")
    parser.add_argument("--output", type=Path, help="explicit path for sanitized JSON report")
    args = parser.parse_args()
    try:
        report = collect()
    except NativePreflightError as exc:
        print(f"PREFLIGHT FAILED: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output: args.output.write_text(rendered, encoding="utf-8")
    else: print(rendered, end="")
    return 0 if report["admission"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
