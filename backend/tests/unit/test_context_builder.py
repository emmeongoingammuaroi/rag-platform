"""Unit tests for app.rag.context_builder."""

from unittest.mock import patch

from app.rag.context_builder import (
    _build_document_context,
    _trim_history,
    build_context,
    count_tokens,
)


class TestCountTokens:
    def test_counts_tokens(self):
        count = count_tokens("Hello, world!")
        assert count > 0
        assert isinstance(count, int)

    def test_empty_string(self):
        assert count_tokens("") == 0


class TestBuildDocumentContext:
    def test_formats_chunks_with_metadata(self):
        chunks = [
            {
                "score": 0.92,
                "payload": {
                    "title": "Doc1",
                    "content": "First chunk content",
                    "document_id": "abc-123",
                    "chunk_index": 0,
                },
            },
            {
                "score": 0.85,
                "payload": {
                    "title": "Doc2",
                    "content": "Second chunk content",
                    "document_id": "def-456",
                    "chunk_index": 2,
                },
            },
        ]
        result = _build_document_context(chunks, max_tokens=3000)
        assert "Doc1" in result
        assert "First chunk content" in result
        assert "Doc2" in result
        assert "Second chunk content" in result
        assert "doc_id: abc-123" in result
        assert "chunk: 0" in result
        assert "relevance: 0.920" in result

    def test_empty_chunks(self):
        assert _build_document_context([], max_tokens=3000) == ""

    def test_respects_token_budget(self):
        long_content = "word " * 2000
        chunks = [
            {"payload": {"title": "Long", "content": long_content}},
            {"payload": {"title": "Never", "content": "should not appear"}},
        ]
        result = _build_document_context(chunks, max_tokens=100)
        assert "should not appear" not in result
        assert "..." in result

    def test_missing_payload_keys(self):
        chunks = [{"payload": {}}]
        result = _build_document_context(chunks, max_tokens=3000)
        assert "Unknown" in result


class TestTrimHistory:
    def test_short_history_unchanged(self):
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = _trim_history(history, max_turns=6, max_tokens=10000)
        assert result == history

    def test_trims_to_max_turns(self):
        history = [
            {"role": "user", "content": f"msg {i}"}
            if i % 2 == 0
            else {"role": "assistant", "content": f"reply {i}"}
            for i in range(20)
        ]
        result = _trim_history(history, max_turns=3, max_tokens=10000)
        assert len(result) == 6
        assert result[0] == history[-6]

    def test_trims_by_token_budget(self):
        history = [
            {"role": "user", "content": "short"},
            {"role": "assistant", "content": "x " * 500},
            {"role": "user", "content": "last question"},
        ]
        result = _trim_history(history, max_turns=10, max_tokens=50)
        assert len(result) < len(history)
        assert result[-1]["content"] == "last question"


class TestBuildContext:
    @patch("app.rag.context_builder.settings")
    def test_full_context_assembly(self, mock_settings):
        mock_settings.CONTEXT_MAX_TOKENS = 3000
        mock_settings.CONTEXT_HISTORY_TURNS = 6
        chunks = [
            {"score": 0.9, "payload": {"title": "Doc1", "content": "relevant info"}},
        ]
        chat_history = [
            {"role": "user", "content": "What is RAG?"},
            {"role": "assistant", "content": "RAG is..."},
            {"role": "user", "content": "Tell me more"},
        ]
        messages = build_context(retrieved_chunks=chunks, chat_history=chat_history)
        assert messages[0]["role"] == "system"
        assert "Doc1" in messages[0]["content"]
        assert "relevant info" in messages[0]["content"]
        assert len(messages) >= 4  # system + 3 history

    @patch("app.rag.context_builder.settings")
    def test_system_always_present(self, mock_settings):
        mock_settings.CONTEXT_MAX_TOKENS = 3000
        mock_settings.CONTEXT_HISTORY_TURNS = 6
        chat_history = [
            {"role": "user", "content": "Hello"},
        ]
        messages = build_context(retrieved_chunks=[], chat_history=chat_history)
        assert messages[0]["role"] == "system"
        assert "helpful assistant" in messages[0]["content"]

    @patch("app.rag.context_builder.settings")
    def test_history_trimming(self, mock_settings):
        mock_settings.CONTEXT_MAX_TOKENS = 3000
        mock_settings.CONTEXT_HISTORY_TURNS = 2
        chunks = [{"score": 0.8, "payload": {"title": "D", "content": "c"}}]
        chat_history = [
            {"role": "user", "content": f"msg {i}"}
            if i % 2 == 0
            else {"role": "assistant", "content": f"reply {i}"}
            for i in range(10)
        ]
        messages = build_context(retrieved_chunks=chunks, chat_history=chat_history)
        assert messages[0]["role"] == "system"
        assert len(messages) <= 5  # 1 system + max 4 history (2 turns)
