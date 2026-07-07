"""Integration tests for conversation send_message — full flow with mocked RAG."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    """Disable rate limiter for conversation tests (avoids Redis dependency)."""
    from app.core.rate_limit import limiter

    limiter.enabled = False
    yield
    limiter.enabled = True


class TestSendMessage:
    async def test_send_message_full_flow(self, auth_client: AsyncClient, mock_vector_db):
        with (
            patch("app.api.v1.conversations.retrieve", new_callable=AsyncMock) as mock_retrieve,
            patch("app.api.v1.conversations.llm_service") as mock_llm,
        ):
            mock_retrieve.return_value = [
                {
                    "id": "chunk-1",
                    "score": 0.9,
                    "payload": {"title": "Test Doc", "content": "Relevant context here."},
                }
            ]
            mock_llm.chat_completion = AsyncMock(
                return_value={
                    "id": "chatcmpl-test",
                    "model": "gpt-4o-mini",
                    "content": "Based on the context, here is the answer.",
                    "role": "assistant",
                    "finish_reason": "stop",
                    "usage": {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
                }
            )

            # Create conversation
            resp = await auth_client.post(
                "/api/v1/conversations", json={"title": "Test conversation"}
            )
            assert resp.status_code == 201
            conv_id = resp.json()["id"]

            # Send message
            resp = await auth_client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                json={"content": "What is in my documents?"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["conversation_id"] == conv_id
            assert data["assistant_message"]["role"] == "assistant"
            assert "answer" in data["assistant_message"]["content"]

            mock_retrieve.assert_called_once()

    async def test_send_message_conversation_not_found(self, auth_client: AsyncClient):
        fake_id = str(uuid4())
        resp = await auth_client.post(
            f"/api/v1/conversations/{fake_id}/messages",
            json={"content": "Hello"},
        )
        assert resp.status_code == 404

    async def test_send_message_auto_title(self, auth_client: AsyncClient, mock_vector_db):
        with (
            patch("app.api.v1.conversations.retrieve", new_callable=AsyncMock) as mock_retrieve,
            patch("app.api.v1.conversations.llm_service") as mock_llm,
        ):
            mock_retrieve.return_value = []
            mock_llm.chat_completion = AsyncMock(
                return_value={
                    "id": "chatcmpl-test",
                    "model": "gpt-4o-mini",
                    "content": "I can help with that.",
                    "role": "assistant",
                    "finish_reason": "stop",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                }
            )

            # Create with default title
            resp = await auth_client.post("/api/v1/conversations", json={})
            assert resp.status_code == 201
            conv_id = resp.json()["id"]
            assert resp.json()["title"] == "New chat"

            # Send message — should auto-update title
            await auth_client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                json={"content": "How does vector search work?"},
            )

            # Verify title was updated
            resp = await auth_client.get(f"/api/v1/conversations/{conv_id}")
            assert resp.status_code == 200
            assert resp.json()["title"] == "How does vector search work?"


class TestConversationCRUD:
    async def test_create_and_list(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/conversations", json={"title": "Conv 1"})
        assert resp.status_code == 201

        resp = await auth_client.get("/api/v1/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(c["title"] == "Conv 1" for c in data["items"])

    async def test_update_title(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/conversations", json={"title": "Original"})
        conv_id = resp.json()["id"]

        resp = await auth_client.patch(
            f"/api/v1/conversations/{conv_id}", json={"title": "Updated"}
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"

    async def test_delete_conversation(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/conversations", json={"title": "To Delete"})
        conv_id = resp.json()["id"]

        resp = await auth_client.delete(f"/api/v1/conversations/{conv_id}")
        assert resp.status_code == 204

        resp = await auth_client.get(f"/api/v1/conversations/{conv_id}")
        assert resp.status_code == 404
