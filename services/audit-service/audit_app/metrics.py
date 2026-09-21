import time

from common.metrics import meter

_meter = meter("bankcore.audit")

events_received = _meter.create_counter("bankcore_audit_events_received", unit="{event}")
events_persisted = _meter.create_counter("bankcore_audit_events_persisted", unit="{event}")
processing_results = _meter.create_counter("bankcore_audit_processing_results", unit="{event}")
processing_duration = _meter.create_histogram("bankcore_audit_processing_duration_seconds", unit="s")
kafka_retries = _meter.create_counter("bankcore_kafka_retries", unit="{retry}")
kafka_dlq = _meter.create_counter("bankcore_kafka_dlq", unit="{event}")

# Register bounded zero-valued series so "no events yet" is distinguishable
# from a missing instrument without inventing high-cardinality labels.
events_received.add(0, {"topic": "transaction.completed.v1"})
events_persisted.add(0, {"outcome": "inserted"})
events_persisted.add(0, {"outcome": "duplicate"})
processing_results.add(0, {"outcome": "processed"})
kafka_retries.add(0, {"failure_class": "transient"})
kafka_dlq.add(0, {"failure_class": "transient"})


def started() -> float:
    return time.perf_counter()


def finished(started_at: float, outcome: str) -> None:
    processing_results.add(1, {"outcome": outcome})
    processing_duration.record(time.perf_counter() - started_at, {"outcome": outcome})
