"""Fail-open OpenTelemetry metrics helpers for BankCore services."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from typing import Any

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
try:
    from starlette.middleware.base import BaseHTTPMiddleware as _BaseHTTPMiddleware
except ImportError:  # Audit/publisher images do not need the HTTP middleware.
    _BaseHTTPMiddleware = object


_provider: MeterProvider | None = None


def configure_metrics(service_name: str) -> None:
    """Enable OTLP metrics only when explicitly configured.

    The application remains fully functional without a collector. Export errors
    are handled by the SDK's background reader and never sit on the financial
    request path.
    """

    global _provider
    endpoint = (
        os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    )
    disabled = os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true"
    if _provider is not None or not endpoint or disabled:
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
        }
    )
    exporter = OTLPMetricExporter(
        endpoint=endpoint,
        insecure=os.getenv("OTEL_EXPORTER_OTLP_METRICS_INSECURE", "true").lower() == "true",
        timeout=int(os.getenv("OTEL_EXPORTER_OTLP_TIMEOUT", "1000")),
    )
    reader = PeriodicExportingMetricReader(
        exporter,
        export_interval_millis=int(os.getenv("OTEL_METRIC_EXPORT_INTERVAL_MS", "1000")),
        export_timeout_millis=1000,
    )
    _provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(_provider)


def meter(name: str):
    return metrics.get_meter(name)


def observable_gauge(
    meter_instance: Any,
    name: str,
    callback: Callable[[CallbackOptions], Iterable[Observation]],
    *,
    unit: str = "1",
    description: str = "",
):
    return meter_instance.create_observable_gauge(
        name,
        callbacks=[callback],
        unit=unit,
        description=description,
    )


class HttpMetricsMiddleware(_BaseHTTPMiddleware):
    """Small bounded-cardinality HTTP request metric middleware."""

    def __init__(self, app: Any, service_name: str) -> None:
        if _BaseHTTPMiddleware is object:
            raise RuntimeError("HTTP metrics middleware requires Starlette")
        super().__init__(app)
        meter_instance = meter(service_name)
        self._requests = meter_instance.create_counter(
            f"bankcore_{service_name.replace('-', '_')}_http_requests",
            unit="{request}",
            description="Completed HTTP requests by method, route and status class.",
        )
        self._duration = meter_instance.create_histogram(
            f"bankcore_{service_name.replace('-', '_')}_http_duration_seconds",
            unit="s",
            description="HTTP request duration in seconds.",
        )

    async def dispatch(self, request: Any, call_next: Any) -> Any:
        import time

        started = time.perf_counter()
        status_class = "5xx"
        try:
            response = await call_next(request)
            status_class = f"{response.status_code // 100}xx"
            return response
        finally:
            route = request.scope.get("route")
            route_template = getattr(route, "path", None) or "unmatched"
            if len(route_template) > 128:
                route_template = "unmatched"
            attributes = {
                "http.request.method": request.method,
                "http.route": route_template,
                "http.response.status_class": status_class,
            }
            self._requests.add(1, attributes)
            self._duration.record(time.perf_counter() - started, attributes)
