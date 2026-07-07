"""Unit tests for app.rag.hyde — expand output, fallback on error."""

from unittest.mock import AsyncMock, patch

from app.rag.hyde import embed_with_hyde, generate_hypothetical_document


class TestGenerateHypotheticalDocument:
    @patch("app.rag.hyde.llm_service")
    async def test_returns_generated_passage(self, mock_llm):
        mock_llm.chat_completion = AsyncMock(
            return_value={"content": "A hypothetical answer about RAG."}
        )
        result = await generate_hypothetical_document("What is RAG?")
        assert result == "A hypothetical answer about RAG."

    @patch("app.rag.hyde.llm_service")
    async def test_prompt_contains_query(self, mock_llm):
        mock_llm.chat_completion = AsyncMock(return_value={"content": "answer"})
        await generate_hypothetical_document("How does chunking work?")
        call_args = mock_llm.chat_completion.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert "How does chunking work?" in messages[0]["content"]

    @patch("app.rag.hyde.llm_service")
    async def test_uses_low_temperature(self, mock_llm):
        mock_llm.chat_completion = AsyncMock(return_value={"content": "text"})
        await generate_hypothetical_document("test")
        call_args = mock_llm.chat_completion.call_args
        assert call_args.kwargs.get("temperature") == 0.0


class TestEmbedWithHyde:
    @patch("app.rag.hyde.settings")
    @patch("app.rag.hyde._raw_embed_query")
    async def test_disabled_uses_raw_embed(self, mock_embed, mock_settings):
        mock_settings.HYDE_ENABLED = False
        mock_embed.return_value = [0.5] * 1536
        result = await embed_with_hyde("test query")
        assert result == [0.5] * 1536
        mock_embed.assert_called_once_with("test query")

    @patch("app.rag.hyde.settings")
    @patch("app.rag.hyde._raw_embed_query")
    @patch("app.rag.hyde.generate_hypothetical_document")
    async def test_enabled_embeds_hypothetical(self, mock_generate, mock_embed, mock_settings):
        mock_settings.HYDE_ENABLED = True
        mock_generate.return_value = "This is a hypothetical document."
        mock_embed.return_value = [0.7] * 1536
        result = await embed_with_hyde("What is RAG?")
        mock_embed.assert_called_once_with("This is a hypothetical document.")
        assert result == [0.7] * 1536

    @patch("app.rag.hyde.settings")
    @patch("app.rag.hyde._raw_embed_query")
    @patch("app.rag.hyde.generate_hypothetical_document")
    async def test_fallback_on_generation_error(self, mock_generate, mock_embed, mock_settings):
        mock_settings.HYDE_ENABLED = True
        mock_generate.side_effect = RuntimeError("LLM API error")
        mock_embed.return_value = [0.3] * 1536
        result = await embed_with_hyde("test query")
        mock_embed.assert_called_once_with("test query")
        assert result == [0.3] * 1536

    @patch("app.rag.hyde.settings")
    @patch("app.rag.hyde._raw_embed_query")
    @patch("app.rag.hyde.generate_hypothetical_document")
    async def test_fallback_on_empty_generation(self, mock_generate, mock_embed, mock_settings):
        mock_settings.HYDE_ENABLED = True
        mock_generate.return_value = "   "
        mock_embed.return_value = [0.4] * 1536
        result = await embed_with_hyde("test")
        mock_embed.assert_called_once_with("test")
        assert result == [0.4] * 1536
