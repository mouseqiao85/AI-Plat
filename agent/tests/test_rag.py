"""Tests for the RAG system."""
import pytest
from app.rag.document import Document, split_text, load_text


class TestDocument:
    def test_document_creation(self):
        doc = Document(id="1", content="test content", metadata={"source": "test"})
        assert doc.id == "1"
        assert doc.content == "test content"
        assert doc.metadata["source"] == "test"


class TestSplitText:
    def test_short_text(self):
        chunks = split_text("short text", chunk_size=500)
        assert len(chunks) == 1
        assert chunks[0] == "short text"

    def test_long_text(self):
        long_text = "A" * 1000
        chunks = split_text(long_text, chunk_size=500, overlap=50)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 500


class TestRetriever:
    def test_add_and_query(self):
        from app.rag.retriever import Retriever
        r = Retriever()
        docs = [
            Document(id="1", content="Python programming", embedding=[0.1] * 32),
            Document(id="2", content="JavaScript tutorial", embedding=[0.2] * 32),
        ]
        r.add_documents(docs)
        results = r.query("Python", k=1)
        assert len(results) == 1

    def test_empty_retriever(self):
        from app.rag.retriever import Retriever
        r = Retriever()
        results = r.query("test")
        assert len(results) == 0
