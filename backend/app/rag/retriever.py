"""RAG retriever — embed query, search vectors, return context."""

from typing import Any
from uuid import UUID

from app.rag.embedder import embed_query
from app.utils.vector_db import vector_db


async def retrieve(
    query: str,
    user_id: UUID,
    top_k: int = 5,
    score_threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """Retrieve relevant document chunks for a user query.

    Flow: embed query → vector search (user-scoped) → return results.

    Args:
        query: User's question text.
        user_id: Scope search to this user's documents only.
        top_k: Maximum results to return.
        score_threshold: Minimum similarity score.

    Returns:
        List of search results with id, score, and payload.
    """
    query_vector = await embed_query(query)
    return vector_db.search(
        query_vector=query_vector,
        user_id=user_id,
        top_k=top_k,
        score_threshold=score_threshold,
    )


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
