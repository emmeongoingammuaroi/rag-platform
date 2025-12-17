"""
Pydantic schemas for AI endpoints.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Chat message schema."""

    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    """Chat completion request schema."""

    messages: list[ChatMessage]
    model: str | None = None
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, gt=0, le=4000)
    stream: bool = False


class ChatResponse(BaseModel):
    """Chat completion response schema."""

    id: str
    model: str
    content: str
    role: str = "assistant"
    finish_reason: str
    usage: dict[str, int] | None = None


class RAGChatRequest(ChatRequest):
    """RAG-enhanced chat request schema."""

    use_rag: bool = True
    top_k: int = Field(5, ge=1, le=20)


class EmbeddingRequest(BaseModel):
    """Embedding generation request schema."""

    input: str | list[str]
    model: str | None = None


class EmbeddingResponse(BaseModel):
    """Embedding generation response schema."""

    embeddings: list[list[float]]
    model: str
    usage: dict[str, int]


class SemanticSearchRequest(BaseModel):
    """Semantic search request schema."""

    query: str
    top_k: int = Field(5, ge=1, le=20)
    score_threshold: float = Field(0.7, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """Single search result schema."""

    document_id: UUID
    title: str
    content: str
    score: float


class SemanticSearchResponse(BaseModel):
    """Semantic search response schema."""

    results: list[SearchResult]
    query: str
