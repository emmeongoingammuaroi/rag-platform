"""Unit tests for app.rag.query_rewriter."""

from unittest.mock import AsyncMock, patch

from app.rag.query_rewriter import rewrite_query


class TestRewriteQuery:
    @patch("app.rag.query_rewriter.settings")
    async def test_disabled_returns_original(self, mock_settings):
        mock_settings.QUERY_REWRITER_ENABLED = False
        result = await rewrite_query(
            "what about that?",
            [
                {"role": "user", "content": "Tell me about RAG"},
                {"role": "assistant", "content": "RAG is..."},
                {"role": "user", "content": "what about that?"},
            ],
        )
        assert result == "what about that?"

    @patch("app.rag.query_rewriter.settings")
    async def test_single_message_returns_original(self, mock_settings):
        mock_settings.QUERY_REWRITER_ENABLED = True
        mock_settings.CONTEXT_HISTORY_TURNS = 6
        result = await rewrite_query(
            "What is RAG?",
            [
                {"role": "user", "content": "What is RAG?"},
            ],
        )
        assert result == "What is RAG?"

    @patch("app.rag.query_rewriter.settings")
    @patch("app.rag.query_rewriter.llm_service")
    async def test_rewrites_followup_question(self, mock_llm, mock_settings):
        mock_settings.QUERY_REWRITER_ENABLED = True
        mock_settings.CONTEXT_HISTORY_TURNS = 6
        mock_llm.chat_completion = AsyncMock(
            return_value={"content": "What are the benefits of RAG?"}
        )
        history = [
            {"role": "user", "content": "Tell me about RAG"},
            {"role": "assistant", "content": "RAG stands for Retrieval-Augmented Generation."},
            {"role": "user", "content": "what are its benefits?"},
        ]
        result = await rewrite_query("what are its benefits?", history)
        assert result == "What are the benefits of RAG?"

    @patch("app.rag.query_rewriter.settings")
    @patch("app.rag.query_rewriter.llm_service")
    async def test_fallback_on_error(self, mock_llm, mock_settings):
        mock_settings.QUERY_REWRITER_ENABLED = True
        mock_settings.CONTEXT_HISTORY_TURNS = 6
        mock_llm.chat_completion = AsyncMock(side_effect=RuntimeError("API error"))
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "what about that?"},
        ]
        result = await rewrite_query("what about that?", history)
        assert result == "what about that?"

    @patch("app.rag.query_rewriter.settings")
    @patch("app.rag.query_rewriter.llm_service")
    async def test_fallback_on_empty_response(self, mock_llm, mock_settings):
        mock_settings.QUERY_REWRITER_ENABLED = True
        mock_settings.CONTEXT_HISTORY_TURNS = 6
        mock_llm.chat_completion = AsyncMock(return_value={"content": ""})
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "elaborate"},
        ]
        result = await rewrite_query("elaborate", history)
        assert result == "elaborate"

    @patch("app.rag.query_rewriter.settings")
    @patch("app.rag.query_rewriter.llm_service")
    async def test_uses_zero_temperature(self, mock_llm, mock_settings):
        mock_settings.QUERY_REWRITER_ENABLED = True
        mock_settings.CONTEXT_HISTORY_TURNS = 6
        mock_llm.chat_completion = AsyncMock(return_value={"content": "rewritten"})
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "more"},
        ]
        await rewrite_query("more", history)
        call_args = mock_llm.chat_completion.call_args
        assert call_args.kwargs.get("temperature") == 0.0
