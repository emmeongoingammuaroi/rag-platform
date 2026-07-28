"""BM25 keyword search over document chunks with user-scoped index."""

import logging
import re
from typing import Any
from uuid import UUID

from rank_bm25 import BM25Okapi

from app.utils.vector_db import vector_db

logger = logging.getLogger(__name__)

_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did will would "
    "shall should may might can could of in to for on with at by from as into "
    "through during before after above below between out off over under again "
    "further then once here there when where why how all each every both few "
    "more most other some such no nor not only own same so than too very".split()
)


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer with stop word removal."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


class BM25Index:
    """In-memory BM25 index built from a user's document chunks."""

    def __init__(self, corpus: list[dict[str, Any]]) -> None:
        self._docs = corpus
        tokenized = [_tokenize(doc.get("content", "")) for doc in corpus]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None

    def search(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
        """Search the BM25 index and return scored results."""
        if not self._bm25 or not self._docs:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        scored_docs: list[tuple[float, int]] = []
        for i, score in enumerate(scores):
            if score > 0:
                scored_docs.append((float(score), i))

        scored_docs.sort(key=lambda x: x[0], reverse=True)

        results: list[dict[str, Any]] = []
        for score, idx in scored_docs[:top_k]:
            doc = self._docs[idx]
            results.append(
                {
                    "id": doc.get("id", ""),
                    "score": score,
                    "payload": doc,
                }
            )
        return results


def build_bm25_index(user_id: UUID) -> BM25Index:
    """Build a BM25 index from all chunks belonging to a user.

    Scrolls through all vectors in Qdrant for the user and builds
    an in-memory BM25 index from their content payloads.
    """
    chunks: list[dict[str, Any]] = []
    offset: str | None = None

    from qdrant_client.models import FieldCondition, Filter, MatchValue

    scroll_filter = Filter(
        must=[
            FieldCondition(
                key="user_id",
                match=MatchValue(value=str(user_id)),
            )
        ]
    )

    while True:
        scroll_kwargs: dict[str, Any] = {
            "collection_name": vector_db.collection_name,
            "scroll_filter": scroll_filter,
            "limit": 100,
            "with_payload": True,
            "with_vectors": False,
        }
        if offset is not None:
            scroll_kwargs["offset"] = offset

        points, next_offset = vector_db.client.scroll(**scroll_kwargs)
        for point in points:
            payload = point.payload or {}
            chunks.append(
                {
                    "id": point.id,
                    "content": payload.get("content", ""),
                    "title": payload.get("title", ""),
                    "document_id": payload.get("document_id", ""),
                    "chunk_index": payload.get("chunk_index", 0),
                }
            )

        if next_offset is None:
            break
        offset = next_offset

    logger.debug("Built BM25 index for user %s with %d chunks", user_id, len(chunks))
    return BM25Index(chunks)
