"""Document ingestion orchestrator — extract, chunk, embed, index."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentEmbeddingStatus
from app.rag.chunker import chunk_text
from app.rag.embedder import embed_texts
from app.services.document import DocumentService
from app.utils.document_extractor import extract_text
from app.utils.vector_db import vector_db

logger = logging.getLogger(__name__)


async def index_document(db: AsyncSession, document_id: UUID) -> None:
    """Chunk, embed, and index a document that already has extracted text.

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
        vector_db.delete_by_document_id(doc.id)

        chunks = chunk_text(doc.content)
        if not chunks:
            await DocumentService.mark_indexed(db, doc, chunk_count=0)
            return

        embeddings = await embed_texts(chunks)

        payloads = [
            {
                "document_id": str(doc.id),
                "user_id": str(doc.user_id),
                "title": doc.title,
                "content": chunk,
            }
            for chunk in chunks
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
        text = extract_text(doc.file_path, doc.file_type)
        doc.content = text
        doc.embedding_status = DocumentEmbeddingStatus.pending
        await db.flush()

        await index_document(db, document_id)

    except Exception as e:
        logger.error(f"Failed ingestion for document {document_id}: {e}")
        doc.embedding_status = DocumentEmbeddingStatus.failed
        await db.flush()
        raise
