"""Synthetic contract tests for the read-only P6-F5C capacity gate."""

from __future__ import annotations

import importlib.util
import math
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "scripts" / "p6f5c-capacity.py"
SPEC = importlib.util.spec_from_file_location("p6f5c_capacity", SCRIPT)
assert SPEC and SPEC.loader
capacity = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = capacity
SPEC.loader.exec_module(capacity)


class CapacityParserTests(unittest.TestCase):
    def test_meminfo_requires_available_and_consistent_values(self) -> None:
        parsed = capacity.parse_meminfo(
            "MemTotal: 16384 kB\nMemAvailable: 8192 kB\n"
            "SwapTotal: 1024 kB\nSwapFree: 768 kB\n"
        )
        self.assertEqual(parsed["MemTotal"], 16 * 1024 * 1024)
        self.assertEqual(parsed["SwapFree"], 768 * 1024)

        with self.assertRaises(capacity.CapacityError):
            capacity.parse_meminfo("MemTotal: 10 kB\nMemAvailable: 11 kB\n")

    def test_cpu_busy_ratio_uses_counter_delta(self) -> None:
        before = capacity.parse_cpu_stat("cpu 100 0 20 800 0 0 0 0\n")
        after = capacity.parse_cpu_stat("cpu 150 0 30 820 0 0 0 0\n")
        self.assertAlmostEqual(capacity.cpu_busy_ratio(before, after), 0.75)

    def test_size_parser_supports_binary_and_decimal_units(self) -> None:
        self.assertEqual(capacity._parse_size("2 GiB"), 2 * 1024**3)
        self.assertEqual(capacity._parse_size("1.5GB"), 1_500_000_000)

    def test_docker_stats_are_anonymized_and_parsed(self) -> None:
        rows = capacity.parse_docker_stats(
            ['{"ID":"secret-id","Name":"secret-name","CPUPerc":"12.5%",'
             '"MemUsage":"512MiB / 2GiB","PIDs":"18"}']
        )
        self.assertEqual(rows, [{
            "container": "container_001",
            "cpu_percent": 12.5,
            "memory_used_bytes": 512 * 1024**2,
            "memory_limit_bytes": 2 * 1024**3,
            "pids": 18,
        }])
        self.assertNotIn("secret-id", repr(rows))
        self.assertNotIn("secret-name", repr(rows))

    def test_docker_df_requires_parseable_storage_summary(self) -> None:
        parsed = capacity.parse_docker_df(
            ['{"Type":"Images","TotalCount":"4","Size":"1.25GB"}']
        )
        self.assertEqual(parsed["Images"]["count"], 4)
        self.assertEqual(parsed["Images"]["size_bytes"], 1_250_000_000)
        with self.assertRaises(capacity.CapacityError):
            capacity.parse_docker_df([])


class CapacityPolicyTests(unittest.TestCase):
    def passing_evidence(self) -> dict:
        return {
            "schema": "bankcore-p6f5c-evidence-v1",
            "observation_minutes": 60,
            "sample_count": 12,
            "representative_peak_period": True,
            "staging_profile_complete": True,
            "host": {
                "cpu_cores": 8,
                "memory_total_bytes": 16 * 1024**3,
                "pid_max": 131072,
                "process_count": 1200,
                "filesystems": {
                    "docker_root": {
                        "total_bytes": 200 * 1024**3,
                        "total_inodes": 1_000_000,
                    }
                },
            },
            "projection": {
                "cpu_busy_p95_ratio": 0.55,
                "load5_per_core_p95": 0.60,
                "load1_per_core_peak": 0.80,
                "memory_available_after_peak_bytes": 5 * 1024**3,
                "swap_io_pages_during_peak": 0,
                "additional_peak_processes": 2000,
                "disk_available_after_peak_bytes": {"docker_root": 60 * 1024**3},
                "inodes_available_after_peak": {"docker_root": 600_000},
                "peak_includes_migrations": True,
                "peak_includes_release_pull_and_retained_A": True,
                "peak_includes_financial_smoke": True,
                "release_images_are_digest_pinned": True,
                "candidate_build_is_off_host": True,
            },
        }

    def test_complete_headroom_evidence_passes(self) -> None:
        self.assertEqual(capacity.evaluate_capacity(self.passing_evidence())["status"], "PASS")

    def test_short_observation_or_missing_profile_is_conditional(self) -> None:
        evidence = self.passing_evidence()
        evidence["observation_minutes"] = 20
        evidence["staging_profile_complete"] = False
        result = capacity.evaluate_capacity(evidence)
        self.assertEqual(result["status"], "CONDITIONAL")
        self.assertIn("insufficient:observation_window_under_60_minutes", result["reasons"])

    def test_missing_schema_or_filesystem_coverage_cannot_pass(self) -> None:
        evidence = self.passing_evidence()
        evidence["schema"] = "unexpected"
        evidence["projection"]["disk_available_after_peak_bytes"] = {}
        result = capacity.evaluate_capacity(evidence)
        self.assertEqual(result["status"], "CONDITIONAL")
        self.assertIn("unknown_or_unproven:evidence_schema", result["reasons"])
        self.assertIn("unknown:filesystem_projection_coverage", result["reasons"])

    def test_exhausted_memory_disk_or_swap_activity_fails(self) -> None:
        evidence = self.passing_evidence()
        evidence["projection"]["memory_available_after_peak_bytes"] = 512 * 1024**2
        evidence["projection"]["swap_io_pages_during_peak"] = 3
        evidence["projection"]["disk_available_after_peak_bytes"]["docker_root"] = 5 * 1024**3
        result = capacity.evaluate_capacity(evidence)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("capacity:swap_io_during_peak", result["failures"])

    def test_non_finite_or_out_of_range_numeric_evidence_fails(self) -> None:
        evidence = self.passing_evidence()
        evidence["projection"]["cpu_busy_p95_ratio"] = math.nan
        result = capacity.evaluate_capacity(evidence)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("invalid:projected_cpu_busy_p95", result["failures"])

    def test_docker_allowlist_has_no_lifecycle_or_shell_commands(self) -> None:
        flattened = [part.lower() for command in capacity.DOCKER_COMMANDS for part in command]
        self.assertFalse({"exec", "run", "start", "stop", "restart", "rm", "up", "down"} & set(flattened))
        self.assertTrue(all(command[0] == "docker" for command in capacity.DOCKER_COMMANDS))


if __name__ == "__main__":
    unittest.main()
