"""Hypothetical Document Embedding (HyDE) for improved retrieval."""

import logging

from app.core.config import settings
from app.rag.embedder import embed_query as _raw_embed_query
from app.services.llm import llm_service

logger = logging.getLogger(__name__)

_HYDE_PROMPT = (
    "Given the following question, write a short passage (2-3 sentences) "
    "that would directly answer it. Write as if this passage comes from a "
    "relevant document. Do not say 'I don't know' — provide a plausible answer.\n\n"
    "Question: {query}\n\nPassage:"
)


async def generate_hypothetical_document(query: str) -> str:
    """Generate a hypothetical document that answers the query.

    Uses an LLM to produce a plausible answer passage, which is then
    embedded instead of the raw query to bridge the semantic gap.

    Args:
        query: The user's question.

    Returns:
        Generated hypothetical passage.
    """
    response = await llm_service.chat_completion(
        messages=[{"role": "user", "content": _HYDE_PROMPT.format(query=query)}],
        temperature=0.0,
        max_tokens=150,
    )
    return response["content"] or ""


async def embed_with_hyde(query: str) -> list[float]:
    """Embed query using HyDE: generate hypothetical answer, then embed it.

    Falls back to raw query embedding if HyDE generation fails.

    Args:
        query: The user's question.

    Returns:
        Embedding vector (of the hypothetical document, or raw query on failure).
    """
    if not settings.HYDE_ENABLED:
        return await _raw_embed_query(query)

    try:
        hypothetical = await generate_hypothetical_document(query)
        if not hypothetical.strip():
            return await _raw_embed_query(query)
        return await _raw_embed_query(hypothetical)
    except Exception as e:
        logger.warning("HyDE generation failed, falling back to raw query: %s", e)
        return await _raw_embed_query(query)
