"""OpenTelemetry tracing: spans over OTLP/HTTP to Jaeger; a no-op without OTEL_EXPORTER_OTLP_ENDPOINT.

The trace id is the flow's Auxin `trace_id` (32 hex), so a Jaeger trace, the task store and the decision log
share one id. The parent span travels in the A2A message metadata as W3C `traceparent`, next to the Auxin
extension (the extension schema stays unchanged). Span names and GenAI attributes: semconv gen-ai/1.42.0.
"""
import atexit
import os
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.trace import Span, SpanKind

TRACEPARENT = "traceparent"

# The trace id a new root span takes: the flow's Auxin trace_id instead of a random one.
_flow_trace_id: ContextVar[int | None] = ContextVar("auxin_flow_trace_id", default=None)

tracer = trace.get_tracer("auxin")


class _FlowIdGenerator(RandomIdGenerator):
    def generate_trace_id(self) -> int:
        return _flow_trace_id.get() or super().generate_trace_id()


def setup(service: str) -> None:
    """Once per process. Also traces every httpx call (knowledge REST, IBKR MCP, ibkrfacade, A2A)."""
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service}), id_generator=_FlowIdGenerator())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    atexit.register(provider.shutdown)  # one-shot runs (operator, run-job) flush before exit
    HTTPXClientInstrumentor().instrument()


def traceparent() -> dict:
    """The current span as {"traceparent": ...} for a message's metadata; empty without a recording span."""
    carrier: dict = {}
    propagate.inject(carrier)
    return {k: v for k, v in carrier.items() if k == TRACEPARENT}


@contextmanager
def span(name: str, *, trace_id: str | None = None, parent: str | None = None, kind: SpanKind = SpanKind.INTERNAL,
         attributes: dict | None = None) -> Iterator[Span]:
    """A span under `parent` (a traceparent) or the current span; without either, a root with `trace_id`."""
    context = propagate.extract({TRACEPARENT: parent}) if parent else None
    token = _flow_trace_id.set(int(trace_id, 16)) if trace_id else None
    try:
        with tracer.start_as_current_span(name, context=context, kind=kind,
                                          attributes={k: v for k, v in (attributes or {}).items() if v is not None}) as s:
            yield s
    finally:
        if token:
            _flow_trace_id.reset(token)
