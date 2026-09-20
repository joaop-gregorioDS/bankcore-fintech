import argparse
import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable

from aiokafka import AIOKafkaConsumer
from aiokafka import AIOKafkaProducer
from sqlalchemy.dialects.postgresql import insert

from audit_app.config import settings
from audit_app.contracts import InvalidAuditEvent, validate_transaction_completed
from audit_app.database import AuditSessionLocal, engine
from audit_app.models import AuditEvent


logger = logging.getLogger("bankcore.audit-consumer")

RETRY_COUNT_HEADER = "retry-count"
ORIGINAL_TOPIC_HEADER = "original-topic"
ORIGINAL_PARTITION_HEADER = "original-partition"
ORIGINAL_OFFSET_HEADER = "original-offset"
FAILURE_CLASS_HEADER = "failure-class"
FAILURE_REASON_HEADER = "failure-reason"
FAILED_AT_HEADER = "failed-at"
TRANSIENT = "TRANSIENT"
PERMANENT = "PERMANENT"
SENSITIVE_ERROR = re.compile(
    r"(?i:(?P<authorization>authorization)\s*[:=]\s*(?:bearer\s+)?[^\s,;]+|"
    r"(?P<field>password|token|secret|api[_-]?key|private[_-]?key|connection[_-]?string)"
    r"\s*[:=]\s*[^\s,;]+)"
)
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]+")


def sanitize_failure_reason(error: BaseException) -> str:
    reason = SENSITIVE_ERROR.sub(
        lambda match: f"{match.group('authorization') or match.group('field')}=<redacted>",
        f"{type(error).__name__}: {error}",
    )
    return CONTROL_CHARS.sub(" ", reason).strip()[:512]


def _header_value(record: Any, name: str) -> str | None:
    for key, value in reversed(getattr(record, "headers", None) or []):
        if key == name:
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
    return None


