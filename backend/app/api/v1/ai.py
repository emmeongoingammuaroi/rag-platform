"""
AI endpoints for chat and embeddings.
"""

import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import (
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    RAGChatRequest,
    SearchResult,
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from app.schemas.chat import (
    Conversation,
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    ConversationUpdate,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.ai import ai_service
from app.services.chat import ChatService
from app.utils.vector_db import vector_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/chat", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ChatResponse:
    """
    Generate chat completion.

    Args:
        request: Chat request with messages
        current_user: Current authenticated user

    Returns:
        Chat completion response

    Raises:
        HTTPException: If chat completion fails
    """
    try:
        # Convert Pydantic models to dicts
        messages = [msg.model_dump() for msg in request.messages]

        # Handle streaming
        if request.stream:

            async def generate() -> AsyncGenerator[str, None]:
                async for chunk in ai_service.chat_completion_stream(
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    model=request.model,
                ):
                    yield chunk

            return StreamingResponse(generate(), media_type="text/event-stream")  # type: ignore[return-value]

        # Non-streaming response
        response = await ai_service.chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            model=request.model,
        )

        return ChatResponse(**response)

    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations", response_model=Conversation)
async def create_conversation(
    conversation_in: ConversationCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Conversation:
    conversation = await ChatService.create_conversation(
        db,
        user_id=current_user.id,
        title=conversation_in.title,
    )
    return conversation


@router.get("/conversations", response_model=ConversationList)
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

    items, total = await ChatService.list_conversations_for_user(
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


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConversationDetail:
    conversation = await ChatService.get_conversation_for_user(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await ChatService.list_messages(
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


@router.patch("/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: UUID,
    conversation_in: ConversationUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Conversation:
    conversation = await ChatService.get_conversation_for_user(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    updated = await ChatService.update_conversation_title(
        db,
        conversation=conversation,
        title=conversation_in.title,
    )
    return updated


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    conversation = await ChatService.get_conversation_for_user(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await ChatService.delete_conversation(db, conversation=conversation)
    return None


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
)
async def send_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SendMessageResponse:
    conversation = await ChatService.get_conversation_for_user(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if (conversation.title or "").strip().lower() == "new chat":
        auto_title = request.content.strip().splitlines()[0][:60]
        if auto_title:
            await ChatService.update_conversation_title(
                db,
                conversation=conversation,
                title=auto_title,
            )

    await ChatService.add_message(
        db,
        conversation_id=conversation_id,
        role="user",
        content=request.content,
    )

    history = await ChatService.list_messages(db, conversation_id=conversation_id)
    messages = [{"role": m.role, "content": m.content} for m in history]

    if request.use_rag:
        query_embedding = await ai_service.create_single_embedding(request.content)
        search_results = vector_db.search(
            query_vector=query_embedding,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
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

    response = await ai_service.chat_completion(
        messages=messages,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        model=request.model,
    )

    assistant_message = await ChatService.add_message(
        db,
        conversation_id=conversation_id,
        role="assistant",
        content=response["content"],
        model=response.get("model"),
    )

    conversation.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return SendMessageResponse(
        conversation_id=conversation_id,
        assistant_message=assistant_message,
    )


@router.post("/chat/rag", response_model=ChatResponse)
async def rag_chat_completion(
    request: RAGChatRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChatResponse:
    """
    Generate RAG-enhanced chat completion.

    Args:
        request: RAG chat request with messages
        current_user: Current authenticated user
        db: Database session

    Returns:
        Chat completion response with RAG context

    Raises:
        HTTPException: If chat completion fails
    """
    try:
        # Get last user message for semantic search
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")

        last_user_message = user_messages[-1].content

        # Generate embedding for query
        query_embedding = await ai_service.create_single_embedding(last_user_message)

        # Search vector DB
        search_results = vector_db.search(
            query_vector=query_embedding,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )

        # Build context from search results
        context_parts = []
        for result in search_results:
            payload = result["payload"]
            context_parts.append(
                f"[Document: {payload.get('title', 'Unknown')}]\n{payload.get('content', '')}"
            )

        context = "\n\n".join(context_parts)

        # Inject context into messages
        messages = [msg.model_dump() for msg in request.messages]

        # Add system message with context if context exists
        if context:
            system_message = {
                "role": "system",
                "content": f"Use the following context to answer the user's question:\n\n{context}",
            }
            messages.insert(0, system_message)

        # Generate completion
        response = await ai_service.chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            model=request.model,
        )

        return ChatResponse(**response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(
    request: EmbeddingRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> EmbeddingResponse:
    """
    Generate embeddings for text(s).

    Args:
        request: Embedding request with input text(s)
        current_user: Current authenticated user

    Returns:
        Embedding vectors

    Raises:
        HTTPException: If embedding generation fails
    """
    try:
        # Handle single string or list of strings
        texts = [request.input] if isinstance(request.input, str) else request.input

        # Generate embeddings
        embeddings = await ai_service.create_embeddings(texts, model=request.model)

        return EmbeddingResponse(
            embeddings=embeddings,
            model=request.model or ai_service.embedding_model,
            usage={"total_tokens": sum(len(text.split()) for text in texts)},
        )

    except Exception as e:
        logger.error(f"Embedding generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embeddings/search", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> SemanticSearchResponse:
    """
    Perform semantic search using embeddings.

    Args:
        request: Search request with query
        current_user: Current authenticated user

    Returns:
        Search results

    Raises:
        HTTPException: If search fails
    """
    try:
        # Generate query embedding
        query_embedding = await ai_service.create_single_embedding(request.query)

        # Search vector DB
        search_results = vector_db.search(
            query_vector=query_embedding,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )

        # Format results
        results = []
        for result in search_results:
            payload = result.get("payload") or {}
            raw_document_id = payload.get("document_id")
            if not raw_document_id:
                continue

            try:
                document_id = UUID(str(raw_document_id))
            except ValueError:
                continue

            results.append(
                SearchResult(
                    document_id=document_id,
                    title=payload.get("title", "Unknown"),
                    content=payload.get("content", ""),
                    score=result["score"],
                )
            )

        return SemanticSearchResponse(
            results=results,
            query=request.query,
        )

    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
