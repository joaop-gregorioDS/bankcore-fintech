"""Local contract tests for the P6-F5C disposable rehearsal runner."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "p6f5c-rehearsal.py"
SPEC = importlib.util.spec_from_file_location("p6f5c_rehearsal", SCRIPT)
assert SPEC and SPEC.loader
rehearsal = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rehearsal
SPEC.loader.exec_module(rehearsal)


class RehearsalSamplerTests(unittest.TestCase):
    def test_percentile_uses_nearest_rank_and_ignores_non_finite(self) -> None:
        self.assertEqual(rehearsal._percentile([1.0, 2.0, 3.0, 4.0], 0.95), 4.0)
        self.assertEqual(rehearsal._percentile([1.0, float("nan")], 0.5), 1.0)
        self.assertIsNone(rehearsal._percentile([], 0.95))

    def test_service_labels_are_low_cardinality_and_name_free(self) -> None:
        self.assertEqual(rehearsal._service_name("bankcore-p6e-auth-service-1"), "auth-service")
        self.assertEqual(rehearsal._service_name("/bankcore-p6e-migrate-transactions-1"), "migrate-transactions")
        self.assertEqual(rehearsal._service_name("customer-987654321"), "other")

    def test_phase_contract_covers_required_operational_states(self) -> None:
        self.assertTrue({
            "baseline_idle", "migrations", "service_startup_readiness", "readiness_validation",
            "steady_state", "financial_smoke", "retained_A_B_images", "rollback_A",
            "smoke_failure_injection",
        }.issubset(rehearsal.PHASES_REQUIRED))

    def test_storage_aggregation_does_not_emit_names(self) -> None:
        value = {"Images": {"size_bytes": 100}, "Local Volumes": {"size_bytes": 20}}
        self.assertEqual(rehearsal._storage_total(value), 120)
        self.assertEqual(rehearsal._storage_total(None), None)

    def test_failure_diagnostics_use_fixed_categories_only(self) -> None:
        self.assertEqual(rehearsal._failure_category("Service is not ready after rollout: risk-service"), "readiness")
        self.assertEqual(rehearsal._failure_category("Compose step failed; password=do-not-echo"), "compose_or_command")
        self.assertEqual(rehearsal._failure_category("unrecognized private diagnostic"), "unclassified_runtime_failure")

    def test_nested_docker_stats_are_rejected_when_totals_exceed_cgroup(self) -> None:
        sample = {"cgroup": {"memory_current_bytes": 100, "pids_current": 10, "cpu_quota_cores": 2},
                  "containers": [{"memory_used_bytes": 80, "pids": 8, "cpu_percent": 150},
                                 {"memory_used_bytes": 80, "pids": 8, "cpu_percent": 150}]}
        self.assertFalse(rehearsal._container_stats_consistent([sample]))


if __name__ == "__main__":
    unittest.main()
