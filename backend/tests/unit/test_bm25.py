"""Unit tests for app.rag.bm25."""

from app.rag.bm25 import BM25Index, _tokenize


class TestTokenize:
    def test_basic_tokenization(self):
        tokens = _tokenize("Hello World! This is a test.")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens

    def test_removes_stop_words(self):
        tokens = _tokenize("the quick brown fox is a very good animal")
        assert "the" not in tokens
        assert "is" not in tokens
        assert "a" not in tokens
        assert "very" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens

    def test_removes_single_char_tokens(self):
        tokens = _tokenize("I am a b c person")
        assert "i" not in tokens
        assert "b" not in tokens
        assert "c" not in tokens

    def test_lowercases(self):
        tokens = _tokenize("RAG Platform RETRIEVAL")
        assert "rag" in tokens
        assert "platform" in tokens
        assert "retrieval" in tokens

    def test_empty_string(self):
        assert _tokenize("") == []


class TestBM25Index:
    def test_search_returns_relevant_results(self):
        corpus = [
            {"id": "1", "content": "machine learning algorithms classification"},
            {"id": "2", "content": "web development react javascript frontend"},
            {"id": "3", "content": "deep learning neural networks classification"},
        ]
        index = BM25Index(corpus)
        results = index.search("machine learning classification")
        assert len(results) > 0
        assert results[0]["id"] in ("1", "3")

    def test_search_empty_corpus(self):
        index = BM25Index([])
        results = index.search("test query")
        assert results == []

    def test_search_no_match(self):
        corpus = [
            {"id": "1", "content": "alpha beta gamma delta"},
        ]
        index = BM25Index(corpus)
        results = index.search("xyzzy qwerty")
        assert results == []

    def test_search_respects_top_k(self):
        corpus = [
            {"id": str(i), "content": f"document about topic {i} retrieval augmented generation"}
            for i in range(20)
        ]
        index = BM25Index(corpus)
        results = index.search("retrieval augmented generation", top_k=3)
        assert len(results) <= 3

    def test_results_have_expected_keys(self):
        corpus = [
            {"id": "abc", "content": "python programming language"},
            {"id": "def", "content": "java enterprise development"},
            {"id": "ghi", "content": "rust systems programming"},
        ]
        index = BM25Index(corpus)
        results = index.search("python programming")
        assert len(results) >= 1
        assert "id" in results[0]
        assert "score" in results[0]
        assert "payload" in results[0]
        assert results[0]["score"] > 0

    def test_search_with_only_stop_words_query(self):
        corpus = [
            {"id": "1", "content": "python programming"},
        ]
        index = BM25Index(corpus)
        results = index.search("the is a")
        assert results == []
