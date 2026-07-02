from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


class ChatService:
    @staticmethod
    async def create_conversation(
        db: AsyncSession, *, user_id: UUID, title: str | None = None
    ) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title or "New chat")
        db.add(conversation)
        await db.flush()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def delete_conversation(db: AsyncSession, *, conversation: Conversation) -> None:
        await db.execute(delete(Message).where(Message.conversation_id == conversation.id))
        await db.delete(conversation)
        await db.flush()

    @staticmethod
    async def list_conversations_for_user(
        db: AsyncSession,
        *,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Conversation], int]:
        offset = (page - 1) * page_size

        total_result = await db.execute(
            select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)
        )
        total = int(total_result.scalar_one())

        items_result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(items_result.scalars().all())
        return items, total

    @staticmethod
    async def get_conversation_for_user(
        db: AsyncSession, *, conversation_id: UUID, user_id: UUID
    ) -> Conversation | None:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conv: Conversation | None = result.scalar_one_or_none()
        return conv

    @staticmethod
    async def update_conversation_title(
        db: AsyncSession,
        *,
        conversation: Conversation,
        title: str,
    ) -> Conversation:
        conversation.title = title
        await db.flush()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def add_message(
        db: AsyncSession,
        *,
        conversation_id: UUID,
        role: str,
        content: str,
        model: str | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
        )
        db.add(msg)
        await db.flush()
        await db.refresh(msg)
        return msg

    @staticmethod
    async def list_messages(
        db: AsyncSession, *, conversation_id: UUID, newest_first: bool = False
    ) -> list[Message]:
        order_by = Message.created_at.desc() if newest_first else Message.created_at.asc()
        result = await db.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(order_by)
        )
        return list(result.scalars().all())
