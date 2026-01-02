from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)


class ConversationInDB(BaseModel):
    id: UUID
    title: str
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Conversation(ConversationInDB):
    pass


class ConversationList(BaseModel):
    items: list[Conversation]
    total: int
    page: int
    page_size: int
    pages: int


class MessageInDB(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    model: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Message(MessageInDB):
    pass


class ConversationDetail(ConversationInDB):
    messages: list[Message]


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, gt=0, le=4000)
    model: str | None = None
    use_rag: bool = False
    top_k: int = Field(5, ge=1, le=20)
    score_threshold: float = Field(0.2, ge=0.0, le=1.0)


class SendMessageResponse(BaseModel):
    conversation_id: UUID
    assistant_message: Message
