"""
Document model for storing uploaded documents and their metadata.
"""

from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Uuid, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDTimestampBase


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
    embedding_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, processing, completed, failed

    def __repr__(self) -> str:
        """String representation of Document."""
        return f"<Document(id={self.id}, title={self.title}, user_id={self.user_id})>"
