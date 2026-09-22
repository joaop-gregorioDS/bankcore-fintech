#!/usr/bin/env python3
"""Read-only Linux/Docker capacity sampler and conservative A+B policy gate.

Nothing is collected unless --collect is supplied. The collector has no sudo,
shell, filesystem-write, Docker lifecycle, or arbitrary-command interface.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COLLECTOR_VERSION = "p6f5c-1"
MIN_OBSERVATION_MINUTES = 60
PASS_CPU_RATIO = 0.70
FAIL_CPU_RATIO = 0.85
PASS_MEMORY_FLOOR_BYTES = 2 * 1024**3
FAIL_MEMORY_FLOOR_BYTES = 1 * 1024**3
PASS_DISK_FLOOR_BYTES = 20 * 1024**3
FAIL_DISK_FLOOR_BYTES = 10 * 1024**3

# Fixed read-only Docker CLI invocations only. No user-supplied command or shell.
DOCKER_COMMANDS = (
    ("docker", "info", "--format", "{{.ServerVersion}}\t{{.DockerRootDir}}"),
    ("docker", "ps", "--all", "--quiet"),
    ("docker", "ps", "--quiet"),
    ("docker", "stats", "--no-stream", "--format", "{{json .}}"),
    ("docker", "image", "ls", "--quiet", "--no-trunc"),
    ("docker", "volume", "ls", "--quiet"),
    ("docker", "system", "df", "--format", "{{json .}}"),
)


class CapacityError(ValueError):
    pass


def _parse_size(value: str) -> int:
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*([kmgtpe]?i?b)?\s*", value, re.IGNORECASE)
    if not match:
        raise CapacityError("unrecognized size field")
    number = float(match.group(1))
    unit = (match.group(2) or "B").lower()
    prefixes = {"b": 0, "kb": 1, "mb": 2, "gb": 3, "tb": 4, "pb": 5, "eb": 6,
                "kib": 1, "mib": 2, "gib": 3, "tib": 4, "pib": 5, "eib": 6}
    if unit not in prefixes:
        raise CapacityError("unrecognized size unit")
    base = 1024 if "i" in unit or unit == "b" else 1000
    return int(number * base**prefixes[unit])


def parse_meminfo(text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"([A-Za-z_()]+):\s+(\d+)\s+kB", line.strip())
        if match:
            values[match.group(1)] = int(match.group(2)) * 1024
    required = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    if not required.issubset(values) or values["MemAvailable"] > values["MemTotal"] or values["SwapFree"] > values["SwapTotal"]:
        raise CapacityError("memory telemetry is incomplete or inconsistent")
    return values


def parse_cpu_stat(text: str) -> tuple[int, int]:
    first = text.splitlines()[0].split()
    if not first or first[0] != "cpu" or len(first) < 5:
        raise CapacityError("CPU counters are unavailable")
    counters = [int(value) for value in first[1:9]]
    total = sum(counters)
    idle = counters[3] + (counters[4] if len(counters) > 4 else 0)
    if total <= 0 or idle > total:
        raise CapacityError("CPU counters are invalid")
    return total, idle


def cpu_busy_ratio(before: tuple[int, int], after: tuple[int, int]) -> float:
    total_delta = after[0] - before[0]
    idle_delta = after[1] - before[1]
    if total_delta <= 0 or idle_delta < 0 or idle_delta > total_delta:
        raise CapacityError("CPU sample interval is invalid")
    return (total_delta - idle_delta) / total_delta


def parse_swap_vmstat(text: str) -> dict[str, int]:
    values = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in {"pswpin", "pswpout"}:
            values[parts[0]] = int(parts[1])
    if set(values) != {"pswpin", "pswpout"}:
        raise CapacityError("swap activity counters are unavailable")
    return values


def _size_pair(value: str) -> tuple[int, int]:
    parts = value.split(" / ", 1)
    if len(parts) != 2:
        raise CapacityError("container memory sample is malformed")
    return _parse_size(parts[0]), _parse_size(parts[1])


def parse_docker_stats(lines: list[str]) -> list[dict[str, float | int]]:
    samples = []
    try:
        decoded = [json.loads(line) for line in lines if line.strip()]
        decoded.sort(key=lambda item: (str(item.get("ID", "")), str(item.get("Name", ""))))
        for item in decoded:
            used, limit = _size_pair(str(item["MemUsage"]))
            cpu = float(str(item["CPUPerc"]).rstrip("%"))
            pids = int(str(item["PIDs"]))
            if min(used, limit, pids, cpu) < 0 or (limit and used > limit):
                raise ValueError
            samples.append({"cpu_percent": cpu, "memory_used_bytes": used, "memory_limit_bytes": limit, "pids": pids})
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, CapacityError) as exc:
        raise CapacityError("Docker stats response is incomplete or invalid") from exc
    return [{"container": f"container_{index:03d}", **sample} for index, sample in enumerate(samples, 1)]


def parse_docker_df(lines: list[str]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    try:
        for line in lines:
            if not line.strip():
                continue
            item = json.loads(line)
            kind = str(item["Type"])
            result[kind] = {"count": int(item["TotalCount"]), "size_bytes": _parse_size(str(item["Size"]))}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, CapacityError) as exc:
        raise CapacityError("Docker storage summary is incomplete or invalid") from exc
    if not result:
        raise CapacityError("Docker storage summary is empty")
    return result


def evaluate_capacity(evidence: dict[str, Any]) -> dict[str, Any]:
    """Evaluate sanitized A+B peak estimates. Unknown/incomplete evidence never PASSes."""
    reasons: list[str] = []
    failures: list[str] = []
    if evidence.get("schema") != "bankcore-p6f5c-evidence-v1":
        reasons.append("unknown_or_unproven:evidence_schema")
    host = evidence.get("host", {})
    projected = evidence.get("projection", {})

    def required(mapping: dict[str, Any], key: str, label: str) -> Any | None:
        if key not in mapping or mapping[key] is None:
            reasons.append(f"unknown:{label}")
            return None
        return mapping[key]

    duration = required(evidence, "observation_minutes", "observation_window")
    samples = required(evidence, "sample_count", "sample_count")
    cores = required(host, "cpu_cores", "host_cpu")
    total_memory = required(host, "memory_total_bytes", "host_memory")
    pid_max = required(host, "pid_max", "host_pid_limit")
    process_count = required(host, "process_count", "host_process_count")
    if duration is not None and duration < MIN_OBSERVATION_MINUTES:
        reasons.append("insufficient:observation_window_under_60_minutes")
    if samples is not None and samples < 12:
        reasons.append("insufficient:fewer_than_12_samples")
    if (cores is not None and cores <= 0) or (total_memory is not None and total_memory <= 0):
        failures.append("invalid:host_capacity")

    cpu = required(projected, "cpu_busy_p95_ratio", "projected_cpu_p95")
    load5 = required(projected, "load5_per_core_p95", "projected_load5")
    load1 = required(projected, "load1_per_core_peak", "projected_load1_peak")
    available_memory = required(projected, "memory_available_after_peak_bytes", "projected_memory_headroom")
    swap_pages = required(projected, "swap_io_pages_during_peak", "swap_activity")
    extra_processes = required(projected, "additional_peak_processes", "additional_processes")

    numeric_fields = {
        "host_cpu_cores": cores,
        "host_memory_bytes": total_memory,
        "host_pid_max": pid_max,
        "host_process_count": process_count,
        "projected_cpu_busy_p95": cpu,
        "projected_load5_per_core": load5,
        "projected_load1_per_core": load1,
        "projected_memory_headroom": available_memory,
        "projected_swap_io_pages": swap_pages,
        "projected_additional_processes": extra_processes,
    }
    for label, value in numeric_fields.items():
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            failures.append(f"invalid:{label}")
    if cpu is not None and isinstance(cpu, (int, float)) and cpu > 1:
        failures.append("invalid:projected_cpu_ratio")
    if available_memory is not None and total_memory is not None and available_memory > total_memory:
        failures.append("invalid:projected_memory_headroom")
    if pid_max is not None and process_count is not None and process_count > pid_max:
        failures.append("invalid:host_process_count_exceeds_pid_max")

    if cpu is not None:
        if cpu > FAIL_CPU_RATIO:
            failures.append("capacity:projected_cpu_over_85_percent")
        elif cpu > PASS_CPU_RATIO:
            reasons.append("margin:projected_cpu_over_70_percent")
    if load5 is not None:
        if load5 > FAIL_CPU_RATIO:
            failures.append("capacity:projected_load5_over_0_85_per_core")
        elif load5 > PASS_CPU_RATIO:
            reasons.append("margin:projected_load5_over_0_70_per_core")
    if load1 is not None:
        if load1 > 1.5:
            failures.append("capacity:projected_load1_over_1_5_per_core")
        elif load1 > 1.0:
            reasons.append("margin:projected_load1_over_1_0_per_core")

    if available_memory is not None and total_memory is not None and total_memory > 0:
        pass_floor = max(PASS_MEMORY_FLOOR_BYTES, int(total_memory * 0.25))
        fail_floor = max(FAIL_MEMORY_FLOOR_BYTES, int(total_memory * 0.15))
        if available_memory < fail_floor:
            failures.append("capacity:post_peak_memory_headroom_below_hard_floor")
        elif available_memory < pass_floor:
            reasons.append("margin:post_peak_memory_headroom_below_25_percent_or_2gib")
    if swap_pages is not None and swap_pages > 0:
        failures.append("capacity:swap_io_during_peak")

    if pid_max is not None and process_count is not None and extra_processes is not None and pid_max > 0:
        projected_pid_ratio = (process_count + extra_processes) / pid_max
        if projected_pid_ratio > 0.85:
            failures.append("capacity:projected_processes_over_85_percent_pid_max")
        elif projected_pid_ratio > 0.70:
            reasons.append("margin:projected_processes_over_70_percent_pid_max")

    filesystems = required(host, "filesystems", "filesystem_baseline")
    projected_disk = required(projected, "disk_available_after_peak_bytes", "projected_disk_headroom")
    projected_inodes = required(projected, "inodes_available_after_peak", "projected_inode_headroom")
    if filesystems is not None and not filesystems:
        reasons.append("unknown:filesystem_baseline_empty")
    if filesystems is not None and projected_disk is not None and projected_inodes is not None:
        if set(projected_disk) != set(filesystems) or set(projected_inodes) != set(filesystems):
            reasons.append("unknown:filesystem_projection_coverage")
        for label, baseline in filesystems.items():
            disk_after = projected_disk.get(label)
            inode_after = projected_inodes.get(label)
            total_disk = baseline.get("total_bytes")
            total_inodes = baseline.get("total_inodes")
            if None in (disk_after, inode_after, total_disk, total_inodes) or total_disk <= 0 or total_inodes <= 0:
                reasons.append(f"unknown:filesystem_budget_{label}")
                continue
            pass_disk = max(PASS_DISK_FLOOR_BYTES, int(total_disk * 0.25))
            fail_disk = max(FAIL_DISK_FLOOR_BYTES, int(total_disk * 0.15))
            if disk_after < fail_disk:
                failures.append(f"capacity:filesystem_{label}_below_disk_hard_floor")
            elif disk_after < pass_disk:
                reasons.append(f"margin:filesystem_{label}_below_disk_pass_floor")
            inode_ratio = inode_after / total_inodes
            if inode_ratio < 0.10:
                failures.append(f"capacity:filesystem_{label}_below_10_percent_inodes")
            elif inode_ratio < 0.20:
                reasons.append(f"margin:filesystem_{label}_below_20_percent_inodes")

    for flag, label in (
        ("peak_includes_migrations", "migration_peak"),
        ("peak_includes_release_pull_and_retained_A", "release_and_rollback_storage"),
        ("peak_includes_financial_smoke", "financial_smoke_load"),
        ("release_images_are_digest_pinned", "immutable_release_identity"),
        ("candidate_build_is_off_host", "off_host_image_build"),
    ):
        if not projected.get(flag, False):
            reasons.append(f"unknown_or_unproven:{label}")

    if not evidence.get("representative_peak_period", False):
        reasons.append("unknown_or_unproven:representative_peak_period")
    if not evidence.get("staging_profile_complete", False):
        reasons.append("unknown_or_unproven:staging_profile_complete")

    if failures:
        status = "FAIL"
    elif reasons:
        status = "CONDITIONAL"
    else:
        status = "PASS"
    return {"status": status, "reasons": sorted(set(reasons)), "failures": sorted(set(failures))}


def _read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="ascii")
    except OSError as exc:
        raise CapacityError("required read-only kernel telemetry is unavailable") from exc


def _meminfo(text: str) -> dict[str, int]:
    values = parse_meminfo(text)
    total = values["MemTotal"]
    available = values["MemAvailable"]
    swap_total = values["SwapTotal"]
    swap_free = values["SwapFree"]
    return {
        "total_bytes": total,
        "available_bytes": available,
        "used_bytes": total - available,
        "cached_bytes": max(values.get("Cached", 0) + values.get("SReclaimable", 0) - values.get("Shmem", 0), 0),
        "swap_total_bytes": swap_total,
        "swap_free_bytes": swap_free,
        "swap_used_bytes": swap_total - swap_free,
    }


def _filesystem(path: Path) -> dict[str, int] | None:
    try:
        statvfs = os.statvfs(path)
    except OSError:
        return None
    fragment = statvfs.f_frsize or statvfs.f_bsize
    total_bytes = statvfs.f_blocks * fragment
    available_bytes = statvfs.f_bavail * fragment
    total_inodes = statvfs.f_files
    available_inodes = statvfs.f_favail
    return {
        "total_bytes": total_bytes,
        "available_bytes": available_bytes,
        "used_bytes": max(total_bytes - statvfs.f_bfree * fragment, 0),
        "total_inodes": total_inodes,
        "available_inodes": available_inodes,
        "used_inodes": max(total_inodes - statvfs.f_ffree, 0),
    }


def _run_docker(argv: tuple[str, ...]) -> str:
    if argv not in DOCKER_COMMANDS:
        raise CapacityError("Docker command is not on the read-only allowlist")
    try:
        result = subprocess.run(argv, check=False, capture_output=True, text=True, timeout=20, shell=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CapacityError("Docker read-only query unavailable") from exc
    if result.returncode:
        raise CapacityError("Docker read-only query unavailable")
    return result.stdout


def collect(sample_seconds: int = 5) -> dict[str, Any]:
    if not sys.platform.startswith("linux") or not Path("/proc/stat").is_file():
        raise CapacityError("collection is supported only on Linux with procfs")
    if not 1 <= sample_seconds <= 60:
        raise CapacityError("sample interval must be between 1 and 60 seconds")

    cpu_before = parse_cpu_stat(_read_text("/proc/stat"))
    swap_before = parse_swap_vmstat(_read_text("/proc/vmstat"))
    time.sleep(sample_seconds)
    cpu_after = parse_cpu_stat(_read_text("/proc/stat"))
    swap_after = parse_swap_vmstat(_read_text("/proc/vmstat"))
    try:
        load1, load5, load15 = os.getloadavg()
    except OSError as exc:
        raise CapacityError("load average is unavailable") from exc

    mem = _meminfo(_read_text("/proc/meminfo"))
    cores = os.cpu_count() or 0
    process_count = sum(entry.name.isdecimal() for entry in Path("/proc").iterdir())
    try:
        pid_max = int(_read_text("/proc/sys/kernel/pid_max").strip())
    except ValueError as exc:
        raise CapacityError("kernel PID limit is invalid") from exc

    fs: dict[str, dict[str, int] | None] = {
        "root": _filesystem(Path("/")),
        "legacy_app": _filesystem(Path("/var/www/bankcore")),
        "candidate_root": _filesystem(Path("/opt/bankcore")),
    }
    docker_data: dict[str, Any] = {"status": "unavailable"}
    try:
        info = _run_docker(DOCKER_COMMANDS[0]).strip().split("\t", 1)
        if len(info) != 2 or not info[0] or not info[1]:
            raise CapacityError("Docker info response is invalid")
        docker_root = Path(info[1])
        fs["docker_root"] = _filesystem(docker_root)
        all_ids = [line for line in _run_docker(DOCKER_COMMANDS[1]).splitlines() if line.strip()]
        running_ids = [line for line in _run_docker(DOCKER_COMMANDS[2]).splitlines() if line.strip()]
        images = {line for line in _run_docker(DOCKER_COMMANDS[4]).splitlines() if line.strip()}
        volumes = {line for line in _run_docker(DOCKER_COMMANDS[5]).splitlines() if line.strip()}
        stats_lines = _run_docker(DOCKER_COMMANDS[3]).splitlines()
        stats = parse_docker_stats(stats_lines)
        disk = parse_docker_df(_run_docker(DOCKER_COMMANDS[6]).splitlines())
        docker_data = {
            "status": "available",
            "server_version": info[0],
            "container_count_all": len(all_ids),
            "container_count_running": len(running_ids),
            "image_count": len(images),
            "volume_count": len(volumes),
            "stats_by_opaque_container": stats,
            "stats_totals": {
                "cpu_percent_sum": round(sum(float(row["cpu_percent"]) for row in stats), 3),
                "memory_used_bytes_sum": sum(int(row["memory_used_bytes"]) for row in stats),
                "pids_sum": sum(int(row["pids"]) for row in stats),
                "pids_peak": max((int(row["pids"]) for row in stats), default=0),
            },
            "disk_usage_by_type": disk,
        }
    except CapacityError:
        fs.pop("docker_root", None)

    return {
        "schema": "bankcore-p6f5c-sample-v1",
        "collector_version": COLLECTOR_VERSION,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_seconds": sample_seconds,
        "host": {
            "cpu_logical_cores": cores,
            "cpu_busy_ratio_sample": round(cpu_busy_ratio(cpu_before, cpu_after), 4),
            "load_average": {"1m": load1, "5m": load5, "15m": load15},
            "load_per_core": {"1m": load1 / cores if cores else None, "5m": load5 / cores if cores else None, "15m": load15 / cores if cores else None},
            "memory": mem,
            "swap_io_pages_delta": {key: max(swap_after[key] - swap_before[key], 0) for key in swap_before},
            "process_count": process_count,
            "pid_max": pid_max,
            "filesystems": fs,
        },
        "docker": docker_data,
        "privacy": {"hostname_included": False, "container_names_included": False, "container_ids_included": False, "image_tags_included": False, "environment_variables_read": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="P6-F5C read-only capacity sampler/evaluator")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--collect", action="store_true", help="collect a local Linux sample using read-only procfs/statvfs/Docker queries")
    modes.add_argument("--evaluate", type=Path, help="evaluate a sanitized A+B evidence JSON document")
    parser.add_argument("--sample-seconds", type=int, default=5)
    args = parser.parse_args()
    if args.collect:
        result = collect(args.sample_seconds)
    else:
        try:
            evidence = json.loads(args.evaluate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CapacityError("capacity evidence file is unavailable or invalid") from exc
        result = evaluate_capacity(evidence)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CapacityError as error:
        print(f"P6-F5C STOP: {error}", file=sys.stderr)
        raise SystemExit(2)
