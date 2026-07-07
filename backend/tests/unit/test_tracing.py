"""Unit tests for app.utils.tracing — span lifecycle, no-op, metrics recording."""

import time
from unittest.mock import patch

from app.utils.tracing import (
    Span,
    Trace,
    _NoOpSpan,
    end_trace,
    get_current_trace,
    start_trace,
    trace_span,
)


class TestSpanLifecycle:
    def test_span_creation(self):
        span = Span(name="test_op", trace_id="trace123")
        assert span.name == "test_op"
        assert span.trace_id == "trace123"
        assert span.span_id is not None
        assert span.end_time is None
        assert span.latency_ms == 0.0

    def test_span_finish(self):
        span = Span(name="test_op", trace_id="trace123")
        time.sleep(0.01)
        span.finish()
        assert span.end_time is not None
        assert span.latency_ms > 0

    def test_span_set_attribute(self):
        span = Span(name="embed", trace_id="t1")
        span.set_attribute("dim", 1536)
        span.set_attribute("model", "text-embedding-3-small")
        assert span.attributes["dim"] == 1536
        assert span.attributes["model"] == "text-embedding-3-small"

    def test_span_to_dict(self):
        span = Span(name="search", trace_id="t2")
        span.set_attribute("top_k", 5)
        span.finish()
        d = span.to_dict()
        assert d["name"] == "search"
        assert d["trace_id"] == "t2"
        assert "span_id" in d
        assert "latency_ms" in d
        assert d["top_k"] == 5


class TestTrace:
    def test_trace_creation(self):
        trace = Trace()
        assert trace.trace_id is not None
        assert trace.spans == []

    def test_trace_to_dict(self):
        trace = Trace()
        span = Span(name="op1", trace_id=trace.trace_id)
        span.finish()
        trace.spans.append(span)
        d = trace.to_dict()
        assert d["trace_id"] == trace.trace_id
        assert d["total_latency_ms"] >= 0
        assert len(d["spans"]) == 1


class TestStartEndTrace:
    def test_start_sets_context(self):
        trace = start_trace()
        assert get_current_trace() is trace
        end_trace(trace)
        assert get_current_trace() is None

    def test_end_clears_context(self):
        trace = start_trace()
        end_trace(trace)
        assert get_current_trace() is None


class TestTraceSpan:
    @patch("app.utils.tracing.settings")
    def test_span_recorded_in_trace(self, mock_settings):
        mock_settings.OBSERVABILITY_PROVIDER = "json"
        trace = start_trace()
        with trace_span("embed_query") as span:
            span.set_attribute("dim", 1536)
        assert len(trace.spans) == 1
        assert trace.spans[0].name == "embed_query"
        assert trace.spans[0].attributes["dim"] == 1536
        assert trace.spans[0].latency_ms >= 0
        end_trace(trace)

    @patch("app.utils.tracing.settings")
    def test_noop_when_provider_none(self, mock_settings):
        mock_settings.OBSERVABILITY_PROVIDER = "none"
        trace = start_trace()
        with trace_span("should_not_record") as span:
            span.set_attribute("key", "value")
        assert len(trace.spans) == 0
        end_trace(trace)

    def test_noop_when_no_active_trace(self):
        with trace_span("orphan") as span:
            span.set_attribute("k", "v")
        assert isinstance(span, _NoOpSpan)


class TestNoOpSpan:
    def test_set_attribute_is_noop(self):
        span = _NoOpSpan()
        span.set_attribute("key", "value")

    def test_latency_is_zero(self):
        span = _NoOpSpan()
        assert span.latency_ms == 0.0
