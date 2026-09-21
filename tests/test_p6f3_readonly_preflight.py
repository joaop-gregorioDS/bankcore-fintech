from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "p6f3-readonly-preflight.py"
SPEC = importlib.util.spec_from_file_location("p6f3_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_mutating_command_is_rejected() -> None:
    with pytest.raises(ValueError):
        MODULE.validate_read_only_command(["rm", "-rf", "/"])


def test_shell_execution_is_rejected() -> None:
    with pytest.raises(ValueError):
        MODULE.validate_read_only_command(["docker", "--shell", "echo unsafe"])


def test_read_only_command_is_allowed() -> None:
    MODULE.validate_read_only_command(["uname", "-a"])


def test_sensitive_values_are_redacted() -> None:
    output = MODULE.sanitize(
        "DATABASE_URL=postgres://user:password@example/db\n"
        "Authorization: Bearer super-secret\n"
        "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----"
    )
    assert "password@example" not in output
    assert "super-secret" not in output
    assert "BEGIN PRIVATE KEY" not in output


def test_report_declares_no_mutation_capabilities() -> None:
    report = MODULE.build_report({"listening_ports": [], "bankcore_user": "present", "docker_rootless_signal": "rootless mentioned", "config_secret_values": "not read; names/metadata only"}, [])
    assert report["mode"] == "read-only"
    assert all(value is False for value in report["safety"].values())
