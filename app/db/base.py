"""
SQLAlchemy declarative base and model imports.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


from app.models.document import Document  # noqa: E402, F401

# Import all models here for Alembic autogenerate
from app.models.user import User  # noqa: E402, F401
