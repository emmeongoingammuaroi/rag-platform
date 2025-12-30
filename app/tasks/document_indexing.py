import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.services.ai import ai_service
from app.services.document import DocumentService
from app.utils.vector_db import vector_db

logger = logging.getLogger(__name__)


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    if chunk_size <= 0:
        return [text]

    chunks: list[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(length, start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == length:
            break
        start = max(0, end - overlap)

    return chunks


async def _index_document_async(db: AsyncSession, document_id: UUID) -> None:
    doc = await DocumentService.get_by_id(db, document_id)
    if doc is None:
        logger.warning(f"Document not found for indexing: {document_id}")
        return

    await DocumentService.mark_indexing(db, doc)

    try:
        vector_db.delete_by_document_id(doc.id)

        chunks = _chunk_text(doc.content)
        if not chunks:
            await DocumentService.mark_indexed(db, doc, chunk_count=0)
            return

        embeddings = await ai_service.create_embeddings(chunks)

        payloads = [
            {
                "document_id": str(doc.id),
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


@celery_app.task(name="documents.index")
def index_document(document_id: str) -> None:
    async def runner() -> None:
        async with AsyncSessionLocal() as session:
            try:
                await _index_document_async(session, UUID(document_id))
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    asyncio.run(runner())


@celery_app.task(name="documents.delete_vectors")
def delete_document_vectors(document_id: str) -> None:
    vector_db.delete_by_document_id(UUID(document_id))
