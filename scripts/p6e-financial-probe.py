"""Financial acceptance probe executed inside the production bundle network.

The probe deliberately uses only the public gateway for business operations and
the internal PostgreSQL service names for controlled acceptance assertions. It
does not publish database ports or print financial identifiers.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from uuid import UUID, uuid4

import asyncpg


BASE_URL = os.environ["E2E_BASE_URL"].rstrip("/")
DATABASE_URL = os.environ["E2E_DATABASE_URL"]
RISK_DATABASE_URL = os.environ["E2E_RISK_DATABASE_URL"]
AUDIT_DATABASE_URL = os.environ["E2E_AUDIT_DATABASE_URL"]


def request_json(path: str, payload: dict[str, object] | None = None, token: str | None = None):
    deadline = time.monotonic() + 45
    while True:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{BASE_URL}{path}",
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
            method="POST" if payload is not None else "GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code not in {502, 503, 504} or time.monotonic() >= deadline:
                detail = error.read().decode("utf-8", errors="replace")
                raise AssertionError(f"gateway request {path} returned HTTP {error.code}: {detail}") from error
        except urllib.error.URLError:
            if time.monotonic() >= deadline:
                raise
        time.sleep(0.5)


def register_user(role: str) -> tuple[str, str]:
    unique = str(time.time_ns())[-10:]
    tax_id = f"9{unique}"
    status, body = request_json(
        "/auth/register",
        {
            "tax_id": tax_id,
            "full_name": f"BankCore P6-E {role}",
            "email": f"bankcore-p6e-{role}-{unique}@example.com",
            "password": "BankCoreP6E!123",
        },
    )
    assert status == 201, status
    return str(body["id"]), tax_id


def login(tax_id: str) -> str:
    status, body = request_json("/auth/login", {"tax_id": tax_id, "password": "BankCoreP6E!123"})
    assert status == 200, status
    return str(body["access_token"])


def create_account(user_id: str, token: str) -> str:
    status, body = request_json("/accounts", {"user_id": user_id}, token)
    assert status == 201, status
    return str(body["id"])


async def db(url: str):
    return await asyncpg.connect(url)


async def snapshot_database(url: str) -> dict[str, object]:
    connection = await db(url)
    try:
        accounts = await connection.fetch(
            """
            SELECT id::text, user_id::text, balance_cents, is_active
            FROM accounts ORDER BY id
            """
        )
        transactions = await connection.fetch(
            """
            SELECT id::text, idempotency_key, source_account_id::text,
                   destination_account_id::text, amount_cents, transaction_type,
                   status, risk_assessment_id::text, risk_decision,
                   risk_rules_version
            FROM ledger_transactions ORDER BY id
            """
        )
        entries = await connection.fetch(
            """
            SELECT id::text, transaction_id::text, account_id::text, side, amount_cents
            FROM ledger_entries ORDER BY id
            """
        )
        idempotency = await connection.fetch(
            """
            SELECT id::text, idempotency_key, user_id::text, account_id::text,
                   operation_type, request_fingerprint, transaction_id::text, status
            FROM idempotency_records ORDER BY id
            """
        )
        outbox = await connection.fetch(
            """
            SELECT id::text, aggregate_type, aggregate_id::text, event_type,
                   event_version, message_key, published_at IS NOT NULL AS published,
                   attempts, locked_by, locked_until IS NOT NULL AS locked
            FROM outbox_events ORDER BY id
            """
        )
        return {
            "accounts": [dict(row) for row in accounts],
            "transactions": [dict(row) for row in transactions],
            "entries": [dict(row) for row in entries],
            "idempotency": [dict(row) for row in idempotency],
            "outbox": [dict(row) for row in outbox],
        }
    finally:
        await connection.close()


async def snapshot_audit(url: str) -> list[dict[str, object]]:
    connection = await db(url)
    try:
        rows = await connection.fetch(
            """
            SELECT id::text, event_id::text, event_type, event_version,
                   transaction_id::text, consumer_version
            FROM audit_events ORDER BY id
            """
        )
        return [dict(row) for row in rows]
    finally:
        await connection.close()


def json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


async def financial_snapshot() -> None:
    payload = {
        "transactions": await snapshot_database(DATABASE_URL),
        "audit": await snapshot_audit(AUDIT_DATABASE_URL),
    }
    canonical = json.dumps(json_safe(payload), sort_keys=True, separators=(",", ":"), default=str)
    print(hashlib.sha256(canonical.encode("utf-8")).hexdigest())


async def wait_for_audit(transaction_id: UUID, timeout: float = 45) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        connection = await db(AUDIT_DATABASE_URL)
        try:
            count = await connection.fetchval(
                "SELECT COUNT(*) FROM audit_events WHERE transaction_id = $1", transaction_id
            )
        finally:
            await connection.close()
        if count == 1:
            return
        await asyncio.sleep(0.5)
    raise AssertionError("audit event was not persisted before the acceptance timeout")


async def financial_smoke() -> None:
    source_user, source_tax_id = register_user("source")
    destination_user, destination_tax_id = register_user("destination")
    source_token = login(source_tax_id)
    destination_token = login(destination_tax_id)
    source_account = create_account(source_user, source_token)
    destination_account = create_account(destination_user, destination_token)
    idempotency_key = f"p6e-{uuid4()}"
    amount_cents = 1000

    connection = await db(DATABASE_URL)
    try:
        await connection.execute(
            "UPDATE accounts SET balance_cents = 10000000 WHERE id = $1",
            UUID(source_account),
        )
    finally:
        await connection.close()

    status, body = request_json(
        "/transactions/pix",
        {
            "source_account_id": source_account,
            "destination_key": destination_account,
            "amount_reais": "10.00",
            "idempotency_key": idempotency_key,
        },
        source_token,
    )
    assert status == 200 and body.get("status") == "COMPLETED", status
    transaction_id = UUID(str(body["transaction_id"]))

    connection = await db(DATABASE_URL)
    try:
        transaction = await connection.fetchrow(
            """
            SELECT amount_cents, risk_assessment_id, risk_decision, risk_rules_version
            FROM ledger_transactions WHERE id = $1
            """,
            transaction_id,
        )
        assert transaction and transaction["amount_cents"] == amount_cents
        assert transaction["risk_assessment_id"] is not None
        assert transaction["risk_decision"] == "APPROVED"
        assert transaction["risk_rules_version"] == "risk-rules-v1"
        entries = await connection.fetch(
            "SELECT side, amount_cents FROM ledger_entries WHERE transaction_id = $1 ORDER BY side",
            transaction_id,
        )
        assert len(entries) == 2
        assert {row["side"] for row in entries} == {"DEBIT", "CREDIT"}
        assert {row["amount_cents"] for row in entries} == {amount_cents}
        idempotency = await connection.fetchrow(
            """
            SELECT transaction_id, status FROM idempotency_records
            WHERE idempotency_key = $1
            """,
            idempotency_key,
        )
        assert idempotency and idempotency["transaction_id"] == transaction_id
        assert idempotency["status"] == "COMPLETED"
        outbox = await connection.fetchrow(
            """
            SELECT event_type, event_version, published_at
            FROM outbox_events WHERE aggregate_id = $1
            """,
            transaction_id,
        )
        assert outbox and outbox["event_type"] == "transaction.completed"
        assert outbox["event_version"] == 1
    finally:
        await connection.close()

    risk_connection = await db(RISK_DATABASE_URL)
    try:
        assert await risk_connection.fetchval(
            "SELECT COUNT(*) FROM risk_assessments WHERE transaction_id = $1", transaction_id
        ) == 1
    finally:
        await risk_connection.close()

    await wait_for_audit(transaction_id)
    connection = await db(DATABASE_URL)
    try:
        balances = await connection.fetch(
            "SELECT id::text, balance_cents FROM accounts WHERE id = ANY($1::uuid[]) ORDER BY id",
            [UUID(source_account), UUID(destination_account)],
        )
        balance_values = {row["id"]: row["balance_cents"] for row in balances}
        assert balance_values[UUID(source_account).__str__()] == 10000000 - amount_cents
        assert balance_values[UUID(destination_account).__str__()] == amount_cents
    finally:
        await connection.close()

    print("P6E FINANCIAL SMOKE PASS: PIX, Risk, double-entry ledger, idempotency, outbox and Audit")


async def main() -> None:
    mode = os.environ.get("P6E_PROBE_MODE", "smoke")
    if mode == "snapshot":
        await financial_snapshot()
    elif mode == "smoke":
        await financial_smoke()
    else:
        raise SystemExit(f"unsupported P6E probe mode: {mode}")


if __name__ == "__main__":
    asyncio.run(main())
