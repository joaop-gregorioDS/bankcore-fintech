from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from common.tracing import extract_trace_context, inject_trace_headers


def test_w3c_trace_context_round_trips_without_changing_business_ids():
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    tracer = provider.get_tracer("test.tracing")

    with tracer.start_as_current_span("parent") as parent:
        headers: dict[str, str] = {}
        inject_trace_headers(headers)
        context = extract_trace_context(headers)
        with tracer.start_as_current_span("child", context=context) as child:
            assert child.get_span_context().trace_id == parent.get_span_context().trace_id
            assert child.get_span_context().span_id != parent.get_span_context().span_id

    assert set(headers) >= {"traceparent"}
    assert "correlation_id" not in headers


def test_invalid_or_missing_trace_headers_are_safe():
    context = extract_trace_context({"traceparent": "not-a-valid-w3c-context"})
    span = trace.get_current_span(context)
    assert not span.get_span_context().is_valid
