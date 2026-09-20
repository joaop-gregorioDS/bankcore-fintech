import asyncio
import json
import logging
from io import StringIO

from common.observability import (
    JsonFormatter,
    RequestContextMiddleware,
    current_correlation_id,
    current_request_id,
    log_event,
    set_correlation_id,
    set_request_id,
)


def test_structured_log_is_allowlisted_and_contextualized():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("test.observability")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    set_request_id("request-123")
    set_correlation_id("correlation-123")
    log_event(
        logger,
        "transactions.operation.started",
        transaction_id="transaction-123",
        Authorization="Bearer should-not-appear",
        cpf="12345678901",
    )

    payload = json.loads(stream.getvalue())
    assert payload["event"] == "transactions.operation.started"
    assert payload["request_id"] == "request-123"
    assert payload["correlation_id"] == "correlation-123"
    assert payload["transaction_id"] == "transaction-123"
    assert "Authorization" not in stream.getvalue()
    assert "12345678901" not in stream.getvalue()


def test_request_context_middleware_preserves_safe_headers_and_emits_response_headers():
    sent = []

    async def application(scope, receive, send):
        assert current_request_id() == "request-abc"
        assert current_correlation_id() == "correlation-abc"
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    async def sender(message):
        sent.append(message)

    middleware = RequestContextMiddleware(application, service="test-service")
    scope = {
        "type": "http",
        "headers": [
            (b"x-request-id", b"request-abc"),
            (b"x-correlation-id", b"correlation-abc"),
        ],
    }

    asyncio.run(middleware(scope, None, sender))
    headers = dict(sent[0]["headers"])
    assert headers[b"x-request-id"] == b"request-abc"
    assert headers[b"x-correlation-id"] == b"correlation-abc"
