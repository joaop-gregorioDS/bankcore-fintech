import argparse
import asyncio
import json
import logging
from typing import Any, Callable

from aiokafka import AIOKafkaConsumer
from sqlalchemy.dialects.postgresql import insert

from audit_app.config import settings
from audit_app.contracts import InvalidAuditEvent, validate_transaction_completed
from audit_app.database import AuditSessionLocal, engine
from audit_app.models import AuditEvent


logger = logging.getLogger("bankcore.audit-consumer")


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
        if kafka_consumer is not None:
            await kafka_consumer.commit()
        return event

    def create_consumer(self) -> AIOKafkaConsumer:
        return self.consumer_factory(
            settings.KAFKA_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=self.group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )

    async def run_once(self) -> Any:
        consumer = self.create_consumer()
        await consumer.start()
        try:
            record = await consumer.getone()
            return await self.process_record(record, consumer)
        finally:
            await consumer.stop()

    async def run_forever(self) -> None:
        consumer = self.create_consumer()
        await consumer.start()
        try:
            async for record in consumer:
                await self.process_record(record, consumer)
        finally:
            await consumer.stop()


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
