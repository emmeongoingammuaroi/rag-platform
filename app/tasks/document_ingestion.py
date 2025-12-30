import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.document import DocumentEmbeddingStatus
from app.services.document import DocumentService
from app.tasks.document_indexing import _index_document_async
from app.utils.document_extractor import extract_text

logger = logging.getLogger(__name__)


async def _extract_and_index_async(db: AsyncSession, document_id: UUID) -> None:
    doc = await DocumentService.get_by_id(db, document_id)
    if doc is None:
        logger.warning(f"Document not found for ingestion: {document_id}")
        return

    if not doc.file_path or not doc.file_type:
        logger.error(f"Document has no file_path/file_type for ingestion: {document_id}")
        doc.embedding_status = DocumentEmbeddingStatus.failed
        await db.flush()
        await db.refresh(doc)
        return

    try:
        text = extract_text(doc.file_path, doc.file_type)
        doc.content = text
        doc.embedding_status = DocumentEmbeddingStatus.pending
        await db.flush()
        await db.refresh(doc)

        await _index_document_async(db, document_id)

    except Exception as e:
        logger.error(f"Failed ingestion for document {document_id}: {e}")
        doc.embedding_status = DocumentEmbeddingStatus.failed
        await db.flush()
        await db.refresh(doc)
        raise


@celery_app.task(name="documents.ingest")
def ingest_document(document_id: str) -> None:
    async def runner() -> None:
        async with AsyncSessionLocal() as session:
            try:
                await _extract_and_index_async(session, UUID(document_id))
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    asyncio.run(runner())
