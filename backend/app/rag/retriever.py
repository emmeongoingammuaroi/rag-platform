"""RAG retriever — embed query, search vectors, rerank, return context."""

from typing import Any
from uuid import UUID

from app.core.config import settings
from app.rag.hyde import embed_with_hyde
from app.rag.reranker import rerank
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
    query_vector = await embed_with_hyde(query)

    initial_top_k = settings.RETRIEVER_INITIAL_TOP_K if settings.RERANKER_ENABLED else top_k

    results = vector_db.search(
        query_vector=query_vector,
        user_id=user_id,
        top_k=initial_top_k,
        score_threshold=score_threshold,
    )

    if settings.RERANKER_ENABLED and results:
        results = rerank(query, results, top_k=top_k)

    return results[:top_k]


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
