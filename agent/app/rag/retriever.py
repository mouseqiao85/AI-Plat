"""In-memory vector store retriever for RAG system."""
import asyncio
import numpy as np
from typing import List, Optional
from app.rag.document import Document
from app.rag.embedding import embedding_service


class Retriever:
    """In-memory vector store with cosine similarity search."""

    def __init__(self):
        self.documents: dict[str, Document] = {}
        self.embeddings: Optional[np.ndarray] = None

    def add_documents(self, docs: List[Document]):
        for doc in docs:
            self.documents[doc.id] = doc
        self._rebuild()

    def _rebuild(self):
        if not self.documents:
            self.embeddings = None
            return
        embeds = []
        for doc in self.documents.values():
            if doc.embedding:
                embeds.append(doc.embedding)
        if embeds:
            self.embeddings = np.array(embeds)

    async def add_and_embed(self, docs: List[Document]):
        texts = [d.content for d in docs]
        embeddings = await embedding_service.embed(texts)
        for doc, emb in zip(docs, embeddings):
            doc.embedding = emb
            self.documents[doc.id] = doc
        self._rebuild()

    def query(self, text: str, k: int = 5) -> List[Document]:
        """Search with synchronous mock embedding for simplicity."""
        if self.embeddings is None and len(self.documents) == 0:
            return []

        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        query_vec = np.array([float(b) / 255.0 for b in h[:32]], dtype=np.float64)
        query_vec = query_vec / (np.linalg.norm(query_vec) or 1.0)

        if self.embeddings is None:
            return list(self.documents.values())[:k]

        norms = np.linalg.norm(self.embeddings, axis=1)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        similarities = np.dot(self.embeddings, query_vec) / (norms * query_norm)
        doc_list = list(self.documents.values())
        top_k = min(k, len(doc_list))
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        return [doc_list[i] for i in top_indices if similarities[i] > 0]

    def clear(self):
        self.documents.clear()
        self.embeddings = None


retriever = Retriever()
