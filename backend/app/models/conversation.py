"""Conversation model — groups messages into a chat thread per user."""

from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import UUIDTimestampBase


class Conversation(UUIDTimestampBase):
    __tablename__ = "conversations"

    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New chat")
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
