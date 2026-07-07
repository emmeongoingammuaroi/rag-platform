"""Integration tests for RAG retrieval flow: query → embed → search → rerank → results."""

from unittest.mock import patch
from uuid import uuid4


class TestRetrievalFlow:
    @patch("app.utils.tracing.settings")
    @patch("app.rag.retriever.rerank")
    @patch("app.rag.retriever.embed_with_hyde")
    @patch("app.rag.retriever.vector_db")
    @patch("app.rag.retriever.settings")
    async def test_full_retrieval_no_reranker(
        self, mock_settings, mock_vdb, mock_embed, mock_rerank, mock_tracing_settings
    ):
        from app.rag.retriever import retrieve

        mock_settings.RERANKER_ENABLED = False
        mock_settings.HYDE_ENABLED = False
        mock_settings.RETRIEVER_INITIAL_TOP_K = 20
        mock_settings.OBSERVABILITY_PROVIDER = "none"
        mock_tracing_settings.OBSERVABILITY_PROVIDER = "none"

        user_id = uuid4()
        mock_embed.return_value = [0.1] * 1536
        mock_vdb.search.return_value = [
            {"id": "p1", "score": 0.92, "payload": {"content": "Chunk 1", "title": "Doc A"}},
            {"id": "p2", "score": 0.88, "payload": {"content": "Chunk 2", "title": "Doc B"}},
        ]

        results = await retrieve("What is RAG?", user_id=user_id, top_k=5)

        mock_embed.assert_called_once_with("What is RAG?")
        mock_vdb.search.assert_called_once()
        call_kwargs = mock_vdb.search.call_args.kwargs
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["top_k"] == 5
        mock_rerank.assert_not_called()
        assert len(results) == 2

    @patch("app.utils.tracing.settings")
    @patch("app.rag.retriever.rerank")
    @patch("app.rag.retriever.embed_with_hyde")
    @patch("app.rag.retriever.vector_db")
    @patch("app.rag.retriever.settings")
    async def test_full_retrieval_with_reranker(
        self, mock_settings, mock_vdb, mock_embed, mock_rerank, mock_tracing_settings
    ):
        from app.rag.retriever import retrieve

        mock_settings.RERANKER_ENABLED = True
        mock_settings.HYDE_ENABLED = False
        mock_settings.RETRIEVER_INITIAL_TOP_K = 20
        mock_settings.RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        mock_settings.OBSERVABILITY_PROVIDER = "none"
        mock_tracing_settings.OBSERVABILITY_PROVIDER = "none"

        user_id = uuid4()
        mock_embed.return_value = [0.1] * 1536
        initial_results = [
            {"id": f"p{i}", "score": 0.9 - i * 0.02, "payload": {"content": f"C{i}"}}
            for i in range(10)
        ]
        mock_vdb.search.return_value = initial_results
        mock_rerank.return_value = initial_results[:3]

        results = await retrieve("test query", user_id=user_id, top_k=3)

        mock_vdb.search.assert_called_once()
        assert mock_vdb.search.call_args.kwargs["top_k"] == 20
        mock_rerank.assert_called_once_with("test query", initial_results, top_k=3)
        assert len(results) == 3

    @patch("app.utils.tracing.settings")
    @patch("app.rag.retriever.rerank")
    @patch("app.rag.retriever.embed_with_hyde")
    @patch("app.rag.retriever.vector_db")
    @patch("app.rag.retriever.settings")
    async def test_empty_results(
        self, mock_settings, mock_vdb, mock_embed, mock_rerank, mock_tracing_settings
    ):
        from app.rag.retriever import retrieve

        mock_settings.RERANKER_ENABLED = True
        mock_settings.HYDE_ENABLED = False
        mock_settings.RETRIEVER_INITIAL_TOP_K = 20
        mock_settings.OBSERVABILITY_PROVIDER = "none"
        mock_tracing_settings.OBSERVABILITY_PROVIDER = "none"

        mock_embed.return_value = [0.1] * 1536
        mock_vdb.search.return_value = []

        results = await retrieve("unknown topic", user_id=uuid4())
        assert results == []
        mock_rerank.assert_not_called()


class TestFormatContext:
    def test_format_context_with_results(self):
        from app.rag.retriever import format_context

        results = [
            {"id": "1", "score": 0.9, "payload": {"title": "Doc A", "content": "Content A"}},
            {"id": "2", "score": 0.8, "payload": {"title": "Doc B", "content": "Content B"}},
        ]
        ctx = format_context(results)
        assert "[Document: Doc A]" in ctx
        assert "Content A" in ctx
        assert "[Document: Doc B]" in ctx
        assert "Content B" in ctx

    def test_format_context_empty(self):
        from app.rag.retriever import format_context

        assert format_context([]) == ""

    def test_format_context_missing_fields(self):
        from app.rag.retriever import format_context

        results = [{"id": "1", "score": 0.9, "payload": {}}]
        ctx = format_context(results)
        assert "[Document: Unknown]" in ctx
