"""Fail-open OpenTelemetry tracing helpers for BankCore services."""

from __future__ import annotations

import os
from collections.abc import MutableMapping
from typing import Any

from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


_TRACER_NAME = "bankcore"
_provider: TracerProvider | None = None


def configure_tracing(service_name: str) -> trace.Tracer:
    """Configure W3C tracing only when an OTLP endpoint is explicitly enabled.

    With no endpoint, the OpenTelemetry API remains a no-op. This avoids
    background connection attempts and guarantees that telemetry cannot affect
    request, ledger, Kafka, or audit availability in the normal stack.
    """

    global _TRACER_NAME, _provider
    _TRACER_NAME = service_name
    endpoint = (
        os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    )
    disabled = os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true"
    if not endpoint or disabled:
        return trace.get_tracer(service_name)

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=endpoint,
        insecure=os.getenv("OTEL_EXPORTER_OTLP_TRACES_INSECURE", "true").lower() == "true",
        timeout=int(os.getenv("OTEL_EXPORTER_OTLP_TIMEOUT", "1000")),
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            exporter,
            max_queue_size=2048,
            max_export_batch_size=128,
            schedule_delay_millis=500,
            export_timeout_millis=1000,
        )
    )
    trace.set_tracer_provider(provider)
    _provider = provider
    return trace.get_tracer(service_name)


def instrument_fastapi(app: Any, service_name: str) -> None:
    """Add HTTP server spans; route/body attributes remain library-controlled."""

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace.get_tracer_provider(),
        excluded_urls="health|readiness",
    )


def tracer(name: str | None = None) -> trace.Tracer:
    return trace.get_tracer(name or _TRACER_NAME)


def inject_trace_headers(headers: MutableMapping[str, str]) -> MutableMapping[str, str]:
    """Inject only W3C trace context into an existing outbound header map."""

    propagate.inject(headers)
    return headers


def extract_trace_context(headers: MutableMapping[str, str]) -> Any:
    """Extract W3C context from HTTP/Kafka-like string headers."""

    return propagate.extract(headers)


def current_trace_fields() -> dict[str, str]:
    span = trace.get_current_span()
    context = span.get_span_context()
    if not context.is_valid:
        return {}
    return {
        "trace_id": format(context.trace_id, "032x"),
        "span_id": format(context.span_id, "016x"),
    }
