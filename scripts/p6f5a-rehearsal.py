#!/usr/bin/env python3
"""Guarded P6-F5A source-backup and disposable-restore rehearsal.

The default invocation is validation-only. Real database access requires the
long explicit opt-in flag and libpq service/pass files; credentials are never
accepted on the command line or printed.
"""

from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ACK = "I_CONFIRM_READ_ONLY_SOURCE_AND_DISPOSABLE_TARGET"
SERVICES = {
    "auth": ("bankcore_source_auth", "bankcore_rehearsal_auth"),
    "transactions": ("bankcore_source_transactions", "bankcore_rehearsal_transactions"),
}
SOURCE_DATABASES = {"auth": "bankcore_auth", "transactions": "bankcore_transactions"}
TARGET_DB_RE = re.compile(r"^bankcore_rehearsal_(auth|transactions)_[a-z0-9][a-z0-9_-]{0,40}$")
TX_REVISIONS = {
    "tx_001_initial_schema", "tx_002_idempotency_ownership",
    "tx_003_risk_audit_linkage", "tx_004_transactional_outbox",
    "tx_005_outbox_leases",
}
MANIFEST_NAME = "p6f5a-manifest.json"


class RehearsalError(ValueError):
    pass


@dataclass(frozen=True)
class Artifact:
    file: str
    bytes: int
    sha256: str


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_artifact_dir(path: Path, repo_root: Path = ROOT) -> Path:
    """Require a pre-created, private, empty directory outside the checkout."""
    if path.is_symlink():
        raise RehearsalError("artifact directory must not be a symlink")
    if not path.exists() or not path.is_dir():
        raise RehearsalError("artifact directory must already exist")
    resolved = path.resolve(strict=True)
    repo = repo_root.resolve(strict=True)
    if _inside(resolved, repo):
        raise RehearsalError("artifact directory must be outside the repository")
    if any(resolved.iterdir()):
        raise RehearsalError("artifact directory must be empty")
    if os.name == "posix":
        mode = stat.S_IMODE(resolved.stat().st_mode)
        if mode & 0o077 or mode & 0o700 != 0o700:
            raise RehearsalError("artifact directory must grant owner rwx only (mode 0700)")
    return resolved


def validate_private_file(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise RehearsalError(f"{label} must be a regular non-symlink file")
    resolved = path.resolve(strict=True)
    if os.name == "posix":
        mode = stat.S_IMODE(resolved.stat().st_mode)
        if mode & 0o077 or not mode & 0o400:
            raise RehearsalError(f"{label} must be owner-readable only (mode 0600 or stricter)")
    return resolved


def service_file_entries(service_file: Path) -> configparser.ConfigParser:
    if service_file.is_symlink() or not service_file.is_file():
        raise RehearsalError("PGSERVICEFILE must be a regular non-symlink file")
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    try:
        with service_file.open(encoding="utf-8") as handle:
            parser.read_file(handle)
    except (OSError, configparser.Error) as exc:
        raise RehearsalError("PGSERVICEFILE could not be validated") from exc
    for alias in (name for pair in SERVICES.values() for name in pair):
        if not parser.has_section(alias):
            raise RehearsalError("PGSERVICEFILE is missing a required logical service")
        section = parser[alias]
        if any(key in section for key in ("password", "passfile", "sslpassword")):
            raise RehearsalError("credentials must be supplied only through a protected PGPASSFILE")
        if not section.get("dbname", "").strip():
            raise RehearsalError("each logical service must declare a database name")
    for logical, (source, _) in SERVICES.items():
        if parser[source].get("dbname", "") != SOURCE_DATABASES[logical]:
            raise RehearsalError("source service database identity does not match the reviewed contract")
    return parser


def validate_target_identity(database: str, marker: str, logical_name: str) -> None:
    match = TARGET_DB_RE.fullmatch(database)
    if not match or match.group(1) != logical_name or len(database) > 63:
        raise RehearsalError("restore target is not an explicitly named P6-F5A rehearsal database")
    if marker != "disposable":
        raise RehearsalError("restore target lacks the server-side disposable environment marker")


def validate_manifest(manifest: dict[str, Any]) -> None:
    if set(manifest) != {"format", "created_at_utc", "pg_dump_version", "databases"}:
        raise RehearsalError("manifest contains missing or unsupported metadata fields")
    if manifest["format"] != "bankcore-p6f5a-custom-v1":
        raise RehearsalError("unsupported rehearsal manifest format")
    databases = manifest["databases"]
    if not isinstance(databases, dict) or set(databases) != set(SERVICES):
        raise RehearsalError("manifest must describe exactly Auth and Transactions")
    for name, entry in databases.items():
        if set(entry) != {"source_service", "restored_revision", "artifact"}:
            raise RehearsalError("manifest contains unexpected database metadata")
        if entry["source_service"] != SERVICES[name][0]:
            raise RehearsalError("manifest source service does not match the logical service")
        artifact = entry["artifact"]
        if set(artifact) != {"file", "bytes", "sha256"}:
            raise RehearsalError("manifest artifact metadata is malformed")
        if artifact["file"] != f"{name}.dump" or not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]):
            raise RehearsalError("manifest artifact path or checksum is invalid")
        if type(artifact["bytes"]) is not int or artifact["bytes"] <= 0:
            raise RehearsalError("manifest artifact size is invalid")
    rendered = json.dumps(manifest, sort_keys=True).lower()
    if any(marker in rendered for marker in ("password", "secret", "token", "postgres://", "-----begin")):
        raise RehearsalError("manifest contains a forbidden credential/secret marker")


