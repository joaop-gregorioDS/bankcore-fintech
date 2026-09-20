import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic


BASE_URL = os.environ["E2E_BASE_URL"].rstrip("/")
DATABASE_URL = os.environ["E2E_DATABASE_URL"]
RISK_DATABASE_URL = os.environ["E2E_RISK_DATABASE_URL"]
AUDIT_DATABASE_URL = os.environ["E2E_AUDIT_DATABASE_URL"]
KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
KAFKA_TOPIC = os.environ["KAFKA_TOPIC"]
RETRY_TOPIC = os.environ["KAFKA_RETRY_TOPIC"]
DLQ_TOPIC = os.environ["KAFKA_DLQ_TOPIC"]


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
        return error.code, json.loads(error.read().decode("utf-8", errors="replace"))


def register_user(suffix):
    unique = str(time.time_ns())[-10:]
    tax_id = f"9{unique}"
    status, body = request_json(
        "/auth/register",
        {
            "tax_id": tax_id,
            "full_name": f"BankCore P3-G {suffix}",
            "email": f"bankcore-p3g-{suffix}-{unique}@example.com",
            "password": "BankCoreP3G!123",
        },
    )
    assert status == 201, (status, body)
    return body["id"], tax_id


def login(tax_id):
    status, body = request_json(
        "/auth/login",
        {"tax_id": tax_id, "password": "BankCoreP3G!123"},
    )
    assert status == 200, (status, body)
    return body["access_token"]


def create_account(user_id, token):
    status, body = request_json("/accounts", {"user_id": user_id}, token)
    assert status == 201, (status, body)
    return body["id"]


async def connect(url):
    return await asyncpg.connect(url)


async def create_transfer(amount_reais="10.00", idempotency_key=None):
    source_user, source_tax_id = register_user("source")
    destination_user, destination_tax_id = register_user("destination")
    source_token = login(source_tax_id)
    destination_token = login(destination_tax_id)
    source_account = create_account(source_user, source_token)
    destination_account = create_account(destination_user, destination_token)
    connection = await connect(DATABASE_URL)
    try:
        await connection.execute(
            "UPDATE accounts SET balance_cents = 10000000 WHERE id = $1",
            UUID(source_account),
        )
    finally:
        await connection.close()

    key = idempotency_key or f"p3g-{uuid4()}"
    payload = {
        "source_account_id": source_account,
        "destination_key": destination_account,
        "amount_reais": amount_reais,
        "idempotency_key": key,
    }
    status, body = request_json("/transactions/pix", payload, source_token)
    assert status == 200, (status, body)
    assert body["status"] == "COMPLETED", body
    return body, source_token, payload


async def transaction_state(transaction_id):
    connection = await connect(DATABASE_URL)
    try:
        tx = await connection.fetchrow(
            """
            SELECT id, amount_cents, risk_assessment_id, risk_decision, risk_rules_version
            FROM ledger_transactions WHERE id = $1
            """,
            UUID(transaction_id),
        )
        entries = await connection.fetchval(
            "SELECT COUNT(*) FROM ledger_entries WHERE transaction_id = $1",
            UUID(transaction_id),
        )
        outbox = await connection.fetchrow(
            """
            SELECT id, published_at, payload, event_type, event_version
            FROM outbox_events WHERE aggregate_id = $1
            """,
            UUID(transaction_id),
        )
        balances = await connection.fetchrow(
            """
            SELECT COALESCE(SUM(CASE WHEN side = 'DEBIT' THEN amount_cents ELSE 0 END), 0) AS debits,
                   COALESCE(SUM(CASE WHEN side = 'CREDIT' THEN amount_cents ELSE 0 END), 0) AS credits
            FROM ledger_entries WHERE transaction_id = $1
            """,
            UUID(transaction_id),
        )
        return tx, entries, outbox, balances
    finally:
        await connection.close()


async def risk_count(transaction_id):
    connection = await connect(RISK_DATABASE_URL)
    try:
        return await connection.fetchval(
            "SELECT COUNT(*) FROM risk_assessments WHERE transaction_id = $1",
            UUID(transaction_id),
        )
    finally:
        await connection.close()


