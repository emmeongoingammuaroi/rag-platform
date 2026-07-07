"""Cross-encoder reranker for two-stage retrieval."""

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_model: Any = None


def _get_model() -> Any:
    """Lazy-load the cross-encoder model on first call."""
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder

        logger.info("Loading cross-encoder model: %s", settings.RERANKER_MODEL)
        _model = CrossEncoder(settings.RERANKER_MODEL)
    return _model


def rerank(
    query: str,
    results: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Rerank search results using a cross-encoder model.

    Takes initial retrieval results (high recall) and re-scores them
    with a cross-encoder for higher precision.

    Args:
        query: The user's query text.
        results: Initial retrieval results with 'payload.content' fields.
        top_k: Number of top results to return after reranking.

    Returns:
        Top-k results sorted by cross-encoder score, with 'rerank_score' added.
    """
    if not results:
        return []

    if not settings.RERANKER_ENABLED:
        return results[:top_k]

    model = _get_model()
    pairs: list[list[str]] = []
    for r in results:
        content = (r.get("payload") or {}).get("content", "")
        pairs.append([query, content])

    scores: list[float] = model.predict(pairs).tolist()

    for result, score in zip(results, scores):
        result["rerank_score"] = score

    ranked = sorted(results, key=lambda r: r["rerank_score"], reverse=True)
    return ranked[:top_k]