def _clean_env() -> dict[str, str]:
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "PATHEXT", "TEMP", "TMP", "PGSERVICEFILE", "PGPASSFILE", "PGSSLMODE", "PGSSLROOTCERT", "PGCONNECT_TIMEOUT"}
    result = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    result["PGCONNECT_TIMEOUT"] = "8"
    return result


def _run(argv: list[str], *, env: dict[str, str] | None = None) -> str:
    """Run an argv-only tool and never include command output in an error."""
    try:
        result = subprocess.run(
            argv, check=False, capture_output=True, text=True, timeout=1800,
            shell=False, env=env or _clean_env(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RehearsalError(f"required PostgreSQL utility failed to start or timed out: {Path(argv[0]).name}") from exc
    if result.returncode:
        raise RehearsalError(f"PostgreSQL utility failed ({Path(argv[0]).name}, exit {result.returncode}); output redacted")
    return result.stdout.strip()


def _psql(service: str, sql: str) -> str:
    return _run(["psql", "--no-password", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "--dbname", f"service={service}", "-c", sql])


def _target_info(service: str, logical_name: str, expected_database: str) -> tuple[str, str, int]:
    raw = _psql(service, "SELECT json_build_array(current_database(), current_setting('bankcore.environment', true), (SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema'))); ")
    try:
        database, marker, user_tables = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise RehearsalError("disposable target preflight returned an invalid response") from exc
    validate_target_identity(str(database), str(marker or ""), logical_name)
    if database != expected_database:
        raise RehearsalError("connected restore target differs from the reviewed service-file database")
    if int(user_tables) != 0:
        raise RehearsalError("restore target is not empty; refusing to overwrite existing data")
    return str(database), str(marker), int(user_tables)


def _source_identity(service: str, logical_name: str) -> None:
    actual = _psql(service, "SELECT current_database();")
    if actual != SOURCE_DATABASES[logical_name]:
        raise RehearsalError("read-only source identity did not match the reviewed database contract")


def _snapshot(service: str) -> dict[str, Any]:
    # Names are fixed by the application schema; no source values/identifiers are selected.
    tables = _psql(
        service,
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;",
    ).splitlines()
    counts: dict[str, int] = {}
    allowed = {"users", "accounts", "ledger_transactions", "ledger_entries", "idempotency_records", "outbox_events"}
    for table in tables:
        if table not in allowed:
            continue
        count_text = _psql(service, f'SELECT count(*) FROM public."{table}";')
        try:
            counts[table] = int(count_text)
        except ValueError as exc:
            raise RehearsalError("source snapshot count query returned invalid metadata") from exc
    revision_text = _psql(
        service,
        "SELECT CASE WHEN to_regclass('public.alembic_version') IS NULL THEN 'unversioned' ELSE COALESCE((SELECT string_agg(version_num, ',' ORDER BY version_num) FROM public.alembic_version), 'invalid_empty_alembic_version') END;",
    )
    integrity: dict[str, int] = {}
    if {"accounts", "ledger_transactions", "ledger_entries"}.issubset(counts):
        integrity["missing_balance_count"] = int(_psql(service, "SELECT count(*) FROM accounts WHERE balance_cents IS NULL;"))
        integrity["orphan_ledger_entry_count"] = int(_psql(
            service,
            "SELECT count(*) FROM ledger_entries e LEFT JOIN ledger_transactions t ON t.id=e.transaction_id LEFT JOIN accounts a ON a.id=e.account_id WHERE t.id IS NULL OR a.id IS NULL;",
        ))
        integrity["unbalanced_transaction_count"] = int(_psql(
            service,
            "SELECT count(*) FROM (SELECT transaction_id FROM ledger_entries GROUP BY transaction_id HAVING SUM(CASE WHEN side='DEBIT' THEN amount_cents ELSE 0 END) <> SUM(CASE WHEN side='CREDIT' THEN amount_cents ELSE 0 END)) q;",
        ))
    if "idempotency_records" in counts:
        integrity["orphan_idempotency_count"] = int(_psql(
            service,
            "SELECT count(*) FROM idempotency_records i LEFT JOIN ledger_transactions t ON t.id=i.transaction_id WHERE i.transaction_id IS NOT NULL AND t.id IS NULL;",
        ))
        integrity["processing_idempotency_count"] = int(_psql(
            service,
            "SELECT count(*) FROM idempotency_records WHERE status='PROCESSING';",
        ))
    if "outbox_events" in counts:
        integrity["orphan_outbox_event_count"] = int(_psql(
            service,
            "SELECT count(*) FROM outbox_events o LEFT JOIN ledger_transactions t ON t.id=o.aggregate_id WHERE t.id IS NULL;",
        ))
    return {"counts": counts, "alembic_revision": revision_text or "unversioned", "integrity": integrity}


def validate_restored_snapshot(logical: str, snapshot: dict[str, Any]) -> None:
    required_tables = {
        "auth": {"users"},
        "transactions": {"accounts", "ledger_transactions", "ledger_entries"},
    }
    if logical not in required_tables or not required_tables[logical].issubset(snapshot.get("counts", {})):
        raise RehearsalError("restored database is missing required application tables; details withheld")
    revision = snapshot.get("alembic_revision")
    allowed_revisions = {"unversioned", "auth_001_initial_users"} if logical == "auth" else TX_REVISIONS | {"unversioned"}
    if revision not in allowed_revisions:
        raise RehearsalError(f"restored {logical.title()} schema has an unknown or ambiguous migration revision")
    if logical == "transactions" and any(snapshot.get("integrity", {}).values()):
        raise RehearsalError("restored Transactions copy failed a basic financial integrity check; details withheld")


def _hash_file(path: Path) -> Artifact:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return Artifact(path.name, size, digest.hexdigest())


def _write_private(path: Path, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    if os.name == "posix":
        os.chmod(path, 0o600)


def execute_rehearsal(artifact_dir: Path) -> dict[str, Any]:
    if os.name != "posix":
        raise RehearsalError("execution requires POSIX permissions; use an isolated Linux/WSL environment")
    service_file_value = os.environ.get("PGSERVICEFILE")
    pass_file_value = os.environ.get("PGPASSFILE")
    if not service_file_value or not pass_file_value:
        raise RehearsalError("PGSERVICEFILE and PGPASSFILE paths are required; credential values are never accepted")
    service_file = Path(service_file_value)
    pass_file = validate_private_file(Path(pass_file_value), "PGPASSFILE")
    services = service_file_entries(service_file)
    for logical, (source, target) in SERVICES.items():
        source_endpoint = (services[source].get("host", ""), services[source].get("hostaddr", ""), services[source].get("port", "5432"))
        target_endpoint = (services[target].get("host", ""), services[target].get("hostaddr", ""), services[target].get("port", "5432"))
        if source_endpoint == target_endpoint:
            raise RehearsalError("source and disposable target must be on distinct PostgreSQL endpoints")
    if os.name == "posix" and stat.S_IMODE(service_file.resolve().stat().st_mode) & 0o077:
        raise RehearsalError("PGSERVICEFILE permissions must be 0600 or stricter")
    env = _clean_env()
    env["PGSERVICEFILE"] = str(service_file.resolve(strict=True))
    env["PGPASSFILE"] = str(pass_file)
    for utility in ("pg_dump", "pg_restore", "psql"):
        if not shutil.which(utility, path=env.get("PATH")):
            raise RehearsalError(f"required PostgreSQL utility is unavailable: {utility}")

    for logical, (source, target) in SERVICES.items():
        _source_identity(source, logical)
        target_db = services[target].get("dbname", "")
        match = TARGET_DB_RE.fullmatch(target_db)
        if not match or match.group(1) != logical:
            raise RehearsalError("target service database name must use the explicit rehearsal identity")
        # Target is inspected before any dump is made; marker and empty-schema gates are fail-closed.
        _target_info(target, logical, target_db)

    version = _run(["pg_dump", "--version"], env=env)
    artifacts: dict[str, Artifact] = {}
    for logical, (source, _) in SERVICES.items():
        dump_path = artifact_dir / f"{logical}.dump"
        _run([
            "pg_dump", "--no-password", "--serializable-deferrable", "--format=custom", "--no-owner", "--no-acl",
            "--file", str(dump_path), "--dbname", f"service={source}",
        ], env=env)
        if not dump_path.is_file() or dump_path.is_symlink():
            raise RehearsalError("pg_dump did not create the expected regular archive")
        if os.name == "posix":
            os.chmod(dump_path, 0o600)
        _run(["pg_restore", "--list", str(dump_path)], env=env)
        artifacts[logical] = _hash_file(dump_path)

    for logical, (_, target) in SERVICES.items():
        _target_info(target, logical, services[target].get("dbname", ""))
        _run([
            "pg_restore", "--no-password", "--exit-on-error", "--single-transaction", "--no-owner", "--no-acl",
            "--dbname", f"service={target}", str(artifact_dir / f"{logical}.dump"),
        ], env=env)

    restored: dict[str, dict[str, Any]] = {}
    for logical, (_, target) in SERVICES.items():
        restored[logical] = _snapshot(target)
    for logical in SERVICES:
        validate_restored_snapshot(logical, restored[logical])

    manifest = {
        "format": "bankcore-p6f5a-custom-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "pg_dump_version": version,
        "databases": {
            logical: {
                "source_service": SERVICES[logical][0],
                "restored_revision": restored[logical]["alembic_revision"],
                "artifact": asdict(artifacts[logical]),
            }
            for logical in SERVICES
        },
    }
    validate_manifest(manifest)
    _write_private(artifact_dir / MANIFEST_NAME, json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return {"core_schema_verified": {"auth": True, "transactions": True}, "manifest": MANIFEST_NAME}


def main() -> int:
    parser = argparse.ArgumentParser(description="P6-F5A guarded backup/restore rehearsal; dry-run by default")
    parser.add_argument("--artifacts", type=Path, required=True, help="pre-created private directory outside the repository")
    parser.add_argument("--execute", action="store_true", help="perform read-only source dumps and restore only into marked empty disposable databases")
    parser.add_argument("--ack", default="", help=f"must exactly equal {ACK} when --execute is supplied")
    args = parser.parse_args()
    artifact_dir = validate_artifact_dir(args.artifacts)
    if not args.execute:
        print(json.dumps({"mode": "validation-only", "artifact_dir_valid": True, "database_access": False, "mutations": False}))
        return 0
    if args.ack != ACK:
        raise RehearsalError("explicit execution acknowledgement is missing")
    result = execute_rehearsal(artifact_dir)
    print(json.dumps({"mode": "completed", "source_read_only": True, "disposable_restore": result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RehearsalError as error:
        print(f"P6-F5A STOP: {error}", file=sys.stderr)
        raise SystemExit(2)
