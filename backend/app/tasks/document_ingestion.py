import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import settings
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
        engine = create_async_engine(
            settings.async_database_url,
            echo=settings.DB_ECHO,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        sessionmaker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        try:
            async with sessionmaker() as session:
                try:
                    await _extract_and_index_async(session, UUID(document_id))
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
        finally:
            await engine.dispose()

    asyncio.run(runner())
