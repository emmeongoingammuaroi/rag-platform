"""
AI endpoints for chat and embeddings.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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
from app.services.ai import ai_service
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

            async def generate():
                async for chunk in ai_service.chat_completion_stream(
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    model=request.model,
                ):
                    yield chunk

            return StreamingResponse(generate(), media_type="text/event-stream")

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
