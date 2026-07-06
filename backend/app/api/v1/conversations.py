"""Conversation endpoints — CRUD and RAG-powered messaging."""

import logging
from datetime import datetime, timezone
from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.conversation import (
    Conversation,
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    ConversationUpdate,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.conversation import ConversationService
from app.services.llm import llm_service
from app.utils.vector_db import vector_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_in: ConversationCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Conversation:
    conversation = await ConversationService.create_conversation(
        db,
        user_id=current_user.id,
        title=conversation_in.title,
    )
    await db.commit()
    return conversation


@router.get("", response_model=ConversationList)
async def list_conversations(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
) -> ConversationList:
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")
    if page_size < 1:
        raise HTTPException(status_code=400, detail="page_size must be >= 1")

    items, total = await ConversationService.list_conversations_for_user(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    pages = ceil(total / page_size) if page_size else 0
    return ConversationList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConversationDetail:
    conversation = await ConversationService.get_conversation_for_user(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await ConversationService.list_messages(
        db,
        conversation_id=conversation_id,
        newest_first=True,
    )
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        user_id=conversation.user_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


@router.patch("/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: UUID,
    conversation_in: ConversationUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Conversation:
    conversation = await ConversationService.get_conversation_for_user(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    updated = await ConversationService.update_conversation_title(
        db,
        conversation=conversation,
        title=conversation_in.title,
    )
    await db.commit()
    return updated


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    conversation = await ConversationService.get_conversation_for_user(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await ConversationService.delete_conversation(db, conversation=conversation)
    await db.commit()
    return None


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
)
@limiter.limit("60/minute")
async def send_message(
    request: Request,
    conversation_id: UUID,
    msg_in: SendMessageRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SendMessageResponse:
    conversation = await ConversationService.get_conversation_for_user(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if (conversation.title or "").strip().lower() == "new chat":
        auto_title = msg_in.content.strip().splitlines()[0][:60]
        if auto_title:
            await ConversationService.update_conversation_title(
                db,
                conversation=conversation,
                title=auto_title,
            )

    await ConversationService.add_message(
        db,
        conversation_id=conversation_id,
        role="user",
        content=msg_in.content,
    )

    history = await ConversationService.list_messages(db, conversation_id=conversation_id)
    messages = [{"role": m.role, "content": m.content} for m in history]

    query_embedding = await llm_service.create_single_embedding(msg_in.content)
    search_results = vector_db.search(
        query_vector=query_embedding,
        user_id=current_user.id,
    )

    context_parts = []
    for result in search_results:
        payload = result.get("payload") or {}
        context_parts.append(
            f"[Document: {payload.get('title', 'Unknown')}]\n{payload.get('content', '')}"
        )
    context = "\n\n".join(context_parts)
    if context:
        messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    f"Use the following context to answer the user's question:\n\n{context}"
                ),
            },
        )

    response = await llm_service.chat_completion(messages=messages)

    assistant_message = await ConversationService.add_message(
        db,
        conversation_id=conversation_id,
        role="assistant",
        content=response["content"],
        model=response.get("model"),
    )

    conversation.updated_at = datetime.now(timezone.utc)
    await db.flush()

    await db.commit()
    return SendMessageResponse(
        conversation_id=conversation_id,
        assistant_message=assistant_message,
    )
