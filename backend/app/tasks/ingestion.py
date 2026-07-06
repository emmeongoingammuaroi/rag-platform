"""Document ingestion tasks — extract, chunk, embed, index."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.document import DocumentEmbeddingStatus
from app.services.document import DocumentService
from app.services.llm import llm_service
from app.utils.document_extractor import extract_text
from app.utils.vector_db import vector_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _celery_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        settings.async_database_url,
        echo=settings.DB_ECHO,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )
    try:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    finally:
        await engine.dispose()


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


async def _index_document(db: AsyncSession, document_id: UUID) -> None:
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

        embeddings = await llm_service.create_embeddings(chunks)

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


async def _ingest_document(db: AsyncSession, document_id: UUID) -> None:
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

        await _index_document(db, document_id)

    except Exception as e:
        logger.error(f"Failed ingestion for document {document_id}: {e}")
        doc.embedding_status = DocumentEmbeddingStatus.failed
        await db.flush()
        raise


@celery_app.task(name="documents.ingest")
def ingest_document(document_id: str) -> None:
    async def _run() -> None:
        async with _celery_session() as session:
            await _ingest_document(session, UUID(document_id))

    asyncio.run(_run())


@celery_app.task(name="documents.index")
def index_document(document_id: str) -> None:
    async def _run() -> None:
        async with _celery_session() as session:
            await _index_document(session, UUID(document_id))

    asyncio.run(_run())


@celery_app.task(name="documents.delete_vectors")
def delete_document_vectors(document_id: str) -> None:
    vector_db.delete_by_document_id(UUID(document_id))
