from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "p6f5a-rehearsal.py"
SPEC = importlib.util.spec_from_file_location("p6f5a_rehearsal", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class P6F5ARehearsalTests(unittest.TestCase):
    def test_artifact_directory_must_be_outside_repository_and_private(self):
        with tempfile.TemporaryDirectory() as temporary:
            outside = Path(temporary) / "secure"
            outside.mkdir()
            if os.name == "posix":
                outside.chmod(0o700)
            self.assertEqual(MODULE.validate_artifact_dir(outside), outside.resolve())
            with self.assertRaisesRegex(MODULE.RehearsalError, "outside the repository"):
                MODULE.validate_artifact_dir(ROOT, repo_root=ROOT)

    def test_artifact_directory_must_be_empty(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "unexpected.txt").touch()
            with self.assertRaisesRegex(MODULE.RehearsalError, "must be empty"):
                MODULE.validate_artifact_dir(directory)

    def test_default_mode_is_validation_only_and_never_connects(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            if os.name == "posix":
                directory.chmod(0o700)
            output = io.StringIO()
            with patch.object(sys, "argv", [str(SCRIPT), "--artifacts", str(directory)]), \
                 patch.object(MODULE, "_psql", side_effect=AssertionError("database access attempted")), \
                 redirect_stdout(output):
                self.assertEqual(MODULE.main(), 0)
            self.assertIn('"database_access": false', output.getvalue())

    def test_execute_requires_explicit_ack_before_database_access(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            if os.name == "posix":
                directory.chmod(0o700)
            with patch.object(sys, "argv", [str(SCRIPT), "--artifacts", str(directory), "--execute"]), \
                 patch.object(MODULE, "_psql", side_effect=AssertionError("database access attempted")):
                with self.assertRaisesRegex(MODULE.RehearsalError, "acknowledgement is missing"):
                    MODULE.main()

    def test_passfile_permissions_are_checked_on_posix(self):
        with tempfile.TemporaryDirectory() as temporary:
            secret_file = Path(temporary) / "pgpass"
            secret_file.write_text("not-a-real-secret\n", encoding="utf-8")
            if os.name == "posix":
                secret_file.chmod(0o644)
                with self.assertRaisesRegex(MODULE.RehearsalError, "0600"):
                    MODULE.validate_private_file(secret_file, "PGPASSFILE")
                secret_file.chmod(0o600)
            self.assertEqual(MODULE.validate_private_file(secret_file, "PGPASSFILE"), secret_file.resolve())

    def test_failed_tool_output_is_redacted_and_never_uses_a_shell(self):
        result = type("Result", (), {"returncode": 1, "stdout": "", "stderr": "synthetic-private-marker"})()
        with patch.object(MODULE.subprocess, "run", return_value=result) as run:
            with self.assertRaises(MODULE.RehearsalError) as raised:
                MODULE._run(["pg_dump", "--version"])
        self.assertNotIn("synthetic-private-marker", str(raised.exception))
        self.assertIs(run.call_args.kwargs["shell"], False)

    def test_restore_target_requires_expected_name_and_server_marker(self):
        MODULE.validate_target_identity("bankcore_rehearsal_auth_20260921", "disposable", "auth")
        for database, marker, logical in (
            ("bankcore_auth", "disposable", "auth"),
            ("bankcore_rehearsal_transactions_abc", "disposable", "auth"),
            ("bankcore_rehearsal_auth_abc", "production", "auth"),
        ):
            with self.subTest(database=database, marker=marker):
                with self.assertRaises(MODULE.RehearsalError):
                    MODULE.validate_target_identity(database, marker, logical)

    def test_restored_snapshot_rejects_unknown_revision_and_bad_ledger_invariant(self):
        MODULE.validate_restored_snapshot("transactions", {
            "counts": {"accounts": 1, "ledger_transactions": 1, "ledger_entries": 2},
            "alembic_revision": "tx_005_outbox_leases",
            "integrity": {"unbalanced_transaction_count": 0},
        })
        unknown = {
            "counts": {"accounts": 1, "ledger_transactions": 1, "ledger_entries": 2},
            "alembic_revision": "unknown_revision",
            "integrity": {},
        }
        with self.assertRaisesRegex(MODULE.RehearsalError, "unknown or ambiguous"):
            MODULE.validate_restored_snapshot("transactions", unknown)
        bad_ledger = {**unknown, "alembic_revision": "tx_005_outbox_leases", "integrity": {"orphan_count": 1}}
        with self.assertRaisesRegex(MODULE.RehearsalError, "integrity check"):
            MODULE.validate_restored_snapshot("transactions", bad_ledger)

    def test_manifest_has_only_sanitized_metadata(self):
        artifact = {"file": "auth.dump", "bytes": 17, "sha256": "a" * 64}
        manifest = {
            "format": "bankcore-p6f5a-custom-v1",
            "created_at_utc": "2026-09-21T00:00:00+00:00",
            "pg_dump_version": "pg_dump 16.4",
            "databases": {
                "auth": {"source_service": "bankcore_source_auth", "restored_revision": "auth_001_initial_users", "artifact": artifact},
                "transactions": {"source_service": "bankcore_source_transactions", "restored_revision": "tx_005_outbox_leases", "artifact": {**artifact, "file": "transactions.dump"}},
            },
        }
        MODULE.validate_manifest(manifest)
        unsafe = json.loads(json.dumps(manifest))
        unsafe["DATABASE_URL"] = "postgres://placeholder.invalid/database"
        with self.assertRaises(MODULE.RehearsalError):
            MODULE.validate_manifest(unsafe)

    def test_service_file_rejects_password_values_and_requires_fixed_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            service_file = Path(temporary) / "pg_service.conf"
            sections = []
            for logical, (source, target) in MODULE.SERVICES.items():
                sections.extend((f"[{source}]", f"dbname={MODULE.SOURCE_DATABASES[logical]}", "host=127.0.0.1", ""))
                sections.extend((f"[{target}]", f"dbname=bankcore_rehearsal_{logical}_20260921", "host=127.0.0.1", ""))
            service_file.write_text("\n".join(sections), encoding="utf-8")
            MODULE.service_file_entries(service_file)
            service_file.write_text(service_file.read_text(encoding="utf-8").replace("host=127.0.0.1", "password=unsafe", 1), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.RehearsalError, "credentials must be supplied only"):
                MODULE.service_file_entries(service_file)

    def test_source_alias_must_point_to_reviewed_database_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            service_file = Path(temporary) / "pg_service.conf"
            sections = []
            for logical, (source, target) in MODULE.SERVICES.items():
                source_db = MODULE.SOURCE_DATABASES[logical]
                if logical == "auth":
                    source_db = "bankcore_rehearsal_auth_test"
                sections.extend((f"[{source}]", f"dbname={source_db}", "host=source.example.invalid", ""))
                sections.extend((f"[{target}]", f"dbname=bankcore_rehearsal_{logical}_test", "host=target.example.invalid", ""))
            service_file.write_text("\n".join(sections), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.RehearsalError, "source service database identity"):
                MODULE.service_file_entries(service_file)


if __name__ == "__main__":
    unittest.main()
