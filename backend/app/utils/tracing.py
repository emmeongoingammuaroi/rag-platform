"""RAG pipeline tracing — structured span tracking for observability."""

import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Generator
from uuid import uuid4

from app.core.config import settings

logger = logging.getLogger(__name__)

_current_trace: ContextVar[str | None] = ContextVar("_current_trace", default=None)


class Span:
    """A single trace span representing one stage of the RAG pipeline."""

    __slots__ = ("name", "trace_id", "span_id", "start_time", "end_time", "attributes")

    def __init__(self, name: str, trace_id: str) -> None:
        self.name = name
        self.trace_id = trace_id
        self.span_id = uuid4().hex[:16]
        self.start_time = time.perf_counter()
        self.end_time: float | None = None
        self.attributes: dict[str, Any] = {}

    @property
    def latency_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def finish(self) -> None:
        self.end_time = time.perf_counter()

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "name": self.name,
            "latency_ms": round(self.latency_ms, 2),
            **self.attributes,
        }


class Trace:
    """Collects spans for a single RAG pipeline invocation."""

    __slots__ = ("trace_id", "spans")

    def __init__(self) -> None:
        self.trace_id = uuid4().hex
        self.spans: list[Span] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "total_latency_ms": round(sum(s.latency_ms for s in self.spans), 2),
            "spans": [s.to_dict() for s in self.spans],
        }


_current_trace_obj: ContextVar[Trace | None] = ContextVar("_current_trace_obj", default=None)


def start_trace() -> Trace:
    """Start a new trace and set it as the current context trace."""
    trace = Trace()
    _current_trace.set(trace.trace_id)
    _current_trace_obj.set(trace)
    return trace


def get_current_trace() -> Trace | None:
    """Get the active trace from context, if any."""
    return _current_trace_obj.get()


def end_trace(trace: Trace) -> None:
    """End a trace, emit it, and clear context."""
    _emit_trace(trace)
    _current_trace.set(None)
    _current_trace_obj.set(None)


@contextmanager
def trace_span(name: str) -> Generator["Span | _NoOpSpan", None, None]:
    """Context manager that records a named span within the current trace.

    Usage:
        with trace_span("embed_query") as span:
            result = await embed(query)
            span.set_attribute("vector_dim", len(result))
    """
    trace = _current_trace_obj.get()
    if trace is None or settings.OBSERVABILITY_PROVIDER == "none":
        yield _NoOpSpan()
        return

    span = Span(name=name, trace_id=trace.trace_id)
    try:
        yield span
    finally:
        span.finish()
        trace.spans.append(span)


class _NoOpSpan:
    """Lightweight no-op span when tracing is disabled."""

    __slots__ = ()

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    @property
    def latency_ms(self) -> float:
        return 0.0


def _emit_trace(trace: Trace) -> None:
    """Emit trace data via the configured provider."""
    if settings.OBSERVABILITY_PROVIDER == "none":
        return
    if not trace.spans:
        return
    logger.info("rag_trace", extra={"trace_data": trace.to_dict()})
