"""Document ingestion Celery tasks — thin wrappers around app.rag.ingest."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import settings
from app.rag.ingest import index_document, ingest_document
from app.utils.storage import object_storage
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


@celery_app.task(name="documents.ingest")
def task_ingest_document(document_id: str) -> None:
    async def _run() -> None:
        async with _celery_session() as session:
            await ingest_document(session, UUID(document_id))

    asyncio.run(_run())


@celery_app.task(name="documents.index")
def task_index_document(document_id: str) -> None:
    async def _run() -> None:
        async with _celery_session() as session:
            await index_document(session, UUID(document_id))

    asyncio.run(_run())


@celery_app.task(name="documents.delete")
def delete_document_task(document_id: str, file_path: str | None = None) -> None:
    """Delete vectors and the stored file for a document."""
    vector_db.delete_by_document_id(UUID(document_id))
    if file_path:
        try:
            object_storage.delete(file_path)
        except Exception as e:
            logger.warning(f"Failed to delete file {file_path} from storage: {e}")
