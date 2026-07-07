"""Integration tests for document ingestion pipeline (mock S3 + Qdrant)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestIngestPipeline:
    @patch("app.rag.ingest.object_storage")
    @patch("app.rag.ingest.embed_texts")
    @patch("app.rag.ingest.vector_db")
    async def test_index_document_full_flow(self, mock_vdb, mock_embed, mock_storage):
        from app.rag.ingest import index_document

        doc_id = uuid4()
        user_id = uuid4()

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.user_id = user_id
        mock_doc.title = "Test Document"
        mock_doc.content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        mock_doc.file_path = "docs/test.pdf"
        mock_doc.file_type = "application/pdf"
        mock_doc.embedding_status = "pending"

        mock_vdb.get_by_document_id.return_value = []
        mock_embed.return_value = [[0.1] * 1536]

        mock_db = AsyncMock()
        mock_service = MagicMock()
        mock_service.get_by_id = AsyncMock(return_value=mock_doc)
        mock_service.mark_indexing = AsyncMock()
        mock_service.mark_indexed = AsyncMock()

        with patch("app.rag.ingest.DocumentService", mock_service):
            await index_document(mock_db, doc_id)

        mock_service.mark_indexing.assert_called_once()
        mock_embed.assert_called_once()
        mock_vdb.upsert_vectors.assert_called_once()

        payloads = mock_vdb.upsert_vectors.call_args.kwargs["payloads"]
        for payload in payloads:
            assert payload["user_id"] == str(user_id)
            assert payload["document_id"] == str(doc_id)
            assert "chunk_hash" in payload

    @patch("app.rag.ingest.object_storage")
    @patch("app.rag.ingest.embed_texts")
    @patch("app.rag.ingest.vector_db")
    async def test_index_empty_content(self, mock_vdb, mock_embed, mock_storage):
        from app.rag.ingest import index_document

        doc_id = uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.user_id = uuid4()
        mock_doc.title = "Empty Doc"
        mock_doc.content = ""
        mock_doc.embedding_status = "pending"

        mock_db = AsyncMock()
        mock_service = MagicMock()
        mock_service.get_by_id = AsyncMock(return_value=mock_doc)
        mock_service.mark_indexing = AsyncMock()
        mock_service.mark_indexed = AsyncMock()

        with patch("app.rag.ingest.DocumentService", mock_service):
            await index_document(mock_db, doc_id)

        mock_vdb.delete_by_document_id.assert_called_once_with(doc_id)
        mock_embed.assert_not_called()
        mock_service.mark_indexed.assert_called_once_with(mock_db, mock_doc, chunk_count=0)

    @patch("app.rag.ingest.object_storage")
    @patch("app.rag.ingest.embed_texts")
    @patch("app.rag.ingest.vector_db")
    async def test_incremental_reindex_skips_unchanged(self, mock_vdb, mock_embed, mock_storage):
        """Chunks that haven't changed should not be re-embedded."""
        import hashlib

        from app.rag.ingest import index_document

        doc_id = uuid4()
        user_id = uuid4()
        content = "Existing chunk content."
        chunk_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.user_id = user_id
        mock_doc.title = "Doc"
        mock_doc.content = content
        mock_doc.embedding_status = "pending"

        mock_vdb.get_by_document_id.return_value = [
            {"id": "existing-point", "payload": {"chunk_hash": chunk_hash}}
        ]

        mock_db = AsyncMock()
        mock_service = MagicMock()
        mock_service.get_by_id = AsyncMock(return_value=mock_doc)
        mock_service.mark_indexing = AsyncMock()
        mock_service.mark_indexed = AsyncMock()

        with patch("app.rag.ingest.DocumentService", mock_service):
            await index_document(mock_db, doc_id)

        mock_embed.assert_not_called()
        mock_vdb.upsert_vectors.assert_not_called()
        mock_vdb.delete_by_ids.assert_not_called()

    @patch("app.rag.ingest.object_storage")
    @patch("app.rag.ingest.embed_texts")
    @patch("app.rag.ingest.vector_db")
    async def test_stale_chunks_deleted(self, mock_vdb, mock_embed, mock_storage):
        """Old chunks that no longer match should be deleted."""
        from app.rag.ingest import index_document

        doc_id = uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.user_id = uuid4()
        mock_doc.title = "Doc"
        mock_doc.content = "New content entirely."
        mock_doc.embedding_status = "pending"

        mock_vdb.get_by_document_id.return_value = [
            {"id": "old-point", "payload": {"chunk_hash": "old-hash-that-wont-match"}}
        ]
        mock_embed.return_value = [[0.1] * 1536]

        mock_db = AsyncMock()
        mock_service = MagicMock()
        mock_service.get_by_id = AsyncMock(return_value=mock_doc)
        mock_service.mark_indexing = AsyncMock()
        mock_service.mark_indexed = AsyncMock()

        with patch("app.rag.ingest.DocumentService", mock_service):
            await index_document(mock_db, doc_id)

        mock_vdb.delete_by_ids.assert_called_once_with(["old-point"])
        mock_embed.assert_called_once()
        mock_vdb.upsert_vectors.assert_called_once()

    @patch("app.rag.ingest.object_storage")
    @patch("app.rag.ingest.extract_text_from_bytes")
    @patch("app.rag.ingest.embed_texts")
    @patch("app.rag.ingest.vector_db")
    async def test_ingest_document_full_pipeline(
        self, mock_vdb, mock_embed, mock_extract, mock_storage
    ):
        """Full ingest: download → extract → chunk → embed → upsert."""
        from app.rag.ingest import ingest_document

        doc_id = uuid4()
        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.user_id = uuid4()
        mock_doc.title = "PDF Doc"
        mock_doc.content = None
        mock_doc.file_path = "uploads/test.pdf"
        mock_doc.file_type = "application/pdf"
        mock_doc.embedding_status = "pending"
        mock_doc.content_hash = None

        mock_storage.download.return_value = b"fake pdf content"
        mock_extract.return_value = "Extracted text from PDF document. This is useful content."
        mock_vdb.get_by_document_id.return_value = []
        mock_embed.return_value = [[0.1] * 1536]

        mock_db = AsyncMock()
        mock_service = MagicMock()
        mock_service.get_by_id = AsyncMock(return_value=mock_doc)
        mock_service.mark_indexing = AsyncMock()
        mock_service.mark_indexed = AsyncMock()

        with patch("app.rag.ingest.DocumentService", mock_service):
            await ingest_document(mock_db, doc_id)

        mock_storage.download.assert_called_once_with("uploads/test.pdf")
        mock_extract.assert_called_once_with(b"fake pdf content", "application/pdf")
        mock_embed.assert_called_once()
        mock_vdb.upsert_vectors.assert_called_once()
