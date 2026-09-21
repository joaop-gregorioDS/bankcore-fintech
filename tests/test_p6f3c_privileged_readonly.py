from __future__ import annotations

import importlib.util
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "p6f3c-privileged-readonly.py"
SPEC = importlib.util.spec_from_file_location("p6f3c_readonly", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_exact_read_only_commands_are_allowed() -> None:
    MODULE.validate_privileged_command(["sudo", "-n", "ss", "-lntup"])
    MODULE.validate_privileged_command(["sudo", "-n", "nft", "list", "ruleset"])
    MODULE.validate_privileged_command(["sudo", "-n", "nginx", "-T"])
    MODULE.validate_privileged_command(["sudo", "-n", "true"])


@pytest.mark.security
@pytest.mark.unit
@pytest.mark.parametrize(
    "command",
    [
        ["sudo", "-n", "rm", "-rf", "/"],
        ["sudo", "-n", "systemctl", "restart", "nginx"],
        ["sudo", "-n", "docker", "compose", "up", "-d"],
        ["sudo", "-n", "sh", "-c", "id"],
        ["sudo", "-n", "find", "/", "-exec", "cat", "{}", ";", "-printf", MODULE.METADATA_FORMAT],
    ],
)
def test_mutation_or_shell_is_rejected(command: list[str]) -> None:
    with pytest.raises(ValueError):
        MODULE.validate_privileged_command(command)


def test_sensitive_certificate_paths_are_not_read() -> None:
    with pytest.raises(ValueError):
        MODULE.validate_privileged_command(
            [
                "sudo",
                "-n",
                "openssl",
                "x509",
                "-in",
                "/etc/letsencrypt/live/example/privkey.pem",
                "-noout",
            ]
        )


def test_metadata_find_rejects_unapproved_roots() -> None:
    with pytest.raises(ValueError):
        MODULE.validate_privileged_command(
            ["sudo", "-n", "find", "/home/deploy", "-maxdepth", "4", "-type", "f", "-printf", MODULE.METADATA_FORMAT]
        )


def test_redaction_never_preserves_secret_values() -> None:
    sanitized = MODULE.sanitize("Authorization: Bearer abc\nPASSWORD=xyz\npublic=ok")
    assert "abc" not in sanitized
    assert "xyz" not in sanitized
    assert "public=<present>" in sanitized


def test_nginx_output_is_limited_to_safe_directives() -> None:
    sanitized = MODULE.sanitize_nginx_config(
        "listen 443 ssl;\n"
        "server_name bankcore.example;\n"
        "proxy_pass http://internal:8080;\n"
        "add_header Authorization secret;\n"
        "ssl_certificate_key /etc/letsencrypt/live/example/privkey.pem;\n"
    )
    assert "listen 443 ssl;" in sanitized
    assert "server_name bankcore.example;" in sanitized
    assert "proxy_pass http://internal:8080;" in sanitized
    assert "Authorization" not in sanitized
    assert "privkey.pem" not in sanitized


def test_missing_sudo_ticket_aborts_before_collection(monkeypatch, capsys) -> None:
    monkeypatch.setattr(MODULE, "preflight_sudo_ticket", lambda: (False, "sudo ticket unavailable"))
    monkeypatch.setattr(MODULE, "collect", lambda: (_ for _ in ()).throw(AssertionError("collection started")))

    assert MODULE.main(["--privileged-readonly", "--json"]) == 2
    output = capsys.readouterr().out
    assert '"privileged_collection": "not started"' in output
    assert "sudo ticket unavailable" in output


def test_preflight_uses_noninteractive_sudo(monkeypatch) -> None:
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    assert MODULE.preflight_sudo_ticket() == (True, "authorized")
    assert calls[0][0] == ["sudo", "-n", "true"]
    assert calls[0][1]["shell"] is False
