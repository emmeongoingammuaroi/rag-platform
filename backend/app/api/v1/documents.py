"""Document management endpoints."""

import os
from math import ceil
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.document import Document, DocumentCreate, DocumentList, DocumentUpdate
from app.services.document import DocumentService
from app.tasks.ingestion import delete_document_vectors, task_index_document, task_ingest_document

router = APIRouter(prefix="/documents", tags=["Documents"])


ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    "pdf": {"application/pdf"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    "txt": {"text/plain"},
    "md": {"text/plain", "text/markdown"},
}


@router.post("/upload", response_model=Document, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Document:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    if ext not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES[ext]:
        raise HTTPException(status_code=400, detail="File content type does not match extension")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    safe_filename = os.path.basename(file.filename).replace("..", "").strip()
    if not safe_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    storage_dir = Path(settings.STORAGE_DIR) / "documents" / str(current_user.id)
    storage_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid4().hex
    stored_path = storage_dir / f"{file_id}.{ext}"
    stored_path.write_bytes(content)

    doc_in = DocumentCreate(
        title=os.path.splitext(os.path.basename(file.filename))[0],
        content="",
    )
    doc = await DocumentService.create(db, user_id=current_user.id, doc_in=doc_in)
    doc.file_path = str(stored_path)
    doc.file_type = ext
    await db.flush()
    await db.refresh(doc)

    await db.commit()
    task_ingest_document.delay(str(doc.id))
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
        items=items,  # type: ignore[arg-type]
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
    doc = await DocumentService.get_by_id_for_user(
        db, document_id=document_id, user_id=current_user.id
    )
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
    doc = await DocumentService.get_by_id_for_user(
        db, document_id=document_id, user_id=current_user.id
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    updated = await DocumentService.update(db, doc=doc, doc_in=doc_in)
    await db.commit()
    task_index_document.delay(str(updated.id))
    return updated


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    doc = await DocumentService.get_by_id_for_user(
        db, document_id=document_id, user_id=current_user.id
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    await DocumentService.delete(db, doc=doc)
    await db.commit()
    delete_document_vectors.delay(str(document_id))
    return None
