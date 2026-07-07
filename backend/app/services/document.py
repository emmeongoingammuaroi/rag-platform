"""Service layer for document CRUD and status management."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentEmbeddingStatus
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentService:
    """Handles all database operations for documents."""

    @staticmethod
    async def get_by_id(db: AsyncSession, document_id: UUID) -> Document | None:
        """Get a document by its ID (no user scope — for internal/task use).

        Args:
            db: Async database session.
            document_id: ID of the document.

        Returns:
            The Document if found, else None.
        """
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc: Document | None = result.scalar_one_or_none()
        return doc

    @staticmethod
    async def get_by_content_hash(
        db: AsyncSession, *, content_hash: str, user_id: UUID
    ) -> Document | None:
        """Find an existing document with the same content hash for a user.

        Args:
            db: Async database session.
            content_hash: SHA-256 hash of the file content.
            user_id: Owner constraint.

        Returns:
            The Document if a duplicate exists, else None.
        """
        result = await db.execute(
            select(Document).where(
                Document.content_hash == content_hash,
                Document.user_id == user_id,
            )
        )
        doc: Document | None = result.scalar_one_or_none()
        return doc

    @staticmethod
    async def get_by_id_for_user(
        db: AsyncSession, *, document_id: UUID, user_id: UUID
    ) -> Document | None:
        """Get a document by ID scoped to a specific user.

        Args:
            db: Async database session.
            document_id: ID of the document.
            user_id: Owner constraint (prevents cross-user access).

        Returns:
            The Document if found and owned by user, else None.
        """
        result = await db.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        doc: Document | None = result.scalar_one_or_none()
        return doc

    @staticmethod
    async def list_for_user(
        db: AsyncSession,
        *,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        """List documents for a user with pagination.

        Args:
            db: Async database session.
            user_id: The user whose documents to list.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Tuple of (documents list, total count).
        """
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
    async def create(db: AsyncSession, *, user_id: UUID, doc_in: DocumentCreate) -> Document:
        """Create a new document record.

        Args:
            db: Async database session.
            user_id: Owner of the document.
            doc_in: Document creation schema.

        Returns:
            The newly created Document instance.
        """
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
    async def update(db: AsyncSession, *, doc: Document, doc_in: DocumentUpdate) -> Document:
        """Update a document's fields and reset embedding status to pending.

        Args:
            db: Async database session.
            doc: The document to update.
            doc_in: Partial update schema.

        Returns:
            The updated Document instance.
        """
        update_data = doc_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(doc, field, value)

        doc.embedding_status = DocumentEmbeddingStatus.pending
        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def mark_indexing(db: AsyncSession, doc: Document) -> Document:
        """Transition document status to 'processing'.

        Args:
            db: Async database session.
            doc: The document being indexed.

        Returns:
            The updated Document instance.
        """
        doc.embedding_status = DocumentEmbeddingStatus.processing
        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def mark_indexed(db: AsyncSession, doc: Document, *, chunk_count: int) -> Document:
        """Transition document status to 'completed' after successful indexing.

        Args:
            db: Async database session.
            doc: The document that was indexed.
            chunk_count: Number of chunks generated.

        Returns:
            The updated Document instance.
        """
        doc.embedding_status = DocumentEmbeddingStatus.completed
        doc.chunk_count = chunk_count
        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def mark_failed(db: AsyncSession, doc: Document) -> Document:
        """Transition document status to 'failed'.

        Args:
            db: Async database session.
            doc: The document that failed processing.

        Returns:
            The updated Document instance.
        """
        doc.embedding_status = DocumentEmbeddingStatus.failed
        await db.flush()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def delete(db: AsyncSession, *, doc: Document) -> None:
        """Delete a document from the database.

        Args:
            db: Async database session.
            doc: The document to delete.
        """
        await db.delete(doc)
        await db.flush()
