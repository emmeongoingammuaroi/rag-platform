"""Integration tests for GET /api/v1/metrics/summary endpoint."""

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _reset_metrics():
    """Reset metrics before each test to avoid cross-test pollution."""
    from app.utils.metrics import metrics

    metrics.reset()
    yield
    metrics.reset()


class TestMetricsEndpoint:
    async def test_returns_correct_schema(self, client: AsyncClient):
        resp = await client.get("/api/v1/metrics/summary")
        assert resp.status_code == 200
        data = resp.json()

        required_fields = [
            "uptime_seconds",
            "total_requests",
            "error_count",
            "error_rate",
            "avg_latency_ms",
            "p95_latency_ms",
            "status_codes",
            "rag_requests",
            "avg_rag_latency_ms",
            "avg_retrieval_score",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    async def test_numeric_types(self, client: AsyncClient):
        resp = await client.get("/api/v1/metrics/summary")
        data = resp.json()

        assert isinstance(data["uptime_seconds"], (int, float))
        assert isinstance(data["total_requests"], int)
        assert isinstance(data["error_count"], int)
        assert isinstance(data["error_rate"], (int, float))
        assert isinstance(data["avg_latency_ms"], (int, float))
        assert isinstance(data["p95_latency_ms"], (int, float))
        assert isinstance(data["status_codes"], dict)
        assert isinstance(data["rag_requests"], int)
        assert isinstance(data["avg_rag_latency_ms"], (int, float))
        assert isinstance(data["avg_retrieval_score"], (int, float))

    async def test_initial_values_are_zero(self, client: AsyncClient):
        resp = await client.get("/api/v1/metrics/summary")
        data = resp.json()
        assert data["total_requests"] == 0
        assert data["error_count"] == 0
        assert data["rag_requests"] == 0

    async def test_reflects_recorded_data(self, client: AsyncClient):
        from app.utils.metrics import metrics

        metrics.record_request(200, 50.0)
        metrics.record_request(500, 100.0)
        metrics.record_rag_latency(200.0)
        metrics.record_retrieval_scores([0.8, 0.9])

        resp = await client.get("/api/v1/metrics/summary")
        data = resp.json()
        assert data["total_requests"] == 2
        assert data["error_count"] == 1
        assert data["rag_requests"] == 1
        assert data["avg_rag_latency_ms"] == 200.0
        assert data["avg_retrieval_score"] == 0.85
