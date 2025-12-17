"""
Pydantic schemas for Document model.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base document schema."""

    title: str = Field(..., min_length=1, max_length=255)
    content: str


class DocumentCreate(DocumentBase):
    """Schema for document creation."""

    pass


class DocumentUpdate(BaseModel):
    """Schema for document update."""

    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = None


class DocumentInDB(DocumentBase):
    """Schema for document in database."""

    id: int
    file_path: str | None
    file_type: str | None
    user_id: int
    chunk_count: int
    embedding_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Document(DocumentInDB):
    """Public document schema."""

    pass


class DocumentList(BaseModel):
    """Schema for paginated document list."""

    items: list[Document]
    total: int
    page: int
    page_size: int
    pages: int
