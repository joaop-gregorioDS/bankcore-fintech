"""Small disposable checks used by the P5 metrics runner."""

import asyncio
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from common.metrics import configure_metrics  # noqa: E402

BASE_URL = os.environ["E2E_BASE_URL"].rstrip("/")
KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
KAFKA_TOPIC = os.environ["KAFKA_TOPIC"]
RETRY_TOPIC = os.environ["KAFKA_RETRY_TOPIC"]

sys.path.insert(0, os.path.join(ROOT, "services", "audit-service"))
audit_database_url = os.environ["E2E_AUDIT_DATABASE_URL"]
if audit_database_url.startswith("postgresql://"):
    audit_database_url = audit_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
os.environ.setdefault("AUDIT_DATABASE_URL", audit_database_url)


def request(path: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8", errors="replace"))


def redis_fallback() -> None:
    suffix = str(time.time_ns())[-10:]
    tax_id = f"8{suffix}"
    status, _ = request(
        "/auth/register",
        {
            "tax_id": tax_id,
            "full_name": "BankCore P5 metrics",
            "email": f"p5-metrics-{uuid4()}@example.com",
            "password": "BankCoreP5Metrics!123",
        },
    )
    assert status == 201, status
    status, _ = request("/auth/login", {"tax_id": tax_id, "password": "wrong-password"})
    assert status == 401, status
    print("P5-D REDIS FALLBACK PASS")


class FailingSessionFactory:
    def __call__(self):
        return self

    async def __aenter__(self):
        raise RuntimeError("controlled transient audit database failure")

    async def __aexit__(self, *args):
        return False


class OffsetSpy:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


def transient_event() -> dict:
    transaction_id = str(uuid4())
    return {
        "event_id": str(uuid4()),
        "event_type": "transaction.completed",
        "event_version": 1,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "producer": "transactions-service",
        "correlation_id": str(uuid4()),
        "data": {
            "transaction_id": transaction_id,
            "source_account_id": str(uuid4()),
            "destination_account_id": str(uuid4()),
            "amount_cents": 1000,
            "operation_type": "PIX",
            "risk_assessment_id": str(uuid4()),
            "risk_rules_version": "risk-rules-v1",
        },
    }


async def kafka_retry() -> None:
    from audit_app.consumer import AuditConsumer

    configure_metrics("p5-metrics-transient-check")
    payload = transient_event()
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    record = SimpleNamespace(
        topic=KAFKA_TOPIC,
        partition=0,
        offset=0,
        key=payload["data"]["transaction_id"].encode("utf-8"),
        value=encoded,
        headers=[],
    )
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        acks="all",
        enable_idempotence=True,
    )
    retry_consumer = AIOKafkaConsumer(
        RETRY_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=f"p5-metrics-retry-check-{uuid4()}",
        auto_offset_reset="latest",
        enable_auto_commit=False,
    )
    await producer.start()
    await retry_consumer.start()
    try:
        result = await AuditConsumer(session_factory=FailingSessionFactory()).handle_record(
            record,
            OffsetSpy(),
            producer,
        )
        assert result == "retry", result
        deadline = time.monotonic() + 15
        found = False
        while time.monotonic() < deadline:
            try:
                retry_record = await asyncio.wait_for(retry_consumer.getone(), timeout=1)
            except asyncio.TimeoutError:
                continue
            if retry_record.value == encoded:
                found = True
                break
        assert found, "transient retry event was not published"
    finally:
        await retry_consumer.stop()
        await producer.stop()
    await asyncio.sleep(2)
    print("P5-D KAFKA TRANSIENT RETRY PASS")


if __name__ == "__main__":
    command = os.sys.argv[1] if len(os.sys.argv) > 1 else "redis-fallback"
    if command == "kafka-retry":
        asyncio.run(kafka_retry())
    elif command != "redis-fallback":
        raise SystemExit(f"Unknown command: {command}")
    else:
        redis_fallback()
