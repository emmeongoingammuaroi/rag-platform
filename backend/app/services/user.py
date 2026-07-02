"""
User service for business logic.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """User service with repository pattern."""

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: UUID) -> User | None:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        user: User | None = result.scalar_one_or_none()
        return user

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))
        user: User | None = result.scalar_one_or_none()
        return user

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> User | None:
        """Get user by username."""
        result = await db.execute(select(User).where(User.username == username))
        user: User | None = result.scalar_one_or_none()
        return user

    @staticmethod
    async def create(db: AsyncSession, user_in: UserCreate) -> User:
        """Create new user."""
        db_user = User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=get_password_hash(user_in.password),
            full_name=user_in.full_name,
        )
        db.add(db_user)
        await db.flush()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def update(db: AsyncSession, user: User, user_in: UserUpdate) -> User:
        """Update user."""
        update_data = user_in.model_dump(exclude_unset=True)

        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
        """Authenticate user with email and password."""
        user = await UserService.get_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def is_active(user: User) -> bool:
        """Check if user is active."""
        active: bool = user.is_active
        return active
