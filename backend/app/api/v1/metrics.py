"""Metrics endpoint — aggregated observability stats."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.utils.metrics import metrics

router = APIRouter(prefix="/metrics", tags=["Metrics"])


class MetricsSummary(BaseModel):
    """Aggregated platform metrics."""

    uptime_seconds: float = Field(description="Seconds since last reset")
    total_requests: int = Field(description="Total HTTP requests handled")
    error_count: int = Field(description="Requests with status >= 400")
    error_rate: float = Field(description="error_count / total_requests")
    avg_latency_ms: float = Field(description="Mean request latency in milliseconds")
    p95_latency_ms: float = Field(description="95th percentile latency in milliseconds")
    status_codes: dict[int, int] = Field(description="Request count per HTTP status code")
    rag_requests: int = Field(description="Total RAG retrieval invocations")
    avg_rag_latency_ms: float = Field(description="Mean RAG pipeline latency in milliseconds")
    avg_retrieval_score: float = Field(description="Mean top-result similarity score")


@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary() -> MetricsSummary:
    """Return aggregated platform metrics."""
    return MetricsSummary(**metrics.summary())
