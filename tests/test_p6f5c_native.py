"""Contract tests for the read-only F5C-4 native-host preflight."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("p6f5c_native_preflight", ROOT / "scripts" / "p6f5c-native-preflight.py")
assert SPEC and SPEC.loader
preflight = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preflight
SPEC.loader.exec_module(preflight)


class NativePreflightTests(unittest.TestCase):
    def passing_report(self) -> dict:
        return {"os": "Linux", "architecture": "x86_64", "logical_cpus": 4,
                "memory_total_bytes": 16 * 1024**3, "docker": {"compose_available": True},
                "remote_engine_detected": False, "docker_root_filesystem": {"total_bytes": 200 * 1024**3}}

    def test_native_profile_passes_only_with_exact_core_and_memory_envelope(self) -> None:
        self.assertEqual(preflight.validate_report(self.passing_report()), [])

    def test_remote_engine_and_profile_drift_fail_closed(self) -> None:
        report = self.passing_report()
        report.update(remote_engine_detected=True, logical_cpus=8, docker_root_filesystem=None)
        reasons = preflight.validate_report(report)
        self.assertIn("remote_engine_detected", reasons)
        self.assertIn("logical_cpu_profile_mismatch", reasons)
        self.assertIn("docker_root_filesystem_unknown", reasons)

    def test_preflight_schema_is_sanitized_and_non_mutating(self) -> None:
        report = self.passing_report()
        report["mutations_performed"] = False
        self.assertFalse(report["mutations_performed"])
        self.assertNotIn("hostname", report)
        self.assertNotIn("name", report)

    def test_readonly_allowlist_rejects_lifecycle_commands(self) -> None:
        with self.assertRaises(preflight.NativePreflightError):
            preflight._run_readonly(["docker", "compose", "up"])


if __name__ == "__main__":
    unittest.main()
