"""Document service for business logic."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentEmbeddingStatus
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentService:
    """Document service with repository pattern."""

    @staticmethod
    async def get_by_id(db: AsyncSession, document_id: UUID) -> Document | None:
        result = await db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id_for_user(
        db: AsyncSession, document_id: UUID, user_id: UUID
    ) -> Document | None:
        result = await db.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_user(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        offset = (page - 1) * page_size

        total_result = await db.execute(
            select(func.count()).select_from(Document).where(Document.user_id == user_id)
        )
        total = int(total_result.scalar_one())

        items_result = await db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(items_result.scalars().all())
        return items, total

    @staticmethod
    async def create(db: AsyncSession, user_id: UUID, doc_in: DocumentCreate) -> Document:
        doc = Document(
            title=doc_in.title,
            content=doc_in.content,
            user_id=user_id,
            chunk_count=0,
            embedding_status=DocumentEmbeddingStatus.pending,
        )
        db.add(doc)
        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def update(db: AsyncSession, doc: Document, doc_in: DocumentUpdate) -> Document:
        update_data = doc_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(doc, field, value)

        doc.embedding_status = DocumentEmbeddingStatus.pending
        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def mark_indexing(db: AsyncSession, doc: Document) -> Document:
        doc.embedding_status = DocumentEmbeddingStatus.processing
        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def mark_indexed(db: AsyncSession, doc: Document, chunk_count: int) -> Document:
        doc.embedding_status = DocumentEmbeddingStatus.completed
        doc.chunk_count = chunk_count
        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def mark_failed(db: AsyncSession, doc: Document) -> Document:
        doc.embedding_status = DocumentEmbeddingStatus.failed
        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def delete(db: AsyncSession, doc: Document) -> None:
        await db.delete(doc)
        await db.flush()
