"""Small, dependency-free observability primitives shared by Python services.

This module deliberately keeps the P5-B contract limited to structured logs and
business/request correlation. OpenTelemetry trace context belongs to P5-C.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import uuid4


_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SENSITIVE_FIELD = re.compile(
    r"(?i)(authorization|bearer|password|passwd|secret|token|api[_-]?key|"
    r"private[_-]?key|connection[_-]?string|cpf|cnpj|pix[_-]?key|email)"
)

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "bankcore_request_id", default=None
)
_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "bankcore_correlation_id", default=None
)

_SERVICE_NAME = "bankcore"
_ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

_ALLOWED_FIELDS = {
    "request_id",
    "correlation_id",
    "transaction_id",
    "event_id",
    "risk_assessment_id",
    "duration_ms",
    "status",
    "attempt",
    "decision",
    "rules_version",
    "operation_type",
    "dependency",
    "retry_count",
    "error_type",
    "failure_class",
    "topic",
    "consumer_group",
    "method",
    "mode",
}


def _new_identifier() -> str:
    return str(uuid4())


def normalize_identifier(value: str | None, *, fallback: str | None = None) -> str:
    """Accept only bounded, header-safe identifiers; otherwise generate one."""

    if value and _SAFE_IDENTIFIER.fullmatch(value) and "\r" not in value and "\n" not in value:
        return value
    return fallback or _new_identifier()


def current_request_id() -> str | None:
    return _request_id.get()


def current_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(value: str | None) -> str:
    normalized = normalize_identifier(value)
    _correlation_id.set(normalized)
    return normalized


def set_request_id(value: str | None) -> str:
    normalized = normalize_identifier(value)
    _request_id.set(normalized)
    return normalized


class JsonFormatter(logging.Formatter):
    """Serialize only the allowlisted operational fields to stdout."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": _SERVICE_NAME,
            "environment": _ENVIRONMENT,
            "event": getattr(record, "bankcore_event", record.name),
        }
        for field in _ALLOWED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["error_type"] = type(record.exc_info[1]).__name__
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(service: str, environment: str | None = None) -> None:
    """Install the same JSON schema for every Python service process."""

    global _SERVICE_NAME, _ENVIRONMENT
    _SERVICE_NAME = service
    _ENVIRONMENT = environment or os.getenv("ENVIRONMENT", "production")
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def log_event(logger: logging.Logger, event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Emit one sanitized event; fields outside the schema are discarded."""

    safe_fields: dict[str, Any] = {}
    for key, value in fields.items():
        if key not in _ALLOWED_FIELDS or _SENSITIVE_FIELD.search(key):
            continue
        if isinstance(value, (str, int, float, bool)):
            safe_fields[key] = value
    safe_fields.setdefault("request_id", current_request_id())
    safe_fields.setdefault("correlation_id", current_correlation_id())
    safe_fields = {key: value for key, value in safe_fields.items() if value is not None}
    logger.log(level, event, extra={"bankcore_event": event, **safe_fields})


class RequestContextMiddleware:
    """Propagate safe request/business IDs and emit a completion event."""

    def __init__(self, app: Callable[..., Awaitable[Any]], service: str, environment: str = "production") -> None:
        self.app = app
        self.service = service
        self.environment = environment
        self.logger = logging.getLogger(f"bankcore.{service}")

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin1").lower(): value.decode("latin1")
            for key, value in scope.get("headers", [])
        }
        request_id = normalize_identifier(headers.get("x-request-id"))
        correlation_id = normalize_identifier(headers.get("x-correlation-id"))
        request_token = _request_id.set(request_id)
        correlation_token = _correlation_id.set(correlation_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_context(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 500))
                response_headers = list(message.get("headers", []))
                response_headers.extend(
                    [
                        (b"x-request-id", request_id.encode("latin1")),
                        (b"x-correlation-id", current_correlation_id().encode("latin1")),
                    ]
                )
                message = {**message, "headers": response_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        finally:
            log_event(
                self.logger,
                "http.request.completed",
                status=status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            _request_id.reset(request_token)
            _correlation_id.reset(correlation_token)
