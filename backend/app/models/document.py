"""
Document model for storing uploaded documents and their metadata.
"""

from enum import Enum
from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDTimestampBase
from app.models import user as _user


class DocumentEmbeddingStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Document(UUIDTimestampBase):
    """Document model for RAG system."""

    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_status: Mapped[DocumentEmbeddingStatus] = mapped_column(
        SAEnum(DocumentEmbeddingStatus, name="document_embedding_status"),
        default=DocumentEmbeddingStatus.pending,
        nullable=False,
    )

    def __repr__(self) -> str:
        """String representation of Document."""
        return f"<Document(id={self.id}, title={self.title}, user_id={self.user_id})>"
