"""Pytest configuration and fixtures for unit + integration tests.

Uses async PostgreSQL-compatible patterns (aiosqlite for isolation),
mocked OpenAI via unittest.mock, and mocked Qdrant (in-memory stub).
"""

from typing import AsyncGenerator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture()
async def db_engine():
    """Create async engine with fresh schema per test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden DB dependency."""
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture()
async def auth_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated test client — separate instance with auth headers.

    Creates its own AsyncClient (not sharing with `client` fixture)
    to avoid header mutation leaking between fixtures.
    """
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        user_data = {
            "email": f"test_{uuid4().hex[:8]}@example.com",
            "username": f"user_{uuid4().hex[:8]}",
            "password": "testpassword123",
        }
        await ac.post("/api/v1/auth/register", json=user_data)
        login_resp = await ac.post(
            "/api/v1/auth/login",
            data={"username": user_data["email"], "password": user_data["password"]},
        )
        token = login_resp.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture()
def mock_vector_db():
    """Mock Qdrant vector DB with in-memory storage."""
    storage: list[dict] = []

    def fake_upsert(vectors, payloads, ids=None):
        if ids is None:
            ids = [str(uuid4()) for _ in vectors]
        for id_, vector, payload in zip(ids, vectors, payloads):
            storage.append({"id": id_, "vector": vector, "payload": payload})

    def fake_search(query_vector, top_k=5, score_threshold=0.7, user_id=None):
        results = []
        for item in storage:
            if user_id and item["payload"].get("user_id") != str(user_id):
                continue
            results.append({"id": item["id"], "score": 0.85, "payload": item["payload"]})
        return results[:top_k]

    def fake_delete_by_document_id(document_id):
        nonlocal storage
        storage = [s for s in storage if s["payload"].get("document_id") != str(document_id)]

    def fake_get_by_document_id(document_id):
        return [
            {"id": s["id"], "payload": s["payload"]}
            for s in storage
            if s["payload"].get("document_id") == str(document_id)
        ]

    def fake_delete_by_ids(point_ids):
        nonlocal storage
        storage = [s for s in storage if s["id"] not in point_ids]

    mock = MagicMock()
    mock.upsert_vectors = MagicMock(side_effect=fake_upsert)
    mock.search = MagicMock(side_effect=fake_search)
    mock.delete_by_document_id = MagicMock(side_effect=fake_delete_by_document_id)
    mock.get_by_document_id = MagicMock(side_effect=fake_get_by_document_id)
    mock.delete_by_ids = MagicMock(side_effect=fake_delete_by_ids)
    mock._storage = storage

    with (
        patch("app.utils.vector_db.vector_db", mock),
        patch("app.rag.retriever.vector_db", mock),
        patch("app.rag.ingest.vector_db", mock),
    ):
        yield mock
