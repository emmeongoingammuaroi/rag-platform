"""In-memory metrics collector for request and RAG pipeline tracking."""

import threading
import time
from typing import Any


class MetricsCollector:
    """Thread-safe in-memory metrics aggregator.

    Tracks request counts, latencies, status codes, and RAG-specific metrics.
    Designed for single-process use (suitable for dev/demo; production would use Redis).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._request_count: int = 0
        self._error_count: int = 0
        self._latencies: list[float] = []
        self._status_codes: dict[int, int] = {}
        self._rag_latencies: list[float] = []
        self._retrieval_scores: list[float] = []
        self._start_time: float = time.time()

    def record_request(self, status_code: int, latency_ms: float) -> None:
        with self._lock:
            self._request_count += 1
            self._latencies.append(latency_ms)
            self._status_codes[status_code] = self._status_codes.get(status_code, 0) + 1
            if status_code >= 400:
                self._error_count += 1

    def record_rag_latency(self, latency_ms: float) -> None:
        with self._lock:
            self._rag_latencies.append(latency_ms)

    def record_retrieval_scores(self, scores: list[float]) -> None:
        with self._lock:
            self._retrieval_scores.extend(scores)

    def summary(self) -> dict[str, Any]:
        with self._lock:
            uptime_s = time.time() - self._start_time
            avg_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
            p95_latency = _percentile(self._latencies, 95) if self._latencies else 0.0
            avg_rag_latency = (
                sum(self._rag_latencies) / len(self._rag_latencies) if self._rag_latencies else 0.0
            )
            avg_retrieval_score = (
                sum(self._retrieval_scores) / len(self._retrieval_scores)
                if self._retrieval_scores
                else 0.0
            )
            error_rate = self._error_count / self._request_count if self._request_count else 0.0

            return {
                "uptime_seconds": round(uptime_s, 1),
                "total_requests": self._request_count,
                "error_count": self._error_count,
                "error_rate": round(error_rate, 4),
                "avg_latency_ms": round(avg_latency, 2),
                "p95_latency_ms": round(p95_latency, 2),
                "status_codes": dict(self._status_codes),
                "rag_requests": len(self._rag_latencies),
                "avg_rag_latency_ms": round(avg_rag_latency, 2),
                "avg_retrieval_score": round(avg_retrieval_score, 4),
            }

    def reset(self) -> None:
        with self._lock:
            self._request_count = 0
            self._error_count = 0
            self._latencies.clear()
            self._status_codes.clear()
            self._rag_latencies.clear()
            self._retrieval_scores.clear()
            self._start_time = time.time()


def _percentile(data: list[float], pct: int) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * pct / 100)
    idx = min(idx, len(sorted_data) - 1)
    return sorted_data[idx]


metrics = MetricsCollector()
