"""RAG retriever — embed query, search vectors, rerank, return context."""

from typing import Any
from uuid import UUID

from app.core.config import settings
from app.rag.hyde import embed_with_hyde
from app.rag.reranker import rerank
from app.utils.metrics import metrics
from app.utils.tracing import end_trace, start_trace, trace_span
from app.utils.vector_db import vector_db


async def retrieve(
    query: str,
    user_id: UUID,
    top_k: int = 5,
    score_threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """Retrieve relevant document chunks for a user query.

    Flow: [HyDE expand] → embed → vector search (user-scoped) → [rerank] → results.

    Args:
        query: User's question text.
        user_id: Scope search to this user's documents only.
        top_k: Maximum results to return.
        score_threshold: Minimum similarity score.

    Returns:
        List of search results with id, score, and payload.
    """
    trace = start_trace()

    with trace_span("embed_query") as span:
        query_vector = await embed_with_hyde(query)
        span.set_attribute("hyde_enabled", settings.HYDE_ENABLED)
        span.set_attribute("vector_dim", len(query_vector))

    initial_top_k = settings.RETRIEVER_INITIAL_TOP_K if settings.RERANKER_ENABLED else top_k

    with trace_span("vector_search") as span:
        results = vector_db.search(
            query_vector=query_vector,
            user_id=user_id,
            top_k=initial_top_k,
            score_threshold=score_threshold,
        )
        span.set_attribute("top_k", initial_top_k)
        span.set_attribute("results_count", len(results))
        if results:
            scores = [r.get("score", 0.0) for r in results]
            span.set_attribute("max_score", round(max(scores), 4))
            span.set_attribute("min_score", round(min(scores), 4))
            metrics.record_retrieval_scores(scores)

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


def format_context(results: list[dict[str, Any]]) -> str:
    """Format retrieval results into a context string for the LLM.

    Args:
        results: Search results from retrieve().

    Returns:
        Formatted context string, empty if no results.
    """
    parts: list[str] = []
    for result in results:
        payload = result.get("payload") or {}
        title = payload.get("title", "Unknown")
        content = payload.get("content", "")
        parts.append(f"[Document: {title}]\n{content}")
    return "\n\n".join(parts)
