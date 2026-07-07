"""FastAPI-Users configuration — JWT auth backend, UserManager, and dependencies."""

import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User


async def get_user_db(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:  # type: ignore[type-arg]
    """Provide SQLAlchemy user database adapter for FastAPI-Users."""
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Handles user lifecycle events (create, verify, reset password)."""

    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY


async def get_user_manager(
    user_db: Annotated[SQLAlchemyUserDatabase, Depends(get_user_db)],  # type: ignore[type-arg]
) -> AsyncGenerator[UserManager, None]:
    """FastAPI dependency that yields a UserManager instance."""
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def get_jwt_strategy() -> JWTStrategy:  # type: ignore[type-arg]
    """Create JWT strategy with token lifetime from config."""
    return JWTStrategy(
        secret=settings.SECRET_KEY,
        lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
