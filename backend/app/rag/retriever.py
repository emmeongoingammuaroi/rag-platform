"""RAG retriever — embed query, parallel vector+BM25 search, RRF fusion, rerank."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.rag.hyde import embed_with_hyde
from app.rag.reranker import rerank
from app.utils.metrics import metrics
from app.utils.tracing import end_trace, start_trace, trace_span
from app.utils.vector_db import vector_db

logger = logging.getLogger(__name__)


def _reciprocal_rank_fusion(
    result_lists: list[list[dict[str, Any]]],
    k: int = 60,
) -> list[dict[str, Any]]:
    """Merge multiple ranked result lists using Reciprocal Rank Fusion (RRF).

    RRF score = sum(1 / (k + rank)) across all lists where the doc appears.
    """
    scores: dict[str, float] = {}
    doc_map: dict[str, dict[str, Any]] = {}

    for results in result_lists:
        for rank, result in enumerate(results):
            doc_id = str(result["id"])
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
            if doc_id not in doc_map:
                doc_map[doc_id] = result

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [{**doc_map[doc_id], "score": scores[doc_id]} for doc_id in sorted_ids]


def _vector_search(
    query_vector: list[float],
    user_id: UUID,
    top_k: int,
    score_threshold: float,
) -> list[dict[str, Any]]:
    """Synchronous vector search (runs in thread for parallel execution)."""
    return vector_db.search(
        query_vector=query_vector,
        user_id=user_id,
        top_k=top_k,
        score_threshold=score_threshold,
    )


def _bm25_search(query: str, user_id: UUID, top_k: int) -> list[dict[str, Any]]:
    """Synchronous BM25 search (runs in thread for parallel execution)."""
    from app.rag.bm25 import build_bm25_index

    bm25_index = build_bm25_index(user_id)
    return bm25_index.search(query, top_k=top_k)


async def retrieve(
    query: str,
    user_id: UUID,
    top_k: int = 5,
    score_threshold: float = 0.3,
) -> list[dict[str, Any]]:
    """Retrieve relevant document chunks for a user query.

    Flow: [HyDE expand] → embed → parallel(vector search, BM25) → [RRF fusion] → [rerank].
    """
    trace = start_trace()

    with trace_span("embed_query") as span:
        query_vector = await embed_with_hyde(query)
        span.set_attribute("hyde_enabled", settings.HYDE_ENABLED)
        span.set_attribute("vector_dim", len(query_vector))

    initial_top_k = settings.RETRIEVER_INITIAL_TOP_K if settings.RERANKER_ENABLED else top_k

    if settings.BM25_ENABLED:
        with trace_span("parallel_search") as span:
            vector_task = asyncio.to_thread(
                _vector_search, query_vector, user_id, initial_top_k, score_threshold
            )
            bm25_task = asyncio.to_thread(_bm25_search, query, user_id, initial_top_k)
            vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)

            span.set_attribute("vector_results_count", len(vector_results))
            span.set_attribute("bm25_results_count", len(bm25_results))

            if vector_results:
                scores = [r.get("score", 0.0) for r in vector_results]
                span.set_attribute("vector_max_score", round(max(scores), 4))
                span.set_attribute("vector_min_score", round(min(scores), 4))
                metrics.record_retrieval_scores(scores)

        with trace_span("rrf_fusion") as span:
            results = _reciprocal_rank_fusion([vector_results, bm25_results])
            span.set_attribute("fused_count", len(results))
    else:
        with trace_span("vector_search") as span:
            vector_results = await asyncio.to_thread(
                _vector_search, query_vector, user_id, initial_top_k, score_threshold
            )
            span.set_attribute("top_k", initial_top_k)
            span.set_attribute("results_count", len(vector_results))
            if vector_results:
                scores = [r.get("score", 0.0) for r in vector_results]
                span.set_attribute("max_score", round(max(scores), 4))
                span.set_attribute("min_score", round(min(scores), 4))
                metrics.record_retrieval_scores(scores)
        results = vector_results

    if settings.RERANKER_ENABLED and results:
        with trace_span("rerank") as span:
            results = rerank(query, results, top_k=top_k)
            span.set_attribute("reranker_model", settings.RERANKER_MODEL)
            span.set_attribute("results_after_rerank", len(results))

    final = results[:top_k]

    total_latency = sum(s.latency_ms for s in trace.spans)
    metrics.record_rag_latency(total_latency)
    end_trace(trace)

    return final
