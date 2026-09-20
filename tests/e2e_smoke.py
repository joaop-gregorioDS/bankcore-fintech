import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from uuid import UUID

import asyncpg


BASE_URL = os.environ["E2E_BASE_URL"].rstrip("/")
DATABASE_URL = os.environ["E2E_DATABASE_URL"]
RISK_DATABASE_URL = os.environ["E2E_RISK_DATABASE_URL"]


def request_json(path, payload=None, token=None):
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
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise AssertionError(f"E2E request {path} returned HTTP {error.code}: {detail}") from error


def register_user(suffix):
    unique = str(time.time_ns())[-10:]
    tax_id = f"9{unique}"
    status, body = request_json(
        "/auth/register",
        {
            "tax_id": tax_id,
            "full_name": f"BankCore E2E {suffix}",
            "email": f"bankcore-e2e-{suffix}-{unique}@example.com",
            "password": "BankCoreE2E!123",
        },
    )
    assert status == 201
    return body["id"], tax_id


def login(tax_id):
    status, body = request_json(
        "/auth/login",
        {"tax_id": tax_id, "password": "BankCoreE2E!123"},
    )
    assert status == 200
    return body["access_token"]


def create_account(user_id, token):
    status, body = request_json("/accounts", {"user_id": user_id}, token)
    assert status == 201
    return body["id"]


async def validate_persistence(transaction_id):
    connection = await asyncpg.connect(DATABASE_URL)
    try:
        transaction = await connection.fetchrow(
            """
            SELECT risk_assessment_id, risk_decision, risk_rules_version
            FROM ledger_transactions
            WHERE id = $1
            """,
            UUID(transaction_id),
        )
        assert transaction is not None
        assert transaction["risk_assessment_id"] is not None
        assert transaction["risk_decision"] == "APPROVED"
        assert transaction["risk_rules_version"] == "risk-rules-v1"

        entries = await connection.fetchval(
            "SELECT COUNT(*) FROM ledger_entries WHERE transaction_id = $1",
            UUID(transaction_id),
        )
        assert entries == 2

        risk_connection = await asyncpg.connect(RISK_DATABASE_URL)
        try:
            assessments = await risk_connection.fetchval(
                "SELECT COUNT(*) FROM risk_assessments WHERE transaction_id = $1",
                UUID(transaction_id),
            )
        finally:
            await risk_connection.close()
        assert assessments == 1
    finally:
        await connection.close()


async def fund_source_account(account_id):
    connection = await asyncpg.connect(DATABASE_URL)
    try:
        await connection.execute(
            "UPDATE accounts SET balance_cents = 10000 WHERE id = $1",
            UUID(account_id),
        )
    finally:
        await connection.close()


async def main_async():
    source_user, source_tax_id = register_user("source")
    destination_user, destination_tax_id = register_user("destination")
    source_token = login(source_tax_id)
    destination_token = login(destination_tax_id)
    source_account = create_account(source_user, source_token)
    destination_account = create_account(destination_user, destination_token)

    await fund_source_account(source_account)

    status, result = request_json(
        "/transactions/pix",
        {
            "source_account_id": source_account,
            "destination_key": destination_account,
            "amount_reais": "10.00",
            "idempotency_key": f"e2e-{time.time_ns()}",
        },
        source_token,
    )
    assert status == 200
    assert result["status"] == "COMPLETED"
    await validate_persistence(result["transaction_id"])
    print("E2E PASS: Auth -> Nginx -> Transactions -> Risk -> PostgreSQL -> Ledger")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