def _header_int(record: Any, name: str, default: int = 0) -> int:
    value = _header_value(record, name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class AuditConsumer:
    def __init__(
        self,
        session_factory: Callable = AuditSessionLocal,
        consumer_factory: Callable[..., AIOKafkaConsumer] | None = None,
        group_id: str | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.consumer_factory = consumer_factory or AIOKafkaConsumer
        self.group_id = group_id or settings.KAFKA_GROUP_ID

    async def persist(self, event: Any) -> None:
        async with self.session_factory() as session:
            statement = insert(AuditEvent).values(
                event_id=event.event_id,
                event_type=event.event_type,
                event_version=event.event_version,
                transaction_id=event.data.transaction_id,
                payload=event.model_dump(mode="json"),
                occurred_at=event.occurred_at,
                consumer_version=settings.CONSUMER_VERSION,
            ).on_conflict_do_nothing(index_elements=[AuditEvent.event_id])
            await session.execute(statement)
            await session.commit()

    async def process_record(self, record: Any, kafka_consumer: Any = None) -> Any:
        payload = record.value
        if isinstance(payload, bytes):
            try:
                payload = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise InvalidAuditEvent("Invalid JSON audit event") from error
        event = validate_transaction_completed(payload)
        record_key = getattr(record, "key", None)
        if record_key is not None:
            try:
                message_key = record_key.decode("utf-8")
            except UnicodeDecodeError as error:
                raise InvalidAuditEvent("Invalid Kafka message key") from error
            if message_key != str(event.data.transaction_id):
                raise InvalidAuditEvent("Kafka message key does not match transaction_id")
        await self.persist(event)
        if settings.CRASH_AFTER_DB_COMMIT:
            raise SystemExit(97)
        if kafka_consumer is not None:
            await kafka_consumer.commit()
        return event

    def create_consumer(self) -> AIOKafkaConsumer:
        return self.create_topic_consumer(settings.KAFKA_TOPIC, self.group_id)

    def create_topic_consumer(self, topic: str, group_id: str) -> AIOKafkaConsumer:
        return self.consumer_factory(
            topic,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )

    def create_producer(self) -> AIOKafkaProducer:
        return AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            acks="all",
            enable_idempotence=True,
        )

    def _failure_headers(self, record: Any, failure_class: str, error: BaseException) -> list[tuple[str, bytes]]:
        original_topic = _header_value(record, ORIGINAL_TOPIC_HEADER) or getattr(
            record, "topic", settings.KAFKA_TOPIC
        )
        original_partition = _header_value(record, ORIGINAL_PARTITION_HEADER) or str(
            getattr(record, "partition", -1)
        )
        original_offset = _header_value(record, ORIGINAL_OFFSET_HEADER) or str(
            getattr(record, "offset", -1)
        )
        return [
            (RETRY_COUNT_HEADER, str(_header_int(record, RETRY_COUNT_HEADER)).encode("ascii")),
            (ORIGINAL_TOPIC_HEADER, original_topic.encode("utf-8")),
            (ORIGINAL_PARTITION_HEADER, original_partition.encode("ascii")),
            (ORIGINAL_OFFSET_HEADER, original_offset.encode("ascii")),
            (FAILURE_CLASS_HEADER, failure_class.encode("ascii")),
            (FAILURE_REASON_HEADER, sanitize_failure_reason(error).encode("utf-8")),
            (FAILED_AT_HEADER, datetime.now(timezone.utc).isoformat().encode("ascii")),
        ]

    async def publish_failure(
        self,
        producer: AIOKafkaProducer,
        record: Any,
        topic: str,
        failure_class: str,
        error: BaseException,
        retry_count: int,
    ) -> None:
        headers = self._failure_headers(record, failure_class, error)
        headers = [
            (RETRY_COUNT_HEADER, str(retry_count).encode("ascii")) if key == RETRY_COUNT_HEADER else (key, value)
            for key, value in headers
        ]
        await producer.send_and_wait(
            topic,
            key=getattr(record, "key", None),
            value=record.value if isinstance(record.value, bytes) else json.dumps(record.value).encode("utf-8"),
            headers=headers,
        )

    async def handle_record(
        self,
        record: Any,
        kafka_consumer: Any,
        producer: AIOKafkaProducer,
    ) -> str:
        retry_count = _header_int(record, RETRY_COUNT_HEADER)
        last_error: BaseException | None = None
        for attempt in range(settings.LOCAL_RETRY_ATTEMPTS + 1):
            try:
                await self.process_record(record)
                await kafka_consumer.commit()
                return "processed"
            except InvalidAuditEvent as error:
                await self.publish_failure(
                    producer,
                    record,
                    settings.KAFKA_DLQ_TOPIC,
                    PERMANENT,
                    error,
                    retry_count,
                )
                await kafka_consumer.commit()
                return "dlq"
            except Exception as error:
                last_error = error
                if attempt < settings.LOCAL_RETRY_ATTEMPTS:
                    await asyncio.sleep(settings.LOCAL_RETRY_DELAY_SECONDS)

        assert last_error is not None
        if retry_count < settings.MAX_RETRIES:
            await self.publish_failure(
                producer,
                record,
                settings.KAFKA_RETRY_TOPIC,
                TRANSIENT,
                last_error,
                retry_count + 1,
            )
            await kafka_consumer.commit()
            return "retry"

        await self.publish_failure(
            producer,
            record,
            settings.KAFKA_DLQ_TOPIC,
            TRANSIENT,
            last_error,
            retry_count,
        )
        await kafka_consumer.commit()
        return "dlq"

    async def _consume_loop(
        self,
        consumer: AIOKafkaConsumer,
        producer: AIOKafkaProducer,
    ) -> None:
        async for record in consumer:
            await self.handle_record(record, consumer, producer)

    async def run_once(self) -> Any:
        consumer = self.create_consumer()
        producer = self.create_producer()
        await consumer.start()
        await producer.start()
        try:
            record = await consumer.getone()
            return await self.handle_record(record, consumer, producer)
        finally:
            await consumer.stop()
            await producer.stop()

    async def run_forever(self) -> None:
        source_consumer = self.create_topic_consumer(settings.KAFKA_TOPIC, self.group_id)
        retry_consumer = self.create_topic_consumer(
            settings.KAFKA_RETRY_TOPIC,
            settings.KAFKA_RETRY_GROUP_ID,
        )
        producer = self.create_producer()
        await source_consumer.start()
        await retry_consumer.start()
        await producer.start()
        try:
            await asyncio.gather(
                self._consume_loop(source_consumer, producer),
                self._consume_loop(retry_consumer, producer),
            )
        finally:
            await source_consumer.stop()
            await retry_consumer.stop()
            await producer.stop()


async def main() -> int:
    parser = argparse.ArgumentParser(description="BankCore idempotent audit consumer")
    parser.add_argument("--once", action="store_true", help="process one Kafka record")
    args = parser.parse_args()
    consumer = AuditConsumer()
    if args.once:
        await consumer.run_once()
    else:
        await consumer.run_forever()
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(asyncio.run(main()))
