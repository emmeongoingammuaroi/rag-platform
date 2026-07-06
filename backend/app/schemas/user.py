"""
Pydantic schemas for FastAPI-Users.
"""

import uuid

from fastapi_users import schemas
from pydantic import Field


class UserRead(schemas.BaseUser[uuid.UUID]):
    username: str
    full_name: str | None = None


class UserCreate(schemas.BaseUserCreate):
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str | None = None


class UserUpdate(schemas.BaseUserUpdate):
    username: str | None = Field(None, min_length=3, max_length=100)
    full_name: str | None = None
