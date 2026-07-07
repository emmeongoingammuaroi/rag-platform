"""Unit tests for app.rag.chunker — boundary cases, overlap, sentence splitting."""

from app.rag.chunker import chunk_text


class TestChunkerEmpty:
    def test_empty_string_returns_empty(self):
        assert chunk_text("") == []

    def test_whitespace_only_returns_empty(self):
        assert chunk_text("   \n\n  \t  ") == []

    def test_single_newline_returns_empty(self):
        assert chunk_text("\n") == []


class TestChunkerSingleSentence:
    def test_short_text_below_chunk_size(self):
        text = "Hello world."
        chunks = chunk_text(text, chunk_size=512)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_single_sentence_exact_chunk_size(self):
        text = "a" * 512
        chunks = chunk_text(text, chunk_size=512)
        assert len(chunks) == 1
        assert chunks[0] == text


class TestChunkerBoundary:
    def test_text_exactly_at_chunk_size(self):
        text = "word " * 102  # 510 chars
        text = text[:512]
        chunks = chunk_text(text, chunk_size=512, overlap=0)
        assert len(chunks) == 1

    def test_text_one_over_chunk_size(self):
        text = "a" * 513
        chunks = chunk_text(text, chunk_size=512, overlap=0)
        assert len(chunks) >= 2

    def test_zero_chunk_size_returns_full_text(self):
        text = "Hello world."
        chunks = chunk_text(text, chunk_size=0)
        assert len(chunks) == 1
        assert chunks[0] == text


class TestChunkerOverlap:
    def test_overlap_creates_shared_content(self):
        sentences = ["Sentence one. ", "Sentence two. ", "Sentence three. "]
        text = "".join(sentences * 20)
        chunks = chunk_text(text, chunk_size=100, overlap=30)
        assert len(chunks) > 1
        for i in range(len(chunks) - 1):
            tail = chunks[i][-30:]
            assert tail in chunks[i + 1] or chunks[i + 1].startswith(tail[:10])

    def test_zero_overlap(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunk_text(text, chunk_size=25, overlap=0)
        assert len(chunks) >= 2


class TestChunkerSentenceSplitting:
    def test_respects_paragraph_boundary(self):
        text = "First paragraph content.\n\nSecond paragraph content."
        chunks = chunk_text(text, chunk_size=30, overlap=0)
        assert any("First" in c for c in chunks)
        assert any("Second" in c for c in chunks)

    def test_respects_sentence_boundary(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunk_text(text, chunk_size=40, overlap=0)
        for chunk in chunks:
            assert not chunk.startswith("econd")
            assert not chunk.startswith("hird")

    def test_newline_separator(self):
        text = "Line one.\nLine two.\nLine three.\nLine four.\nLine five."
        chunks = chunk_text(text, chunk_size=25, overlap=0)
        assert len(chunks) >= 2

    def test_multiple_newlines_collapsed(self):
        text = "Para one.\n\n\n\n\nPara two."
        chunks = chunk_text(text, chunk_size=512)
        full = " ".join(chunks)
        assert "\n\n\n" not in full


class TestChunkerCustomSeparators:
    def test_custom_separators(self):
        text = "A|B|C|D|E|F|G|H"
        chunks = chunk_text(text, chunk_size=5, overlap=0, separators=["|"])
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 6  # tolerance for separator

    def test_no_matching_separator_falls_to_char(self):
        text = "abcdefghijklmnop"
        chunks = chunk_text(text, chunk_size=5, overlap=0, separators=["|", ";"])
        assert len(chunks) >= 3


class TestChunkerLargeText:
    def test_large_document(self):
        text = ("This is a test sentence. " * 1000).strip()
        chunks = chunk_text(text, chunk_size=512, overlap=50)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 600  # some tolerance due to sentence boundaries

    def test_no_empty_chunks(self):
        text = "\n\n".join(["Short." for _ in range(100)])
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        assert all(c.strip() for c in chunks)
