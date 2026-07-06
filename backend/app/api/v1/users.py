"""
User management routers powered by FastAPI-Users.
"""

from fastapi import APIRouter

from app.core.auth import fastapi_users
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])

router.include_router(fastapi_users.get_users_router(UserRead, UserUpdate))
