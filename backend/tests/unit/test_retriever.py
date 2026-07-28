"""Unit tests for app.rag.retriever — RRF fusion logic."""

from app.rag.retriever import _reciprocal_rank_fusion


class TestReciprocalRankFusion:
    def test_merges_two_lists(self):
        list_a = [
            {"id": "1", "score": 0.9, "payload": {"content": "a"}},
            {"id": "2", "score": 0.8, "payload": {"content": "b"}},
            {"id": "3", "score": 0.7, "payload": {"content": "c"}},
        ]
        list_b = [
            {"id": "2", "score": 5.0, "payload": {"content": "b"}},
            {"id": "4", "score": 4.0, "payload": {"content": "d"}},
            {"id": "1", "score": 3.0, "payload": {"content": "a"}},
        ]
        results = _reciprocal_rank_fusion([list_a, list_b], k=60)
        ids = [r["id"] for r in results]
        assert "1" in ids
        assert "2" in ids
        assert ids[0] in ("1", "2")

    def test_doc_in_both_lists_ranks_higher(self):
        list_a = [
            {"id": "shared", "score": 0.5, "payload": {"content": "x"}},
            {"id": "only_a", "score": 0.9, "payload": {"content": "y"}},
        ]
        list_b = [
            {"id": "shared", "score": 3.0, "payload": {"content": "x"}},
            {"id": "only_b", "score": 5.0, "payload": {"content": "z"}},
        ]
        results = _reciprocal_rank_fusion([list_a, list_b], k=60)
        assert results[0]["id"] == "shared"

    def test_empty_lists(self):
        results = _reciprocal_rank_fusion([[], []])
        assert results == []

    def test_single_list(self):
        single = [
            {"id": "1", "score": 0.9, "payload": {"content": "a"}},
            {"id": "2", "score": 0.5, "payload": {"content": "b"}},
        ]
        results = _reciprocal_rank_fusion([single], k=60)
        assert len(results) == 2
        assert results[0]["id"] == "1"

    def test_scores_are_rrf_values(self):
        list_a = [{"id": "1", "score": 1.0, "payload": {}}]
        results = _reciprocal_rank_fusion([list_a], k=60)
        expected_score = 1.0 / (60 + 1)
        assert abs(results[0]["score"] - expected_score) < 1e-6
