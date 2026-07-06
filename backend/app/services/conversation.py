"""Service layer for conversation and message CRUD operations."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


class ConversationService:
    """Handles all database operations for conversations and messages."""

    @staticmethod
    async def create_conversation(
        db: AsyncSession, *, user_id: UUID, title: str | None = None
    ) -> Conversation:
        """Create a new conversation for the given user.

        Args:
            db: Async database session.
            user_id: Owner of the conversation.
            title: Optional title (defaults to "New chat").

        Returns:
            The newly created Conversation instance.
        """
        conversation = Conversation(user_id=user_id, title=title or "New chat")
        db.add(conversation)
        await db.flush()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def delete_conversation(db: AsyncSession, *, conversation: Conversation) -> None:
        """Delete a conversation and all its messages.

        Args:
            db: Async database session.
            conversation: The conversation to delete.
        """
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
        """List conversations for a user with pagination.

        Args:
            db: Async database session.
            user_id: The user whose conversations to list.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Tuple of (conversations list, total count).
        """
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
        """Get a single conversation owned by the user.

        Args:
            db: Async database session.
            conversation_id: ID of the conversation to fetch.
            user_id: Owner constraint (prevents cross-user access).

        Returns:
            The Conversation if found and owned by user, else None.
        """
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_conversation_title(
        db: AsyncSession,
        *,
        conversation: Conversation,
        title: str,
    ) -> Conversation:
        """Update the title of an existing conversation.

        Args:
            db: Async database session.
            conversation: The conversation to update.
            title: New title value.

        Returns:
            The updated Conversation instance.
        """
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
        """Append a message to a conversation.

        Args:
            db: Async database session.
            conversation_id: ID of the parent conversation.
            role: Message role ("user" or "assistant").
            content: Message text content.
            model: LLM model used (for assistant messages).

        Returns:
            The newly created Message instance.
        """
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
        """List all messages in a conversation.

        Args:
            db: Async database session.
            conversation_id: The conversation to list messages for.
            newest_first: If True, order by newest first.

        Returns:
            List of Message instances ordered by creation time.
        """
        order_by = Message.created_at.desc() if newest_first else Message.created_at.asc()
        result = await db.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(order_by)
        )
        return list(result.scalars().all())
