"""Document management endpoints."""

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.document import Document, DocumentCreate, DocumentList, DocumentUpdate
from app.services.document import DocumentService
from app.tasks.document_indexing import delete_document_vectors, index_document

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=Document, status_code=status.HTTP_201_CREATED)
async def create_document(
    doc_in: DocumentCreate,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Document:
    doc = await DocumentService.create(db, user_id=current_user.id, doc_in=doc_in)
    index_document.delay(str(doc.id))
    return doc


@router.get("", response_model=DocumentList)
async def list_documents(
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
) -> DocumentList:
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")
    if page_size < 1:
        raise HTTPException(status_code=400, detail="page_size must be >= 1")

    items, total = await DocumentService.list_for_user(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    pages = ceil(total / page_size) if page_size else 0
    return DocumentList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Document:
    doc = await DocumentService.get_by_id_for_user(db, document_id, current_user.id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.put("/{document_id}", response_model=Document)
async def update_document(
    document_id: UUID,
    doc_in: DocumentUpdate,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Document:
    doc = await DocumentService.get_by_id_for_user(db, document_id, current_user.id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    updated = await DocumentService.update(db, doc, doc_in)
    index_document.delay(str(updated.id))
    return updated


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    doc = await DocumentService.get_by_id_for_user(db, document_id, current_user.id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    await DocumentService.delete(db, doc)
    delete_document_vectors.delay(str(document_id))
    return None
