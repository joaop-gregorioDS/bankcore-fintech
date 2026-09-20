"""Disposable PostgreSQL backup/restore verification for BankCore."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg
import bcrypt

AUTH_DB = "bankcore_test_auth"
TRANSACTIONS_DB = "bankcore_test_transactions"
SOURCE_HOST = os.environ.get("BACKUP_SOURCE_HOST", "backup-source")
TARGET_HOST = os.environ.get("BACKUP_TARGET_HOST", "backup-target")
DB_USER = os.environ.get("BACKUP_POSTGRES_USER", "bankadmin")
DB_PASSWORD = os.environ["BACKUP_POSTGRES_PASSWORD"]
TEST_PASSWORD = "BackupOnly-2026!"
USER_ID = "11111111-1111-4111-8111-111111111111"
DESTINATION_USER_ID = "22222222-2222-4222-8222-222222222222"
SOURCE_ACCOUNT_ID = "33333333-3333-4333-8333-333333333333"
DESTINATION_ACCOUNT_ID = "44444444-4444-4444-8444-444444444444"
TRANSACTION_ID = "55555555-5555-4555-8555-555555555555"
DEBIT_ENTRY_ID = "66666666-6666-4666-8666-666666666666"
CREDIT_ENTRY_ID = "77777777-7777-4777-8777-777777777777"
IDEMPOTENCY_ID = "88888888-8888-4888-8888-888888888888"
FIXED_TIME = datetime(2026, 1, 1, 12, 0, 0)


class BackupValidationError(RuntimeError):
    """Raised before pg_restore when a backup cannot be trusted."""


class RestoreSafetyError(RuntimeError):
    """Raised when a restore target is not explicitly disposable test data."""


@dataclass(frozen=True)
class DatabaseTarget:
    host: str
    database: str


def _connection_kwargs(target: DatabaseTarget) -> dict[str, Any]:
    return {
        "host": target.host,
        "port": 5432,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": target.database,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_pg_tool(arguments: list[str], description: str) -> None:
    environment = os.environ.copy()
    environment["PGPASSWORD"] = DB_PASSWORD
    result = subprocess.run(
        arguments,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{description} failed with exit code {result.returncode}.")


def _require_test_database(database: str, *, explicit_test_mode: bool) -> None:
    if not explicit_test_mode or not database.startswith("bankcore_test_"):
        raise RestoreSafetyError(
            "Restore requires explicit test mode and a bankcore_test_ database."
        )


def _manifest_for(artifact_dir: Path, versions: dict[str, str]) -> dict[str, Any]:
    databases = {}
    for name, version in versions.items():
        dump_path = artifact_dir / f"{name}.dump"
        databases[name] = {
            "dump": dump_path.name,
            "sha256": _sha256(dump_path),
            "size_bytes": dump_path.stat().st_size,
            "alembic_version": version,
        }
    return {
        "format": "bankcore-postgresql-custom-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "databases": databases,
    }


def _write_manifest(artifact_dir: Path, manifest: dict[str, Any]) -> None:
    (artifact_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _verify_manifest(artifact_dir: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(
            (artifact_dir / "manifest.json").read_text(encoding="utf-8")
        )
        if manifest.get("format") != "bankcore-postgresql-custom-v1":
            raise BackupValidationError("Unsupported backup manifest format.")
        for entry in manifest["databases"].values():
            dump_path = artifact_dir / entry["dump"]
            if not dump_path.is_file() or _sha256(dump_path) != entry["sha256"]:
                raise BackupValidationError("Backup checksum validation failed.")
            if dump_path.stat().st_size != entry["size_bytes"]:
                raise BackupValidationError("Backup size validation failed.")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise BackupValidationError("Backup manifest is invalid.") from exc
    return manifest


async def _alembic_version(conn: asyncpg.Connection) -> str:
    return await conn.fetchval("SELECT version_num FROM alembic_version LIMIT 1")


async def _snapshot_auth(target: DatabaseTarget) -> dict[str, Any]:
    conn = await asyncpg.connect(**_connection_kwargs(target))
    try:
        rows = await conn.fetch(
            """
            SELECT id::text, tax_id, full_name, email, is_active, created_at::text
            FROM users ORDER BY id
            """
        )
        return {
            "alembic_version": await _alembic_version(conn),
            "user_count": len(rows),
            "users": [dict(row) for row in rows],
        }
    finally:
        await conn.close()


async def _snapshot_transactions(target: DatabaseTarget) -> dict[str, Any]:
    conn = await asyncpg.connect(**_connection_kwargs(target))
    try:
        accounts = await conn.fetch(
            """
            SELECT id::text, user_id::text, account_number, balance_cents,
                   is_active, created_at::text FROM accounts ORDER BY id
            """
        )
        transactions = await conn.fetch(
            """
            SELECT id::text, idempotency_key, source_account_id::text,
                   destination_account_id::text, amount_cents, transaction_type,
                   status, description, created_at::text
            FROM ledger_transactions ORDER BY id
            """
        )
        entries = await conn.fetch(
            """
            SELECT id::text, transaction_id::text, account_id::text, side,
                   amount_cents, created_at::text FROM ledger_entries ORDER BY id
            """
        )
        idempotency = await conn.fetch(
            """
            SELECT id::text, idempotency_key, user_id::text, account_id::text,
                   operation_type, request_fingerprint, transaction_id::text,
                   status, created_at::text
            FROM idempotency_records ORDER BY id
            """
        )
        orphan_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM ledger_entries e
            LEFT JOIN ledger_transactions t ON t.id = e.transaction_id
            LEFT JOIN accounts a ON a.id = e.account_id
            WHERE t.id IS NULL OR a.id IS NULL
            """
        )
        unbalanced_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM (
                SELECT transaction_id,
                       SUM(CASE WHEN side = 'DEBIT' THEN amount_cents ELSE 0 END) debit,
                       SUM(CASE WHEN side = 'CREDIT' THEN amount_cents ELSE 0 END) credit
                FROM ledger_entries GROUP BY transaction_id
                HAVING SUM(CASE WHEN side = 'DEBIT' THEN amount_cents ELSE 0 END)
                    <> SUM(CASE WHEN side = 'CREDIT' THEN amount_cents ELSE 0 END)
            ) unbalanced
            """
        )
        processing_count = await conn.fetchval(
            "SELECT COUNT(*) FROM idempotency_records WHERE status = 'PROCESSING'"
        )
        return {
            "alembic_version": await _alembic_version(conn),
            "account_count": len(accounts),
            "ledger_transaction_count": len(transactions),
            "ledger_entry_count": len(entries),
            "idempotency_record_count": len(idempotency),
            "accounts": [dict(row) for row in accounts],
            "ledger_transactions": [dict(row) for row in transactions],
            "ledger_entries": [dict(row) for row in entries],
            "idempotency_records": [dict(row) for row in idempotency],
            "orphan_count": orphan_count,
            "unbalanced_transaction_count": unbalanced_count,
            "processing_count": processing_count,
        }
    finally:
        await conn.close()


async def _seed_source() -> None:
    auth = await asyncpg.connect(**_connection_kwargs(DatabaseTarget(SOURCE_HOST, AUTH_DB)))
    try:
        password_hash = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()
        for user_id, tax_id, full_name, email in (
            (USER_ID, "11111111111", "Backup Test User", "backup-test-1@example.invalid"),
            (DESTINATION_USER_ID, "22222222222", "Backup Test Destination", "backup-test-2@example.invalid"),
        ):
            await auth.execute(
                """
                INSERT INTO users (id, tax_id, full_name, email, hashed_password, is_active, created_at)
                VALUES ($1::uuid, $2, $3, $4, $5, TRUE, $6)
                ON CONFLICT (id) DO NOTHING
                """,
                user_id, tax_id, full_name, email, password_hash, FIXED_TIME,
            )
    finally:
        await auth.close()

    transactions = await asyncpg.connect(
        **_connection_kwargs(DatabaseTarget(SOURCE_HOST, TRANSACTIONS_DB))
    )
    try:
        await transactions.execute(
            """
            INSERT INTO accounts (id, user_id, account_number, balance_cents, is_active, created_at)
            VALUES ($1::uuid, $2::uuid, '90000-1', 97500, TRUE, $5),
                   ($3::uuid, $4::uuid, '90000-2', 12500, TRUE, $5)
            ON CONFLICT (id) DO NOTHING
            """,
            SOURCE_ACCOUNT_ID, USER_ID, DESTINATION_ACCOUNT_ID,
            DESTINATION_USER_ID, FIXED_TIME,
        )
        await transactions.execute(
            """
            INSERT INTO ledger_transactions
                (id, idempotency_key, source_account_id, destination_account_id,
                 amount_cents, transaction_type, status, description, created_at)
            VALUES ($1::uuid, 'backup-transfer-1', $2::uuid, $3::uuid,
                    2500, 'TRANSFER', 'COMPLETED', 'Disposable backup fixture', $4)
            ON CONFLICT (id) DO NOTHING
            """,
            TRANSACTION_ID, SOURCE_ACCOUNT_ID, DESTINATION_ACCOUNT_ID, FIXED_TIME,
        )
        await transactions.execute(
            """
            INSERT INTO ledger_entries
                (id, transaction_id, account_id, side, amount_cents, created_at)
            VALUES ($1::uuid, $3::uuid, $4::uuid, 'DEBIT', 2500, $6),
                   ($2::uuid, $3::uuid, $5::uuid, 'CREDIT', 2500, $6)
            ON CONFLICT (id) DO NOTHING
            """,
            DEBIT_ENTRY_ID, CREDIT_ENTRY_ID, TRANSACTION_ID,
            SOURCE_ACCOUNT_ID, DESTINATION_ACCOUNT_ID, FIXED_TIME,
        )
        await transactions.execute(
            """
            INSERT INTO idempotency_records
                (id, idempotency_key, user_id, account_id, operation_type,
                 request_fingerprint, transaction_id, status, created_at)
            VALUES ($1::uuid, 'backup-transfer-1', $2::uuid, $3::uuid,
                    'TRANSFER', repeat('a', 64), $4::uuid, 'COMPLETED', $5)
            ON CONFLICT (id) DO NOTHING
            """,
            IDEMPOTENCY_ID, USER_ID, SOURCE_ACCOUNT_ID, TRANSACTION_ID, FIXED_TIME,
        )
    finally:
        await transactions.close()


def _dump_database(artifact_dir: Path, source: DatabaseTarget, logical_name: str) -> None:
    _run_pg_tool(
        [
            "pg_dump", "--format=custom", "--no-owner", "--no-privileges",
            "--file", str(artifact_dir / f"{logical_name}.dump"),
            "--host", source.host, "--port", "5432", "--username", DB_USER,
            "--dbname", source.database,
        ],
        f"{logical_name} backup",
    )


def _restore_database(
    artifact_dir: Path,
    manifest: dict[str, Any],
    target: DatabaseTarget,
    logical_name: str,
    *,
    explicit_test_mode: bool,
) -> None:
    _require_test_database(target.database, explicit_test_mode=explicit_test_mode)
    _verify_manifest(artifact_dir)
    _run_pg_tool(
        [
            "pg_restore", "--exit-on-error", "--single-transaction", "--clean",
            "--if-exists", "--no-owner", "--no-privileges", "--host", target.host,
            "--port", "5432", "--username", DB_USER, "--dbname", target.database,
            str(artifact_dir / manifest["databases"][logical_name]["dump"]),
        ],
        f"{logical_name} restore",
    )


async def _verify_authentication(target: DatabaseTarget) -> None:
    conn = await asyncpg.connect(**_connection_kwargs(target))
    try:
        password_hash = await conn.fetchval(
            "SELECT hashed_password FROM users WHERE id = $1::uuid", USER_ID
        )
        if not password_hash or not bcrypt.checkpw(TEST_PASSWORD.encode(), password_hash.encode()):
            raise RuntimeError("Restored authentication credential verification failed.")
    finally:
        await conn.close()


async def _scenario(artifact_dir: Path) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    await _seed_source()
    source_auth = DatabaseTarget(SOURCE_HOST, AUTH_DB)
    source_transactions = DatabaseTarget(SOURCE_HOST, TRANSACTIONS_DB)
    target_auth = DatabaseTarget(TARGET_HOST, AUTH_DB)
    target_transactions = DatabaseTarget(TARGET_HOST, TRANSACTIONS_DB)
    before_auth = await _snapshot_auth(source_auth)
    before_transactions = await _snapshot_transactions(source_transactions)
    _dump_database(artifact_dir, source_auth, "auth")
    _dump_database(artifact_dir, source_transactions, "transactions")
    manifest = _manifest_for(artifact_dir, {
        "auth": before_auth["alembic_version"],
        "transactions": before_transactions["alembic_version"],
    })
    _write_manifest(artifact_dir, manifest)
    _verify_manifest(artifact_dir)
    _restore_database(artifact_dir, manifest, target_auth, "auth", explicit_test_mode=True)
    _restore_database(artifact_dir, manifest, target_transactions, "transactions", explicit_test_mode=True)
    after_auth = await _snapshot_auth(target_auth)
    after_transactions = await _snapshot_transactions(target_transactions)
    await _verify_authentication(target_auth)
    if before_auth != after_auth or before_transactions != after_transactions:
        raise RuntimeError("Restored database snapshot differs from source snapshot.")
    if any(after_transactions[key] != 0 for key in (
        "orphan_count", "unbalanced_transaction_count", "processing_count"
    )):
        raise RuntimeError("Restored financial integrity checks failed.")

    with tempfile.TemporaryDirectory(dir=artifact_dir) as tampered_dir_name:
        tampered_dir = Path(tampered_dir_name)
        for path in artifact_dir.iterdir():
            if path.is_file():
                shutil.copy2(path, tampered_dir / path.name)
        with (tampered_dir / "transactions.dump").open("ab") as stream:
            stream.write(b"tampered")
        try:
            _verify_manifest(tampered_dir)
        except BackupValidationError:
            pass
        else:
            raise RuntimeError("Tampered backup was not rejected.")

    try:
        _require_test_database("bankcore_transactions", explicit_test_mode=True)
    except RestoreSafetyError:
        pass
    else:
        raise RuntimeError("Restore safety guard accepted a non-test database.")

    print(
        "Backup/restore verification passed: "
        f"auth_users={after_auth['user_count']}, "
        f"accounts={after_transactions['account_count']}, "
        f"ledger_transactions={after_transactions['ledger_transaction_count']}, "
        f"ledger_entries={after_transactions['ledger_entry_count']}, "
        f"idempotency_records={after_transactions['idempotency_record_count']}, "
        f"auth_revision={after_auth['alembic_version']}, "
        f"transactions_revision={after_transactions['alembic_version']}, "
        "tamper_rejected=true, unsafe_target_rejected=true, redis_source_of_truth=false"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=("scenario",))
    parser.add_argument("--artifacts", type=Path, default=Path("/artifacts"))
    args = parser.parse_args()
    asyncio.run(_scenario(args.artifacts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
