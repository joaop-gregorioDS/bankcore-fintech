"""At-least-once publisher for committed transactional outbox events."""

import argparse
import asyncio
import json
import logging
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import UUID

from aiokafka import AIOKafkaProducer
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.models import OutboxEvent
from common.observability import log_event, set_correlation_id
from common.tracing import configure_tracing, inject_trace_headers, tracer

logger = logging.getLogger("bankcore.outbox-publisher")
_tracer = tracer("bankcore.outbox-publisher")


SENSITIVE_ERROR = re.compile(
    r"(?i:(?P<authorization>authorization)\s*[:=]\s*(?:bearer\s+)?[^\s,;]+|"
    r"(?P<field>password|token|secret|api[_-]?key|private[_-]?key)\s*[:=]\s*[^\s,;]+)"
)
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]+")


@dataclass(frozen=True)
class ClaimedOutboxEvent:
    id: UUID
    payload: dict[str, Any]
    message_key: str


def sanitize_error(error: BaseException) -> str:
    """Keep retry diagnostics useful without persisting credentials or headers."""

    summary = f"{type(error).__name__}: {error}"
    summary = SENSITIVE_ERROR.sub(
        lambda match: f"{match.group('authorization') or match.group('field')}=<redacted>",
        summary,
    )
    summary = CONTROL_CHARS.sub(" ", summary).strip()
    return summary[:500]


class OutboxPublisher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
        producer_factory: Callable[..., AIOKafkaProducer] | None = None,
        publisher_id: str | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.producer_factory = producer_factory or self._default_producer
        self.publisher_id = publisher_id or settings.OUTBOX_PUBLISHER_ID or socket.gethostname()
        self.now = now or (lambda: datetime.now(timezone.utc))

    def _default_producer(self) -> AIOKafkaProducer:
        return AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            acks="all",
            enable_idempotence=True,
        )

    async def claim_pending(self) -> list[ClaimedOutboxEvent]:
        now = self.now()
        lease_until = now + timedelta(seconds=settings.OUTBOX_LEASE_SECONDS)
        async with self.session_factory() as session:
            statement = (
                select(OutboxEvent)
                .where(
                    OutboxEvent.published_at.is_(None),
                    or_(
                        OutboxEvent.locked_until.is_(None),
                        OutboxEvent.locked_until <= now,
                    ),
                )
                .order_by(OutboxEvent.occurred_at, OutboxEvent.id)
                .limit(settings.OUTBOX_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            rows = (await session.execute(statement)).scalars().all()
            if not rows:
                return []

            claimed = [
                ClaimedOutboxEvent(
                    id=row.id,
                    payload=dict(row.payload),
                    message_key=row.message_key,
                )
                for row in rows
            ]
            for row in rows:
                row.locked_by = self.publisher_id
                row.locked_until = lease_until
            await session.commit()
            for event in claimed:
                correlation_id = event.payload.get("correlation_id")
                if correlation_id:
                    set_correlation_id(str(correlation_id))
                log_event(
                    logger,
                    "outbox.event.claimed",
                    event_id=str(event.id),
                    transaction_id=str(event.payload.get("data", {}).get("transaction_id", "")),
                    attempt=int(next((row.attempts for row in rows if row.id == event.id), 0)),
                )
            return claimed

    async def mark_published(self, event_id: UUID) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(
                update(OutboxEvent)
                .where(
                    OutboxEvent.id == event_id,
                    OutboxEvent.published_at.is_(None),
                    OutboxEvent.locked_by == self.publisher_id,
                )
                .values(
                    published_at=self.now(),
                    locked_by=None,
                    locked_until=None,
                )
            )
            await session.commit()
            return result.rowcount == 1

    async def mark_failed(self, event_id: UUID, error: BaseException) -> None:
        async with self.session_factory() as session:
            await session.execute(
                update(OutboxEvent)
                .where(
                    OutboxEvent.id == event_id,
                    OutboxEvent.published_at.is_(None),
                    OutboxEvent.locked_by == self.publisher_id,
                )
                .values(
                    attempts=OutboxEvent.attempts + 1,
                    last_error=sanitize_error(error),
                    locked_by=None,
                    locked_until=None,
                )
            )
            await session.commit()

    async def _publish_one(
        self,
        producer: AIOKafkaProducer,
        event: ClaimedOutboxEvent,
    ) -> None:
        payload = json.dumps(
            event.payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        kafka_headers = {
            "x-event-id": str(event.payload.get("event_id", event.id)),
            "x-correlation-id": str(event.payload.get("correlation_id", "")),
        }
        with _tracer.start_as_current_span("kafka.produce transaction.completed.v1") as span:
            span.set_attribute("messaging.destination.name", settings.KAFKA_TOPIC)
            span.set_attribute("messaging.operation", "publish")
            inject_trace_headers(kafka_headers)
            await producer.send_and_wait(
                settings.KAFKA_TOPIC,
                key=event.message_key.encode("utf-8"),
                value=payload,
                headers=[(key, value.encode("ascii")) for key, value in kafka_headers.items()],
            )

    async def run_once(self, producer: AIOKafkaProducer | None = None) -> tuple[int, int]:
        events = await self.claim_pending()
        if not events:
            return 0, 0

        owns_producer = producer is None
        active_producer = producer or self.producer_factory()
        published = 0
        failed = 0
        producer_started = False
        try:
            if owns_producer:
                try:
                    await active_producer.start()
                    producer_started = True
                except Exception as error:
                    for event in events:
                        await self.mark_failed(event.id, error)
                    return 0, len(events)

            for event in events:
                try:
                    await self._publish_one(active_producer, event)
                    set_correlation_id(str(event.payload.get("correlation_id", "")))
                    log_event(
                        logger,
                        "outbox.event.publish.succeeded",
                        event_id=str(event.id),
                        transaction_id=str(event.payload.get("data", {}).get("transaction_id", "")),
                        topic=settings.KAFKA_TOPIC,
                    )
                    if settings.OUTBOX_CRASH_AFTER_KAFKA_ACK:
                        raise SystemExit(97)
                    if await self.mark_published(event.id):
                        published += 1
                except Exception as error:
                    failed += 1
                    set_correlation_id(str(event.payload.get("correlation_id", "")))
                    log_event(
                        logger,
                        "outbox.event.publish.failed",
                        level=logging.WARNING,
                        event_id=str(event.id),
                        transaction_id=str(event.payload.get("data", {}).get("transaction_id", "")),
                        topic=settings.KAFKA_TOPIC,
                        error_type=type(error).__name__,
                    )
                    await self.mark_failed(event.id, error)
        finally:
            if owns_producer and producer_started:
                await active_producer.stop()
        return published, failed

    async def run_forever(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL_SECONDS)


async def main() -> int:
    parser = argparse.ArgumentParser(description="BankCore transactional outbox publisher")
    parser.add_argument("--once", action="store_true", help="claim and publish one batch")
    args = parser.parse_args()
    from common.observability import configure_logging

    configure_logging("outbox-publisher")
    configure_tracing("outbox-publisher")
    publisher = OutboxPublisher()
    if args.once:
        await publisher.run_once()
    else:
        await publisher.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
