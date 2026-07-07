"""Unit tests for app.rag.reranker — ordering, top_k, empty input."""

from unittest.mock import MagicMock, patch

import numpy as np

from app.rag.reranker import rerank


def _make_results(n: int) -> list[dict]:
    """Generate mock search results."""
    return [
        {
            "id": f"point-{i}",
            "score": 0.9 - i * 0.05,
            "payload": {"content": f"Document content {i}", "title": f"Doc {i}"},
        }
        for i in range(n)
    ]


class TestRerankerDisabled:
    @patch("app.rag.reranker.settings")
    def test_disabled_returns_top_k_slice(self, mock_settings):
        mock_settings.RERANKER_ENABLED = False
        results = _make_results(10)
        output = rerank("query", results, top_k=3)
        assert len(output) == 3
        assert output == results[:3]

    @patch("app.rag.reranker.settings")
    def test_disabled_returns_all_if_fewer_than_top_k(self, mock_settings):
        mock_settings.RERANKER_ENABLED = False
        results = _make_results(2)
        output = rerank("query", results, top_k=5)
        assert len(output) == 2


class TestRerankerEmpty:
    @patch("app.rag.reranker.settings")
    def test_empty_results_returns_empty_when_disabled(self, mock_settings):
        mock_settings.RERANKER_ENABLED = False
        output = rerank("query", [], top_k=5)
        assert output == []

    @patch("app.rag.reranker._get_model")
    @patch("app.rag.reranker.settings")
    def test_empty_results_returns_empty_when_enabled(self, mock_settings, mock_get_model):
        mock_settings.RERANKER_ENABLED = True
        output = rerank("query", [], top_k=5)
        assert output == []
        mock_get_model.assert_not_called()


class TestRerankerEnabled:
    @patch("app.rag.reranker.settings")
    @patch("app.rag.reranker._get_model")
    def test_ordering_correctness(self, mock_get_model, mock_settings):
        mock_settings.RERANKER_ENABLED = True
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.1, 0.9, 0.5, 0.3])
        mock_get_model.return_value = mock_model

        results = _make_results(4)
        output = rerank("test query", results, top_k=4)

        assert output[0]["id"] == "point-1"
        assert output[1]["id"] == "point-2"
        assert output[2]["id"] == "point-3"
        assert output[3]["id"] == "point-0"

    @patch("app.rag.reranker.settings")
    @patch("app.rag.reranker._get_model")
    def test_top_k_limit(self, mock_get_model, mock_settings):
        mock_settings.RERANKER_ENABLED = True
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
        mock_get_model.return_value = mock_model

        results = _make_results(5)
        output = rerank("test query", results, top_k=3)
        assert len(output) == 3

    @patch("app.rag.reranker.settings")
    @patch("app.rag.reranker._get_model")
    def test_rerank_score_added(self, mock_get_model, mock_settings):
        mock_settings.RERANKER_ENABLED = True
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.5, 0.8])
        mock_get_model.return_value = mock_model

        results = _make_results(2)
        output = rerank("test query", results, top_k=2)
        assert "rerank_score" in output[0]
        assert "rerank_score" in output[1]
        assert output[0]["rerank_score"] > output[1]["rerank_score"]

    @patch("app.rag.reranker.settings")
    @patch("app.rag.reranker._get_model")
    def test_pairs_constructed_correctly(self, mock_get_model, mock_settings):
        mock_settings.RERANKER_ENABLED = True
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.5, 0.8])
        mock_get_model.return_value = mock_model

        results = _make_results(2)
        rerank("my query", results, top_k=2)

        call_args = mock_model.predict.call_args[0][0]
        assert call_args[0] == ["my query", "Document content 0"]
        assert call_args[1] == ["my query", "Document content 1"]
