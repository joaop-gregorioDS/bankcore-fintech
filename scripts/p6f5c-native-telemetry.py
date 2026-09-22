#!/usr/bin/env python3
"""Read-only native-host telemetry sampler for P6-F5C-4."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any


class TelemetryError(ValueError):
    pass


def _readonly(argv: list[str], timeout: int = 8) -> str | None:
    allowed = argv[:3] == ["docker", "system", "df"] or argv[:3] == ["docker", "stats", "--no-stream"]
    if not allowed:
        raise TelemetryError("command is outside the Docker read-only allowlist")
    try:
        result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=timeout, check=False, shell=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def parse_cpu(text: str) -> tuple[int, int]:
    fields = text.splitlines()[0].split()
    if fields[0] != "cpu":
        raise TelemetryError("aggregate CPU line is missing")
    values = [int(value) for value in fields[1:9]]
    total = sum(values)
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return total, idle


def cpu_busy_ratio(before: tuple[int, int], after: tuple[int, int]) -> float:
    total_delta = after[0] - before[0]
    idle_delta = after[1] - before[1]
    if total_delta <= 0:
        raise TelemetryError("CPU counters did not advance")
    return max(0.0, min(1.0, 1.0 - idle_delta / total_delta))


def parse_meminfo(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].rstrip(":") in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
            result[parts[0].rstrip(":")] = int(parts[1]) * (1024 if len(parts) > 2 and parts[2] == "kB" else 1)
    if not {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"} <= result.keys():
        raise TelemetryError("required memory fields are missing")
    return result


def parse_vmstat(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in text.splitlines():
        key, value = line.split()[:2]
        if key in {"pswpin", "pswpout"}:
            result[key] = int(value)
    return result


def filesystem(path: str) -> dict[str, int] | None:
    try:
        value = os.statvfs(path)
        unit = value.f_frsize or value.f_bsize
        return {"total_bytes": value.f_blocks * unit, "available_bytes": value.f_bavail * unit,
                "total_inodes": value.f_files, "available_inodes": value.f_favail}
    except OSError:
        return None


def _docker_aggregate() -> dict[str, Any] | None:
    storage = _readonly(["docker", "system", "df", "--format", "{{json .}}"])
    stats = _readonly(["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}}\t{{.MemUsage}}\t{{.PIDs}}"])
    if storage is None or stats is None:
        return None
    return {"storage_rows": len(storage.splitlines()),
            "image_rows": sum('"Type":"Images"' in line for line in storage.splitlines()),
            "running_rows": len(stats.splitlines()), "stats_present": bool(stats.strip())}


def sample(phase: str, previous_cpu: tuple[int, int] | None = None) -> tuple[dict[str, Any], tuple[int, int]]:
    current_cpu = parse_cpu(Path("/proc/stat").read_text(encoding="ascii"))
    mem = parse_meminfo(Path("/proc/meminfo").read_text(encoding="ascii"))
    vm = parse_vmstat(Path("/proc/vmstat").read_text(encoding="ascii"))
    load = os.getloadavg()
    return {"phase": phase, "timestamp_epoch": time.time(), "logical_cpus": os.cpu_count(),
            "cpu_busy_ratio": cpu_busy_ratio(previous_cpu, current_cpu) if previous_cpu else None,
            "load1": load[0], "load5": load[1], "load15": load[2],
            "memory_total_bytes": mem["MemTotal"], "memory_available_bytes": mem["MemAvailable"],
            "swap_total_bytes": mem["SwapTotal"], "swap_io_pages": vm.get("pswpin", 0) + vm.get("pswpout", 0),
            "filesystems": {path: filesystem(path) for path in ("/", "/var/lib/docker", "/opt/bankcore")},
            "docker": _docker_aggregate()}, current_cpu


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only F5C-4 native telemetry sampler")
    parser.add_argument("--phase", required=True)
    parser.add_argument("--duration-seconds", type=float, required=True)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.duration_seconds <= 0 or args.interval_seconds <= 0:
        raise SystemExit("duration and interval must be positive")
    rows: list[dict[str, Any]] = []
    previous: tuple[int, int] | None = None
    end = time.monotonic() + args.duration_seconds
    while time.monotonic() < end:
        row, previous = sample(args.phase, previous)
        rows.append(row)
        time.sleep(args.interval_seconds)
    args.output.write_text(json.dumps({"schema": "bankcore-p6f5c-native-telemetry-v1", "samples": rows}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
