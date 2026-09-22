#!/usr/bin/env python3
"""Measure a digest-pinned P6-E A/B rehearsal inside disposable Linux/Docker.

The host mode builds/runs the existing P6-F2 disposable target and always
removes it. The inside mode measures only that disposable target. No VPS,
source dumps, or production databases are accessed.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import math
import os
import re
import stat
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "artifacts" / "p6f5c" / "vps-baseline.json"
TARGET_DOCKERFILE = ROOT / "infra" / "ansible" / "tests" / "p6f2-target.Dockerfile"
TARGET_CPU_LIMIT = 4
TARGET_MEMORY_LIMIT_BYTES = 15 * 1024**3
SAMPLE_INTERVAL_SECONDS = 1.0
IDLE_SECONDS = 20
READINESS_HOLD_SECONDS = 10
STABLE_HOLD_SECONDS = 20
PHASES_REQUIRED = {
    "baseline_idle",
    "migrations",
    "service_startup_readiness",
    "readiness_validation",
    "steady_state",
    "financial_smoke",
    "retained_A_B_images",
    "rollback_A",
    "smoke_failure_injection",
}
COMPOSE_SERVICES = (
    "postgres", "audit-postgres", "redis", "kafka", "otel-collector", "prometheus", "grafana",
    "migrate-auth", "migrate-transactions", "migrate-risk", "migrate-audit", "kafka-init",
    "auth-service", "transactions-service", "risk-service", "outbox-publisher", "audit-consumer", "nginx",
)
MIGRATION_SERVICES = {"migrate-auth", "migrate-transactions", "migrate-risk", "migrate-audit"}
APP_READY_SERVICES = {"auth-service", "transactions-service", "risk-service", "nginx"}


class CapacityRehearsalError(ValueError):
    pass


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CapacityRehearsalError("required BankCore runner module is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_p6e() -> Any:
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    return _load_module("p6e_deploy_rollback", ROOT / "scripts" / "p6e-deploy-rollback.py")


def _load_capacity_module() -> Any:
    return _load_module("p6f5c_capacity", ROOT / "scripts" / "p6f5c-capacity.py")


def _p6e_args(p6e: Any, bundle_root: Path, mode: str) -> argparse.Namespace:
    return argparse.Namespace(
        release_a=bundle_root / "release-a" / "manifest.json",
        release_b=bundle_root / "release-b" / "manifest.json",
        smoke_a="python3 scripts/p6e-financial-acceptance.py smoke",
        smoke_b="python3 scripts/p6e-financial-acceptance.py smoke",
        snapshot_command="python3 scripts/p6e-financial-acceptance.py snapshot",
        failure_command="exit 97",
        failure_mode=mode,
        health_only=False,
        state_dir=None,
    )


def _parse_cgroup_file(path: Path) -> dict[str, int] | None:
    try:
        values: dict[str, int] = {}
        for line in path.read_text(encoding="ascii").splitlines():
            key, value = line.split()
            values[key] = int(value)
        return values
    except (OSError, ValueError):
        return None


def _cgroup_v2() -> dict[str, int | None]:
    result: dict[str, int | None] = {"cpu_quota_cores": None, "cpu_usage_usec": None,
                                    "memory_current_bytes": None, "memory_max_bytes": None,
                                    "memory_swap_current_bytes": None, "pids_current": None, "pids_max": None}
    cpu_max = Path("/sys/fs/cgroup/cpu.max")
    try:
        quota, period = cpu_max.read_text(encoding="ascii").split()
        if quota != "max" and int(period) > 0:
            result["cpu_quota_cores"] = int(quota) / int(period)
    except (OSError, ValueError):
        pass
    cpu_stat = _parse_cgroup_file(Path("/sys/fs/cgroup/cpu.stat"))
    if cpu_stat:
        result["cpu_usage_usec"] = cpu_stat.get("usage_usec")
    for filename, key in (("memory.current", "memory_current_bytes"),
                          ("memory.max", "memory_max_bytes"),
                          ("memory.swap.current", "memory_swap_current_bytes"),
                          ("pids.current", "pids_current"),
                          ("pids.max", "pids_max")):
        try:
            value = Path("/sys/fs/cgroup", filename).read_text(encoding="ascii").strip()
            result[key] = None if value == "max" else int(value)
        except (OSError, ValueError):
            pass
    return result


def _cpu_total_idle(text: str) -> tuple[int, int] | None:
    try:
        first = text.splitlines()[0].split()
        counters = [int(value) for value in first[1:9]]
        if first[0] != "cpu" or len(counters) < 4:
            return None
        return sum(counters), counters[3] + (counters[4] if len(counters) > 4 else 0)
    except (IndexError, ValueError):
        return None


def _meminfo(capacity: Any) -> dict[str, int] | None:
    try:
        values = capacity.parse_meminfo(Path("/proc/meminfo").read_text(encoding="ascii"))
        return {"total_bytes": values["MemTotal"], "available_bytes": values["MemAvailable"],
                "used_bytes": values["MemTotal"] - values["MemAvailable"],
                "swap_total_bytes": values["SwapTotal"], "swap_free_bytes": values["SwapFree"]}
    except (OSError, ValueError, KeyError):
        return None


def _fs_sample(path: Path) -> dict[str, int] | None:
    try:
        vfs = os.statvfs(path)
        size = vfs.f_frsize or vfs.f_bsize
        return {"total_bytes": vfs.f_blocks * size, "available_bytes": vfs.f_bavail * size,
                "used_bytes": max((vfs.f_blocks - vfs.f_bfree) * size, 0),
                "total_inodes": vfs.f_files, "available_inodes": vfs.f_favail,
                "used_inodes": max(vfs.f_files - vfs.f_ffree, 0)}
    except OSError:
        return None


def _run_readonly(argv: list[str], timeout: int = 8) -> str | None:
    try:
        result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=timeout, check=False, shell=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def _service_name(container_name: str) -> str:
    clean = container_name.lstrip("/")
    for service in sorted(COMPOSE_SERVICES, key=len, reverse=True):
        if re.search(rf"(?:^|[-_]){re.escape(service)}(?:[-_]\d+)?$", clean):
            return service
    if "p6e-probe" in clean:
        return "financial-probe"
    return "other"


def _docker_stats(capacity: Any) -> list[dict[str, Any]] | None:
    text = _run_readonly(["docker", "stats", "--no-stream", "--format", "{{json .}}"])
    if text is None:
        return None
    result: list[dict[str, Any]] = []
    try:
        for line in text.splitlines():
            item = json.loads(line)
            used, _limit = capacity._size_pair(str(item["MemUsage"]))
            result.append({"service": _service_name(str(item.get("Name", ""))),
                           "cpu_percent": float(str(item["CPUPerc"]).rstrip("%")),
                           "memory_used_bytes": used, "pids": int(item["PIDs"])})
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, capacity.CapacityError):
        return None
    return result


def _docker_storage() -> dict[str, dict[str, int]] | None:
    text = _run_readonly(["docker", "system", "df", "--format", "{{json .}}"])
    if text is None:
        return None
    try:
        return _load_capacity_module().parse_docker_df(text.splitlines())
    except CapacityRehearsalError:
        return None
    except ValueError:
        return None


def _release_storage_ok(p6e: Any, root: Path) -> tuple[dict[str, Any], bool]:
    manifests: dict[str, Any] = {}
    try:
        for label in ("release-a", "release-b"):
            manifest = p6e.load_verified_manifest(root / label / "manifest.json")
            manifests[label] = {"release": manifest["release"], "git_commit": manifest["git_commit"],
                                "image_count": len(manifest["images"]),
                                "all_images_digest_pinned": all("@sha256:" in image["immutable_ref"] for image in manifest["images"])}
        ok = (manifests["release-a"]["release"] != manifests["release-b"]["release"]
              and all(row["image_count"] == 4 and row["all_images_digest_pinned"] for row in manifests.values()))
        return manifests, ok
    except Exception:
        return {}, False


def _inside(bundle_root: Path, only_scenario: str | None = None) -> dict[str, Any]:
    if not sys.platform.startswith("linux"):
        raise CapacityRehearsalError("inside rehearsal requires disposable Linux")
    p6e = _load_p6e()
    capacity = _load_capacity_module()
    release_metadata, releases_valid = _release_storage_ok(p6e, bundle_root)
    if not releases_valid:
        raise CapacityRehearsalError("verified digest-pinned P6-D A/B bundle contract is invalid")

    state: dict[str, Any] = {"phase": "baseline_idle", "scenario": "setup"}
    lock = threading.Lock()
    samples: list[dict[str, Any]] = []
    stop = threading.Event()
    cpu_previous = _cpu_total_idle(Path("/proc/stat").read_text(encoding="ascii"))
    cgroup_previous = _cgroup_v2()
    cgroup_previous_at = time.monotonic()
    vmstat_previous = capacity.parse_swap_vmstat(Path("/proc/vmstat").read_text(encoding="ascii"))
    docker_info = _run_readonly(["docker", "info", "--format", "{{.DockerRootDir}}\t{{.NCPU}}\t{{.MemTotal}}"], timeout=15)
    if not docker_info:
        raise CapacityRehearsalError("rootless Docker telemetry unavailable in disposable Linux target")
    docker_root_text, _engine_cpus, _engine_memory = docker_info.strip().split("\t", 2)
    docker_root = Path(docker_root_text)

    def set_state(phase: str, scenario: str) -> None:
        with lock:
            state["phase"] = phase
            state["scenario"] = scenario
            state["timestamp_utc"] = datetime.now(timezone.utc).isoformat()

    def current_state() -> dict[str, str]:
        with lock:
            return {key: str(state.get(key, "unknown")) for key in ("phase", "scenario")}

    def query_phase(phase: str, scenario: str) -> str:
        if phase != "migrations_startup_readiness":
            return phase
        project = state.get("compose_project")
        if not project:
            return phase
        text = _run_readonly(["docker", "ps", "--all", "--filter", f"label=com.docker.compose.project={project}",
                              "--format", '{{.Label "com.docker.compose.service"}}\t{{.State}}'])
        if text is None:
            return phase
        rows = [line.split("\t", 1) for line in text.splitlines() if line.strip()]
        if any(len(row) == 2 and row[0] in MIGRATION_SERVICES and row[1] == "running" for row in rows):
            return "migrations"
        if rows:
            return "service_startup_readiness"
        return phase

    def monitor() -> None:
        nonlocal cpu_previous, cgroup_previous, cgroup_previous_at, vmstat_previous
        last_storage = 0.0
        latest_storage: dict[str, dict[str, int]] | None = None
        while not stop.is_set():
            started = time.monotonic()
            current = current_state()
            cpu_text = _run_readonly(["cat", "/proc/stat"])
            cpu_now = _cpu_total_idle(cpu_text) if cpu_text else None
            cpu_ratio = None
            if cpu_previous and cpu_now:
                total_delta = cpu_now[0] - cpu_previous[0]
                idle_delta = cpu_now[1] - cpu_previous[1]
                if total_delta > 0 and 0 <= idle_delta <= total_delta:
                    cpu_ratio = (total_delta - idle_delta) / total_delta
            if cpu_now:
                cpu_previous = cpu_now
            memory = _meminfo(capacity)
            try:
                load1, load5, load15 = os.getloadavg()
                logical_cpus = os.cpu_count() or 0
            except OSError:
                load1 = load5 = load15 = 0.0
                logical_cpus = 0
            cgroup_now = _cgroup_v2()
            cpu_limit = cgroup_now.get("cpu_quota_cores")
            sample_at = time.monotonic()
            cpu_quota_ratio = None
            if (cgroup_previous.get("cpu_usage_usec") is not None and cgroup_now.get("cpu_usage_usec") is not None
                    and cpu_limit and cpu_limit > 0):
                delta = cgroup_now["cpu_usage_usec"] - cgroup_previous["cpu_usage_usec"]
                elapsed_usec = max((sample_at - cgroup_previous_at) * 1_000_000, 1)
                cpu_quota_ratio = min(max(delta, 0) / (elapsed_usec * cpu_limit), 1.0)
            cgroup_previous = cgroup_now
            cgroup_previous_at = sample_at
            vmstat_now = None
            try:
                vmstat_now = capacity.parse_swap_vmstat(Path("/proc/vmstat").read_text(encoding="ascii"))
            except (OSError, ValueError, capacity.CapacityError):
                pass
            swap_delta = None
            if vmstat_now and vmstat_previous:
                swap_delta = {key: max(vmstat_now[key] - vmstat_previous[key], 0) for key in vmstat_now}
            if vmstat_now:
                vmstat_previous = vmstat_now
            filesystems = {"root": _fs_sample(Path("/")), "docker_root": _fs_sample(docker_root)}
            stats = _docker_stats(capacity)
            now = time.monotonic()
            if now - last_storage >= 10:
                latest_storage = _docker_storage()
                last_storage = now
            effective_phase = query_phase(current["phase"], current["scenario"])
            sample = {
                "timestamp_monotonic": now,
                "phase": effective_phase,
                "scenario": current["scenario"],
                "cpu_host_busy_ratio": cpu_ratio,
                "cpu_quota_busy_ratio": cpu_quota_ratio,
                "load_per_core": {"1m": load1 / logical_cpus if logical_cpus else None,
                                   "5m": load5 / logical_cpus if logical_cpus else None,
                                   "15m": load15 / logical_cpus if logical_cpus else None},
                "logical_cpus": logical_cpus,
                "memory": memory,
                "swap_io_pages_delta": swap_delta,
                "cgroup": cgroup_now,
                "filesystems": filesystems,
                "containers": stats,
                "docker_storage": latest_storage,
            }
            samples.append(sample)
            stop.wait(max(SAMPLE_INTERVAL_SECONDS - (time.monotonic() - started), 0.05))

    monitor_thread = threading.Thread(target=monitor, name="p6f5c-readonly-sampler", daemon=True)
    monitor_thread.start()
    p6e_original_deploy = p6e.deploy
    p6e_original_compose = p6e.compose
    p6e_original_verify = p6e.verify_rollout
    p6e_original_smoke = p6e.smoke
    current_release = {"value": "unknown"}
    current_scenario = {"value": "unknown"}
    failed_b = {"value": False}
    compose_failure: dict[str, str] = {}

    def instrumented_compose(project: str, environment: dict[str, str], override: Path, *arguments: str) -> Any:
        with lock:
            state["compose_project"] = project
        if arguments[:3] == ("up", "-d", "--wait"):
            phase = "rollback_A" if failed_b["value"] and current_release["value"] == "A" else "migrations_startup_readiness"
            set_state(phase, current_scenario["value"])
        result = p6e_original_compose(project, environment, override, *arguments)
        if result.returncode:
            message = (result.stderr or result.stdout or "").lower()
            if "unhealthy" in message:
                detail = "health_unhealthy"
            elif "dependency" in message:
                detail = "dependency_failure"
            elif "timed out" in message or "timeout" in message:
                detail = "timeout"
            elif "no such" in message or "not found" in message:
                detail = "missing_resource"
            elif "pull access denied" in message or "failed to pull" in message:
                detail = "registry_pull"
            else:
                detail = "nonzero_compose_exit"
            compose_failure.clear()
            compose_failure.update({"phase": current_state()["phase"], "detail": detail,
                                    "operation": "up_wait" if arguments[:3] == ("up", "-d", "--wait") else "compose"})
            if arguments[:3] == ("up", "-d", "--wait"):
                try:
                    records = p6e.compose_records(project, environment, override)
                    unhealthy = sorted({str(row.get("Service")) for row in records
                                        if str(row.get("Health", "")).lower() == "unhealthy"
                                        and str(row.get("Service", "")) in COMPOSE_SERVICES})
                    if unhealthy:
                        compose_failure["unhealthy_services"] = ",".join(unhealthy)
                except Exception:
                    pass
        return result

    def instrumented_verify(project: str, environment: dict[str, str], override: Path, manifest: dict[str, Any]) -> None:
        set_state("readiness_validation", current_scenario["value"])
        p6e_original_verify(project, environment, override, manifest)
        time.sleep(READINESS_HOLD_SECONDS)
        set_state("steady_state", current_scenario["value"])
        time.sleep(STABLE_HOLD_SECONDS)

    def instrumented_smoke(command: str | None, environment: dict[str, str], *, release: str, health_only: bool) -> None:
        phase = "smoke_failure_injection" if current_scenario["value"] == "smoke" and current_release["value"] == "B" else "financial_smoke"
        set_state(phase, current_scenario["value"])
        if phase == "smoke_failure_injection":
            # Keep healthy B up briefly so the sampler records the state immediately before exit 97.
            time.sleep(5)
        p6e_original_smoke(command, environment, release=release, health_only=health_only)

    def instrumented_deploy(project: str, environment: dict[str, str], manifest: dict[str, Any], override: Path,
                            *, smoke_command: str | None, health_only: bool) -> None:
        release = "A" if manifest["release"] == release_metadata["release-a"]["release"] else "B"
        current_release["value"] = release
        if release == "A" and failed_b["value"]:
            set_state("rollback_A", current_scenario["value"])
        else:
            set_state(f"rollout_{release}", current_scenario["value"])
        try:
            p6e_original_deploy(project, environment, manifest, override, smoke_command=smoke_command, health_only=health_only)
        except Exception:
            if release == "B":
                failed_b["value"] = True
            raise

    p6e.compose = instrumented_compose
    p6e.verify_rollout = instrumented_verify
    p6e.smoke = instrumented_smoke
    p6e.deploy = instrumented_deploy
    scenario_results: list[dict[str, str]] = []
    scenario_failure: dict[str, str] | None = None
    try:
        set_state("baseline_idle", "baseline")
        time.sleep(IDLE_SECONDS)
        scenarios = (("none", "healthy_A_to_B"), ("readiness", "readiness_rollback"), ("smoke", "smoke_rollback"))
        if only_scenario:
            scenarios = tuple(item for item in scenarios if item[1] == only_scenario)
        for mode, scenario in scenarios:
            current_scenario["value"] = scenario
            failed_b["value"] = False
            set_state("scenario_start", scenario)
            try:
                output = io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    result = p6e.run_scenario(_p6e_args(p6e, bundle_root, mode))
                if result != 0:
                    raise CapacityRehearsalError("P6-E scenario returned non-zero")
                if mode != "none":
                    failed_b["value"] = True
                scenario_results.append({"scenario": scenario, "result": "PASS"})
            except Exception as exc:
                # Suppress P6-E output/exception details so no credential-bearing diagnostic is exposed.
                category = _failure_category(str(exc))
                scenario_results.append({"scenario": scenario, "result": "FAIL", "failure_type": type(exc).__name__,
                                         "failure_category": category, "failure_phase": current_state()["phase"],
                                         **({"compose_failure": dict(compose_failure)} if compose_failure else {})})
                scenario_failure = {"scenario": scenario, "category": category, "phase": current_state()["phase"],
                                    **({"compose_operation": compose_failure.get("operation", "unknown"),
                                       "compose_detail": compose_failure.get("detail", "unknown"),
                                       **({"unhealthy_services": compose_failure["unhealthy_services"]}
                                          if compose_failure.get("unhealthy_services") else {})}
                                       if compose_failure else {})}
                break
            set_state("retained_A_B_images", scenario)
            time.sleep(IDLE_SECONDS)
        set_state("final_retained_A_B", "retained_images")
        time.sleep(IDLE_SECONDS)
    finally:
        stop.set()
        monitor_thread.join(timeout=15)
        p6e.deploy = p6e_original_deploy
        p6e.compose = p6e_original_compose
        p6e.verify_rollout = p6e_original_verify
        p6e.smoke = p6e_original_smoke

    phase_rows: dict[str, list[dict[str, Any]]] = {}
    for sample in samples:
        phase_rows.setdefault(sample["phase"], []).append(sample)
    phase_summary: dict[str, Any] = {}
    for phase, rows in sorted(phase_rows.items()):
        valid_cgroup_mem = [row["cgroup"]["memory_current_bytes"] for row in rows if row["cgroup"]["memory_current_bytes"] is not None]
        valid_cpu = [row["cpu_quota_busy_ratio"] for row in rows if row["cpu_quota_busy_ratio"] is not None]
        valid_pids = [row["cgroup"]["pids_current"] for row in rows if row["cgroup"]["pids_current"] is not None]
        service_rows: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            for container in row["containers"] or []:
                service_rows.setdefault(container["service"], []).append(container)
        phase_summary[phase] = {
            "sample_count": len(rows),
            "cpu_quota_busy_ratio_p95": _percentile(valid_cpu, .95),
            "cpu_quota_busy_ratio_max": max(valid_cpu) if valid_cpu else None,
            "cgroup_memory_current_bytes_max": max(valid_cgroup_mem) if valid_cgroup_mem else None,
            "cgroup_pids_current_max": max(valid_pids) if valid_pids else None,
            "host_memory_available_bytes_min": min((row["memory"]["available_bytes"] for row in rows if row["memory"]) , default=None),
            "docker_root_available_bytes_min": min((row["filesystems"]["docker_root"]["available_bytes"] for row in rows if row["filesystems"]["docker_root"]), default=None),
            "docker_root_available_inodes_min": min((row["filesystems"]["docker_root"]["available_inodes"] for row in rows if row["filesystems"]["docker_root"]), default=None),
            "docker_storage_max_bytes_by_type": _storage_max(rows),
            "containers": {service: {
                "cpu_percent_max": max(item["cpu_percent"] for item in values),
                "memory_used_bytes_max": max(item["memory_used_bytes"] for item in values),
                "pids_max": max(item["pids"] for item in values),
            } for service, values in sorted(service_rows.items())},
        }

    idle_samples = phase_rows.get("baseline_idle", [])
    profile_samples = [sample for sample in samples if sample["phase"] != "baseline_idle"]
    idle_mem = [row["cgroup"]["memory_current_bytes"] for row in idle_samples if row["cgroup"]["memory_current_bytes"] is not None]
    profile_mem = [row["cgroup"]["memory_current_bytes"] for row in profile_samples if row["cgroup"]["memory_current_bytes"] is not None]
    profile_pids = [row["cgroup"]["pids_current"] for row in profile_samples if row["cgroup"]["pids_current"] is not None]
    quota_values = [row["cpu_quota_busy_ratio"] for row in profile_samples if row["cpu_quota_busy_ratio"] is not None]
    storage_values = [_storage_total(row.get("docker_storage")) for row in profile_samples]
    vps_baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    baseline_fs = vps_baseline["host"]["filesystems"]["docker_root"]
    vps_cpu_cores = vps_baseline["host"]["cpu_logical_cores"]
    stage_cpu_cores = _cgroup_v2().get("cpu_quota_cores")
    stage_memory_max = _cgroup_v2().get("memory_max_bytes")
    incremental_memory = max(max(profile_mem, default=0) - min(idle_mem, default=0), 0) if profile_mem and idle_mem else None
    staged_storage_peak = max((value for value in storage_values if value is not None), default=None)
    inode_samples = [row["filesystems"]["docker_root"] for row in samples if row["filesystems"]["docker_root"]]
    staging_inode_delta = None
    if idle_samples and inode_samples:
        idle_inode_values = [row["filesystems"]["docker_root"]["available_inodes"] for row in idle_samples if row["filesystems"]["docker_root"]]
        all_inode_values = [row["available_inodes"] for row in inode_samples]
        if idle_inode_values and all_inode_values:
            staging_inode_delta = max(min(idle_inode_values) - min(all_inode_values), 0)

    immutable_images_present = True
    for label in ("release-a", "release-b"):
        manifest = p6e.load_verified_manifest(bundle_root / label / "manifest.json")
        for image in manifest["images"]:
            if not _run_readonly(["docker", "image", "inspect", str(image["immutable_ref"]), "--format", "{{.Id}}"], timeout=15):
                immutable_images_present = False
    container_stats_reliable = _container_stats_consistent(samples)
    if not container_stats_reliable:
        for summary in phase_summary.values():
            summary["containers"] = {}

    stage_names = set(phase_summary)
    required_phases_covered = PHASES_REQUIRED.issubset(stage_names)
    scenarios_passed = len(scenario_results) == 3 and all(row["result"] == "PASS" for row in scenario_results)
    metrics_complete = bool(
        len(idle_samples) >= 3 and required_phases_covered and scenarios_passed
        and stage_cpu_cores is not None and abs(stage_cpu_cores - TARGET_CPU_LIMIT) < 0.05
        and stage_memory_max is not None and stage_memory_max <= TARGET_MEMORY_LIMIT_BYTES
        and incremental_memory is not None and staged_storage_peak is not None
        and staging_inode_delta is not None and profile_pids
        and all(phase_summary.get(phase, {}).get("containers") for phase in ("migrations", "service_startup_readiness", "financial_smoke", "rollback_A"))
        and immutable_images_present and container_stats_reliable
    )
    projected: dict[str, Any] = {
        "cpu_busy_p95_ratio": (vps_baseline["host"].get("cpu_busy_ratio_5s", {}).get("p95", 0)
                                + _percentile(quota_values, .95)) if quota_values else None,
        "load5_per_core_p95": None,
        "load1_per_core_peak": None,
        "memory_available_after_peak_bytes": (vps_baseline["host"]["memory_available_bytes_min"] - incremental_memory) if incremental_memory is not None else None,
        "swap_io_pages_during_peak": sum(row["swap_io_pages_delta"][key] for row in samples if row["swap_io_pages_delta"] for key in row["swap_io_pages_delta"]),
        "additional_peak_processes": max(max(profile_pids, default=0) - min((row["cgroup"]["pids_current"] for row in idle_samples if row["cgroup"]["pids_current"] is not None), default=0), 0),
        "disk_available_after_peak_bytes": {"docker_root": baseline_fs["available_bytes_min"] - staged_storage_peak} if staged_storage_peak is not None else {},
        "inodes_available_after_peak": {"docker_root": baseline_fs["available_inodes_min"] - staging_inode_delta} if staging_inode_delta is not None else {},
        "peak_includes_migrations": "migrations" in stage_names,
        "peak_includes_release_pull_and_retained_A": "retained_A_B_images" in stage_names and scenarios_passed,
        "peak_includes_financial_smoke": "financial_smoke" in stage_names and scenarios_passed,
        "release_images_are_digest_pinned": all(row["image_count"] == 4 and row["all_images_digest_pinned"] for row in release_metadata.values()),
        "candidate_build_is_off_host": True,
    }
    # Load average cannot be faithfully translated from a 12-vCPU disposable VM to the 4-vCPU VPS;
    # omit rather than fabricate a passing number.
    evidence = {
        "schema": "bankcore-p6f5c-evidence-v1",
        "observation_minutes": vps_baseline["observation_span_minutes"],
        "sample_count": vps_baseline["successful_samples"],
        "representative_peak_period": vps_baseline["representative_peak_period"],
        "staging_profile_complete": metrics_complete,
        "host": {
            "cpu_cores": vps_cpu_cores,
            "memory_total_bytes": vps_baseline["host"]["memory_total_bytes"],
            "pid_max": vps_baseline["host"]["pid_max"],
            "process_count": vps_baseline["host"]["process_count_max"],
            "filesystems": {"docker_root": {"total_bytes": baseline_fs["total_bytes"], "total_inodes": baseline_fs["total_inodes"]}},
        },
        "projection": projected,
    }
    policy = capacity.evaluate_capacity(evidence)
    return {
        "schema": "bankcore-p6f5c-rehearsal-v1",
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "scenario_results": scenario_results,
        "scenario_failure": scenario_failure,
        "release_metadata": release_metadata,
        "staging_host": {"docker_cpu_quota_cores": stage_cpu_cores, "docker_memory_limit_bytes": stage_memory_max,
                          "vps_cpu_cores": vps_cpu_cores, "vps_memory_total_bytes": vps_baseline["host"]["memory_total_bytes"],
                          "hardware_equivalent": False},
        "phase_metrics": phase_summary,
        "all_eight_release_images_retained_by_digest": immutable_images_present,
        "combined_projection": projected,
        "classification": policy["status"] if metrics_complete else ("FAIL" if policy["status"] == "FAIL" else "CONDITIONAL"),
        "policy_reasons": policy["reasons"],
        "policy_failures": policy["failures"],
        "profile_complete": metrics_complete,
        "per_container_stats_reliable": container_stats_reliable,
        "limitations": [
            "Disposable runner is a 4-vCPU, 15-GiB cgroup inside a 12-vCPU Docker host; CPU/RAM are constrained, but host kernel, storage layer, CPU model and concurrent noise are not identical to the VPS.",
            "The VPS one-hour sample window was not proven representative of peak production traffic.",
            "VPS Docker storage was aggregated by type; this rehearsal does not establish per-volume quota behavior on the VPS.",
            "Linux load averages cannot be accurately rescaled between the disposable host and VPS; policy remains CONDITIONAL when required load evidence is not comparable.",
            "Read-only Linux staging, P6-E synthetic financial smoke only; no live VPS data or production database was used.",
        ],
        "privacy": {"container_ids_or_names_emitted": False, "image_names_or_tags_emitted": False,
                    "environment_values_read": False, "raw_samples_retained": False},
    }


def _percentile(values: list[float], quantile: float) -> float | None:
    ordered = sorted(value for value in values if math.isfinite(value))
    if not ordered:
        return None
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)]


def _storage_total(value: dict[str, dict[str, int]] | None) -> int | None:
    if not value:
        return None
    return sum(int(entry["size_bytes"]) for entry in value.values())


def _storage_max(rows: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        for label, entry in (row.get("docker_storage") or {}).items():
            result[label] = max(result.get(label, 0), int(entry["size_bytes"]))
    return result


def _container_stats_consistent(samples: list[dict[str, Any]]) -> bool:
    """Reject nested-Docker per-container readings that exceed the measured target cgroup."""
    for row in samples:
        containers = row.get("containers") or []
        cgroup = row.get("cgroup") or {}
        if len(containers) < 2:
            continue
        memory = cgroup.get("memory_current_bytes")
        pids = cgroup.get("pids_current")
        quota = cgroup.get("cpu_quota_cores")
        summed_memory = sum(int(item["memory_used_bytes"]) for item in containers)
        summed_pids = sum(int(item["pids"]) for item in containers)
        summed_cpu_percent = sum(float(item["cpu_percent"]) for item in containers)
        if memory and summed_memory > memory * 1.25:
            return False
        if pids and summed_pids > pids * 1.25:
            return False
        if quota and summed_cpu_percent > quota * 100 * 1.25:
            return False
    return True


def _failure_category(message: str) -> str:
    """Map runner errors to a fixed safe category; never echo subprocess output."""
    normalized = message.lower()
    categories = (
        (("ordered migration",), "migration_contract"),
        (("runtime image identity mismatch", "not digest pinned"), "image_digest_verification"),
        (("not ready after rollout", "healthcheck"), "readiness"),
        (("smoke test failed", "financial smoke"), "financial_smoke"),
        (("snapshot", "financial state"), "financial_snapshot"),
        (("pull access denied", "failed to resolve reference", "failed to pull"), "registry_pull"),
        (("compose step failed", "command failed"), "compose_or_command"),
    )
    for needles, category in categories:
        if any(needle in normalized for needle in needles):
            return category
    return "unclassified_runtime_failure"


def _host_mode(bundle_root: Path, only_scenario: str | None = None) -> dict[str, Any]:
    if os.name == "nt":
        # Docker Desktop's Linux Engine is the disposable Linux host; its limits are applied to the target.
        pass
    p6e = _load_p6e()
    root = bundle_root.resolve(strict=True)
    if root == ROOT or ROOT in root.parents:
        raise CapacityRehearsalError("release bundles must stay outside the repository")
    release_metadata, valid = _release_storage_ok(p6e, root)
    if not valid:
        raise CapacityRehearsalError("verified P6-D release A/B bundles and SBOMs are required")
    engine = subprocess.run(["docker", "info", "--format", "{{.OSType}} {{.NCPU}} {{.MemTotal}}"],
                            cwd=ROOT, text=True, capture_output=True, check=False, shell=False)
    if engine.returncode or not engine.stdout.strip().startswith("linux "):
        raise CapacityRehearsalError("Linux Docker Engine is required for disposable capacity rehearsal")
    image = f"bankcore-p6f5c-target:{uuid.uuid4().hex[:12]}"
    container = f"bankcore-p6f5c-{uuid.uuid4().hex[:10]}"
    try:
        build = subprocess.run(["docker", "build", "--file", str(TARGET_DOCKERFILE), "--tag", image, "."],
                               cwd=ROOT, text=True, capture_output=True, check=False, shell=False, timeout=900)
        if build.returncode:
            raise CapacityRehearsalError("could not build disposable Linux target")
        command = ["docker", "run", "--detach", "--privileged", "--name", container,
                   "--cpus", str(TARGET_CPU_LIMIT), "--memory", "15g",
                   "--env", "DOCKER_TLS_CERTDIR=",
                   "--volume", f"{ROOT}:/workspace:ro", "--volume", f"{ROOT / '.git'}:/workspace/.git:ro",
                   "--volume", f"{root}:/bundles:ro", image]
        started = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False, shell=False, timeout=60)
        if started.returncode:
            raise CapacityRehearsalError("could not start disposable Linux target")
        staging = _load_module("p6f_staging", ROOT / "scripts" / "p6f-staging.py")
        try:
            staging.wait_for_rootless_docker(container)
            staging.docker_exec(container, ["git", "config", "--file", "/tmp/p6e-gitconfig", "--add", "safe.directory", "/workspace"])
            scenario_args = ["--scenario", only_scenario] if only_scenario else []
            result = staging.docker_exec(container,
                ["env", "GIT_CONFIG_GLOBAL=/tmp/p6e-gitconfig", "DOCKER_HOST=unix:///run/user/1000/docker.sock",
                 "XDG_RUNTIME_DIR=/run/user/1000", "python3", "/workspace/scripts/p6f5c-rehearsal.py",
                 "--inside", "--bundles", "/bundles", *scenario_args],
                user="bankcore", check=False, timeout=5400)
            if result.returncode:
                safe_status = next((line.strip() for line in (result.stderr or "").splitlines()
                                    if line.startswith("P6-F5C STOP:")), "P6-F5C STOP: inner rehearsal failed")
                raise CapacityRehearsalError(safe_status[:240])
        except Exception as exc:
            if isinstance(exc, CapacityRehearsalError):
                raise
            raise CapacityRehearsalError(f"disposable capacity runner failed ({type(exc).__name__}); details withheld") from None
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise CapacityRehearsalError("disposable runner did not produce a valid sanitized summary") from exc
        payload["release_metadata"] = release_metadata
        payload["local_docker_engine"] = {"operating_system": "linux", "logical_cpus": int(engine.stdout.split()[1]),
                                          "memory_bytes": int(engine.stdout.split()[2])}
        return payload
    finally:
        subprocess.run(["docker", "rm", "--force", container], cwd=ROOT, capture_output=True, check=False, shell=False, timeout=60)
        subprocess.run(["docker", "image", "rm", "--force", image], cwd=ROOT, capture_output=True, check=False, shell=False, timeout=120)


def main() -> int:
    parser = argparse.ArgumentParser(description="P6-F5C-3 disposable P6-D/P6-E A+B capacity rehearsal")
    parser.add_argument("--bundles", type=Path, required=True, help="external directory containing verified release-a/ and release-b/ bundles")
    parser.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--scenario", choices=("healthy_A_to_B", "readiness_rollback", "smoke_rollback"),
                        help="run one isolated scenario for diagnostics; full profile remains incomplete")
    args = parser.parse_args()
    bundle_root = args.bundles.resolve(strict=True)
    result = _inside(bundle_root, args.scenario) if args.inside else _host_mode(bundle_root, args.scenario)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CapacityRehearsalError as error:
        print(f"P6-F5C STOP: {error}", file=sys.stderr)
        raise SystemExit(2)
