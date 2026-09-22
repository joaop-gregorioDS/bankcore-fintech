"""Contract tests for native F5C-4 aggregate telemetry parsing."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("p6f5c_native_telemetry", ROOT / "scripts" / "p6f5c-native-telemetry.py")
assert SPEC and SPEC.loader
telemetry = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = telemetry
SPEC.loader.exec_module(telemetry)


class NativeTelemetryTests(unittest.TestCase):
    def test_cpu_ratio_is_bounded_and_uses_counter_delta(self) -> None:
        before = telemetry.parse_cpu("cpu 100 0 20 800 0 0 0 0\n")
        after = telemetry.parse_cpu("cpu 150 0 30 820 0 0 0 0\n")
        self.assertAlmostEqual(telemetry.cpu_busy_ratio(before, after), 0.75)
        self.assertLessEqual(telemetry.cpu_busy_ratio(before, after), 1.0)

    def test_memory_and_swap_parsers_are_aggregate_only(self) -> None:
        parsed = telemetry.parse_meminfo("MemTotal: 16384 kB\nMemAvailable: 8192 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n")
        self.assertEqual(parsed["MemAvailable"], 8192 * 1024)
        self.assertEqual(telemetry.parse_vmstat("pswpin 2\npswpout 3\n"), {"pswpin": 2, "pswpout": 3})

    def test_docker_lifecycle_is_outside_allowlist(self) -> None:
        with self.assertRaises(telemetry.TelemetryError):
            telemetry._readonly(["docker", "compose", "up"])


if __name__ == "__main__":
    unittest.main()
