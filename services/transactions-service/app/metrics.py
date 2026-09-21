from opentelemetry.metrics import Observation

from common.metrics import meter

_meter = meter("bankcore.transactions")

operation_results = _meter.create_counter("bankcore_transactions_operations", unit="{operation}")
risk_requests = _meter.create_counter("bankcore_transactions_risk_requests", unit="{request}")
risk_duration = _meter.create_histogram("bankcore_transactions_risk_duration_seconds", unit="s")
ledger_commits = _meter.create_counter("bankcore_transactions_ledger_commits", unit="{commit}")
outbox_events_created = _meter.create_counter("bankcore_transactions_outbox_events_created", unit="{event}")
outbox_published = _meter.create_counter("bankcore_outbox_publish", unit="{event}")
outbox_publish_duration = _meter.create_histogram("bankcore_outbox_publish_duration_seconds", unit="s")

_outbox_state = {"pending": 0, "oldest_age_seconds": 0.0}


def set_outbox_state(pending: int, oldest_age_seconds: float) -> None:
    _outbox_state["pending"] = max(0, pending)
    _outbox_state["oldest_age_seconds"] = max(0.0, oldest_age_seconds)


_meter.create_observable_gauge(
    "bankcore_outbox_pending",
    callbacks=[lambda options: [Observation(_outbox_state["pending"], {})]],
    unit="{event}",
)
_meter.create_observable_gauge(
    "bankcore_outbox_oldest_age_seconds",
    callbacks=[lambda options: [Observation(_outbox_state["oldest_age_seconds"], {})]],
    unit="s",
)
