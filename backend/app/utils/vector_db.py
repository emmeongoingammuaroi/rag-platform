"""Qdrant vector database client with lazy initialization and user-scoped search."""

import logging
from typing import Any
from uuid import UUID, uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorDB:
    """Qdrant client wrapper.

    Connects lazily on first use to avoid import-time failures
    when Qdrant is unreachable (e.g. in tests or CLI).
    """

    def __init__(self) -> None:
        """Initialize without connecting — connection deferred to first access."""
        self._client: QdrantClient | None = None
        self.collection_name = settings.QDRANT_COLLECTION_NAME

    @property
    def client(self) -> QdrantClient:
        """Get or create the Qdrant client (lazy init).

        Returns:
            Connected QdrantClient instance.
        """
        if self._client is None:
            self._client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
            self._ensure_collection()
        return self._client

    def _ensure_collection(self) -> None:
        """Create the target collection if it doesn't exist."""
        assert self._client is not None
        try:
            collections = self._client.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.VECTOR_DIMENSION,
                        distance=Distance.COSINE,
                    ),
                )
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise

    def upsert_vectors(
        self,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: list[str] | None = None,
    ) -> None:
        """Upsert embedding vectors with associated metadata.

        Args:
            vectors: List of embedding vectors.
            payloads: List of metadata dicts (must include user_id, document_id).
            ids: Optional point IDs (auto-generated UUIDs if omitted).
        """
        if ids is None:
            ids = [str(uuid4()) for _ in vectors]

        points = [
            PointStruct(id=id_, vector=vector, payload=payload)
            for id_, vector, payload in zip(ids, vectors, payloads)
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info(f"Upserted {len(points)} vectors to {self.collection_name}")

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        score_threshold: float = 0.7,
        user_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic similarity search, scoped to a user's documents.

        Args:
            query_vector: The query embedding vector.
            top_k: Maximum number of results to return.
            score_threshold: Minimum cosine similarity score.
            user_id: Filter results to this user's documents only.

        Returns:
            List of dicts with keys: id, score, payload.
        """
        query_filter = None
        if user_id is not None:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=str(user_id)),
                    )
                ]
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": result.id,
                "score": result.score,
                "payload": result.payload,
            }
            for result in results
        ]

    def get_by_document_id(self, document_id: UUID) -> list[dict[str, Any]]:
        """Retrieve all vectors belonging to a specific document.

        Args:
            document_id: The document whose vectors to retrieve.

        Returns:
            List of dicts with keys: id, payload.
        """
        results: list[dict[str, Any]] = []
        offset: str | None = None
        while True:
            scroll_kwargs: dict[str, Any] = {
                "collection_name": self.collection_name,
                "scroll_filter": Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=str(document_id)),
                        )
                    ]
                ),
                "limit": 100,
                "with_payload": True,
                "with_vectors": False,
            }
            if offset is not None:
                scroll_kwargs["offset"] = offset
            points, next_offset = self.client.scroll(**scroll_kwargs)
            for point in points:
                results.append({"id": point.id, "payload": point.payload or {}})
            if next_offset is None:
                break
            offset = next_offset
        return results

    def delete_by_ids(self, point_ids: list[str]) -> None:
        """Delete vectors by their point IDs.

        Args:
            point_ids: List of Qdrant point IDs to delete.
        """
        if not point_ids:
            return
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=point_ids),
        )
        logger.info(f"Deleted {len(point_ids)} vectors by ID")

    def delete_by_document_id(self, document_id: UUID) -> None:
        """Delete all vectors belonging to a specific document.

        Args:
            document_id: The document whose vectors should be removed.
        """
        selector = FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=str(document_id)),
                    )
                ]
            )
        )
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=selector,
        )
        logger.info(f"Deleted vectors for document_id: {document_id}")

    def close(self) -> None:
        """Close the Qdrant client connection."""
        if self._client is not None:
            self._client.close()
            self._client = None


vector_db = VectorDB()