async def audit_count(transaction_id=None):
    connection = await connect(AUDIT_DATABASE_URL)
    try:
        if transaction_id:
            return await connection.fetchval(
                "SELECT COUNT(*) FROM audit_events WHERE transaction_id = $1",
                UUID(transaction_id),
            )
        return await connection.fetchval("SELECT COUNT(*) FROM audit_events")
    finally:
        await connection.close()


async def wait_for_recovery(transaction_id, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        tx, entries, outbox, balances = await transaction_state(transaction_id)
        if outbox and outbox["published_at"] is not None and await audit_count(transaction_id) == 1:
            assert tx["risk_assessment_id"] is not None
            assert tx["risk_decision"] == "APPROVED"
            assert tx["risk_rules_version"] == "risk-rules-v1"
            assert entries == 2
            assert balances["debits"] == balances["credits"] == tx["amount_cents"]
            assert await risk_count(transaction_id) == 1
            return
        await asyncio.sleep(0.5)
    tx, entries, outbox, balances = await transaction_state(transaction_id)
    raise AssertionError(
        f"Transaction {transaction_id} did not recover within {timeout}s: "
        f"tx={tx!r}, entries={entries}, outbox={outbox!r}, balances={balances!r}, "
        f"audit_count={await audit_count(transaction_id)}, risk_count={await risk_count(transaction_id)}"
    )


async def ensure_topics():
    admin = AIOKafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await admin.start()
    try:
        try:
            await admin.create_topics(
                [
                    NewTopic(KAFKA_TOPIC, num_partitions=3, replication_factor=1),
                    NewTopic(RETRY_TOPIC, num_partitions=3, replication_factor=1),
                    NewTopic(DLQ_TOPIC, num_partitions=3, replication_factor=1),
                ]
            )
        except Exception as error:
            if "TopicExists" not in str(error) and "already exists" not in str(error):
                raise
    finally:
        await admin.close()


async def happy():
    body, _, _ = await create_transfer()
    await wait_for_recovery(body["transaction_id"])
    print(f"P3-G HAPPY PASS transaction={body['transaction_id']}")


async def create_pending():
    body, _, _ = await create_transfer()
    tx, entries, outbox, _ = await transaction_state(body["transaction_id"])
    assert tx is not None and entries == 2 and outbox is not None
    assert outbox["published_at"] is None
    assert await audit_count(body["transaction_id"]) == 0
    print(f"P3-G PENDING PASS transaction={body['transaction_id']}")


async def create_published():
    body, _, _ = await create_transfer()
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        _, _, outbox, _ = await transaction_state(body["transaction_id"])
        if outbox and outbox["published_at"] is not None:
            assert await audit_count(body["transaction_id"]) == 0
            print(f"P3-G PUBLISHED-WAITING-AUDIT PASS transaction={body['transaction_id']}")
            return
        await asyncio.sleep(0.5)
    raise AssertionError("outbox event was not published while audit was stopped")


async def verify_recovery():
    connection = await connect(DATABASE_URL)
    try:
        transaction_id = await connection.fetchval(
            "SELECT id FROM ledger_transactions ORDER BY created_at DESC LIMIT 1"
        )
    finally:
        await connection.close()
    assert transaction_id is not None
    await wait_for_recovery(str(transaction_id))
    print(f"P3-G RECOVERY PASS transaction={transaction_id}")


async def idempotent_transfer():
    body, token, payload = await create_transfer(idempotency_key=f"p3g-idempotent-{uuid4()}")
    status, replay = request_json("/transactions/pix", payload, token)
    assert status == 200 and replay["transaction_id"] == body["transaction_id"]
    await wait_for_recovery(body["transaction_id"])
    connection = await connect(DATABASE_URL)
    try:
        ledger_count = await connection.fetchval(
            "SELECT COUNT(*) FROM ledger_transactions WHERE id = $1", UUID(body["transaction_id"])
        )
        outbox_count = await connection.fetchval(
            "SELECT COUNT(*) FROM outbox_events WHERE aggregate_id = $1", UUID(body["transaction_id"])
        )
    finally:
        await connection.close()
    assert ledger_count == outbox_count == 1
    print("P3-G IDEMPOTENCY PASS: one ledger, one outbox, one audit effect")


async def risk_rejected():
    connection = await connect(DATABASE_URL)
    try:
        before_ledger = await connection.fetchval("SELECT COUNT(*) FROM ledger_transactions")
        before_outbox = await connection.fetchval("SELECT COUNT(*) FROM outbox_events")
    finally:
        await connection.close()
    source_user, source_tax_id = register_user("rejected-source")
    destination_user, destination_tax_id = register_user("rejected-destination")
    source_token = login(source_tax_id)
    destination_token = login(destination_tax_id)
    source_account = create_account(source_user, source_token)
    destination_account = create_account(destination_user, destination_token)
    connection = await connect(DATABASE_URL)
    try:
        await connection.execute(
            "UPDATE accounts SET balance_cents = 10000000 WHERE id = $1", UUID(source_account)
        )
    finally:
        await connection.close()
    status, _ = request_json(
        "/transactions/pix",
        {
            "source_account_id": source_account,
            "destination_key": destination_account,
            "amount_reais": "10001.00",
            "idempotency_key": f"p3g-rejected-{uuid4()}",
        },
        source_token,
    )
    assert status == 422, status
    connection = await connect(DATABASE_URL)
    try:
        after_ledger = await connection.fetchval("SELECT COUNT(*) FROM ledger_transactions")
        after_outbox = await connection.fetchval("SELECT COUNT(*) FROM outbox_events")
    finally:
        await connection.close()
    assert before_ledger == after_ledger
    assert before_outbox == after_outbox
    print("P3-G RISK REJECTION PASS: zero ledger and outbox effects")


async def send_poison():
    poison = b'{"event_id":"poison","event_type":"transaction.completed"}'
    valid = {
        "event_id": str(uuid4()),
        "event_type": "transaction.completed",
        "event_version": 1,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "producer": "transactions-service",
        "correlation_id": str(uuid4()),
        "data": {
            "transaction_id": str(uuid4()),
            "source_account_id": str(uuid4()),
            "destination_account_id": str(uuid4()),
            "amount_cents": 1,
            "operation_type": "PIX",
            "risk_assessment_id": str(uuid4()),
            "risk_rules_version": "risk-rules-v1",
        },
    }
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, acks="all")
    await producer.start()
    try:
        await producer.send_and_wait(KAFKA_TOPIC, key=b"poison", value=poison)
        await producer.send_and_wait(
            KAFKA_TOPIC,
            key=valid["data"]["transaction_id"].encode(),
            value=json.dumps(valid, sort_keys=True).encode(),
        )
    finally:
        await producer.stop()

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if await audit_count(valid["data"]["transaction_id"]) == 1:
            break
        await asyncio.sleep(0.5)
    assert await audit_count(valid["data"]["transaction_id"]) == 1

    consumer = AIOKafkaConsumer(
        DLQ_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=f"p3g-dlq-check-{uuid4()}",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    try:
        found = False
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                record = await asyncio.wait_for(consumer.getone(), timeout=1)
            except asyncio.TimeoutError:
                continue
            if record.value == poison:
                found = True
                break
        assert found, "poison event was not found in DLQ"
    finally:
        await consumer.stop()
    print("P3-G POISON PASS: invalid event in DLQ, following valid event audited")


async def main():
    command = os.sys.argv[1] if len(os.sys.argv) > 1 else "happy"
    commands = {
        "ensure-topics": ensure_topics,
        "happy": happy,
        "create-pending": create_pending,
        "create-published": create_published,
        "verify-recovery": verify_recovery,
        "idempotency": idempotent_transfer,
        "risk-rejected": risk_rejected,
        "poison": send_poison,
    }
    if command not in commands:
        raise SystemExit(f"Unknown P3-G command: {command}")
    await commands[command]()


if __name__ == "__main__":
    asyncio.run(main())
