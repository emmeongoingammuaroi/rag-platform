"""Document ingestion orchestrator — extract, chunk, embed, index.

Supports incremental re-indexing: only embeds chunks whose content has changed.
"""

import hashlib
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentEmbeddingStatus
from app.rag.chunker import chunk_text
from app.rag.embedder import embed_texts
from app.services.document import DocumentService
from app.utils.document_extractor import extract_text_from_bytes
from app.utils.storage import object_storage
from app.utils.vector_db import vector_db

logger = logging.getLogger(__name__)


def _chunk_hash(content: str) -> str:
    """Compute SHA-256 hash of a chunk's content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def index_document(db: AsyncSession, document_id: UUID) -> None:
    """Chunk, embed, and index a document with incremental update support.

    Compares chunk hashes with existing vectors to avoid re-embedding unchanged chunks.

    Args:
        db: Async database session.
        document_id: The document to index.
    """
    doc = await DocumentService.get_by_id(db, document_id)
    if doc is None:
        logger.warning(f"Document not found for indexing: {document_id}")
        return

    await DocumentService.mark_indexing(db, doc)

    try:
        chunks = chunk_text(doc.content)
        if not chunks:
            vector_db.delete_by_document_id(doc.id)
            await DocumentService.mark_indexed(db, doc, chunk_count=0)
            return

        new_hashes = [_chunk_hash(c) for c in chunks]

        existing_points = vector_db.get_by_document_id(doc.id)
        existing_by_hash: dict[str, str] = {}
        for point in existing_points:
            payload = point.get("payload", {})
            chunk_h = payload.get("chunk_hash", "")
            if chunk_h:
                existing_by_hash[chunk_h] = point["id"]

        keep_ids: set[str] = set()
        chunks_to_embed: list[str] = []
        chunk_indices_to_embed: list[int] = []

        for i, (chunk, h) in enumerate(zip(chunks, new_hashes)):
            if h in existing_by_hash:
                keep_ids.add(existing_by_hash[h])
            else:
                chunks_to_embed.append(chunk)
                chunk_indices_to_embed.append(i)

        all_existing_ids = {p["id"] for p in existing_points}
        stale_ids = all_existing_ids - keep_ids
        if stale_ids:
            vector_db.delete_by_ids(list(stale_ids))

        if chunks_to_embed:
            embeddings = await embed_texts(chunks_to_embed)
            payloads = [
                {
                    "document_id": str(doc.id),
                    "user_id": str(doc.user_id),
                    "title": doc.title,
                    "content": chunks_to_embed[j],
                    "chunk_index": chunk_indices_to_embed[j],
                    "chunk_hash": new_hashes[chunk_indices_to_embed[j]],
                }
                for j in range(len(chunks_to_embed))
            ]
            vector_db.upsert_vectors(vectors=embeddings, payloads=payloads)

        await DocumentService.mark_indexed(db, doc, chunk_count=len(chunks))

    except Exception as e:
        logger.error(f"Failed indexing document {document_id}: {e}")
        await DocumentService.mark_failed(db, doc)
        raise


async def ingest_document(db: AsyncSession, document_id: UUID) -> None:
    """Full ingestion pipeline: extract text → chunk → embed → index.

    Args:
        db: Async database session.
        document_id: The document to ingest.
    """
    doc = await DocumentService.get_by_id(db, document_id)
    if doc is None:
        logger.warning(f"Document not found for ingestion: {document_id}")
        return

    if not doc.file_path or not doc.file_type:
        logger.error(f"Document has no file_path/file_type: {document_id}")
        doc.embedding_status = DocumentEmbeddingStatus.failed
        await db.flush()
        return

    try:
        file_data = object_storage.download(doc.file_path)
        text = extract_text_from_bytes(file_data, doc.file_type)
        doc.content = text

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        doc.content_hash = content_hash

        doc.embedding_status = DocumentEmbeddingStatus.pending
        await db.flush()

        await index_document(db, document_id)

    except Exception as e:
        logger.error(f"Failed ingestion for document {document_id}: {e}")
        doc.embedding_status = DocumentEmbeddingStatus.failed
        await db.flush()
        raise
