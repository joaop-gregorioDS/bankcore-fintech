from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "p6f4-change-plan-validate.py"
SPEC = importlib.util.spec_from_file_location("p6f4_change_plan_validate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class P6F4ChangePlanTests(unittest.TestCase):
    def test_committed_plan_passes_static_contract(self):
        MODULE.validate_plan_text(MODULE.PLAN.read_text(encoding="utf-8"))

    def test_missing_live_data_blocker_fails_closed(self):
        text = MODULE.PLAN.read_text(encoding="utf-8").replace("Unresolved blocker", "Open item", 1)
        with self.assertRaisesRegex(ValueError, "live financial data transition blocker"):
            MODULE.validate_plan_text(text)

    def test_mutating_shell_command_is_rejected(self):
        text = MODULE.PLAN.read_text(encoding="utf-8") + "\n```sh\nsudo ufw allow 1234\n```\n"
        with self.assertRaisesRegex(ValueError, "executable mutation"):
            MODULE.validate_plan_text(text)

    def test_secret_value_is_rejected(self):
        text = MODULE.PLAN.read_text(encoding="utf-8") + "\nTOKEN=actual-sensitive-value\n"
        with self.assertRaisesRegex(ValueError, "secret content"):
            MODULE.validate_plan_text(text)

    def test_missing_rollback_field_is_rejected(self):
        text = MODULE.PLAN.read_text(encoding="utf-8").replace("- **Rollback:**", "- **Recovery:**", 1)
        with self.assertRaisesRegex(ValueError, "missing required field Rollback"):
            MODULE.validate_plan_text(text)


if __name__ == "__main__":
    unittest.main()
