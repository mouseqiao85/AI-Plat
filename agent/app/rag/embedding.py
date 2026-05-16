"""Text embedding service for RAG system."""
import numpy as np
from typing import List
from openai import AsyncOpenAI
from app.core.config import settings


class EmbeddingService:
    """Generate text embeddings via LLM API."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        ) if settings.LLM_API_KEY else None

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if self.client is None:
            return self._mock_embed(texts)

        try:
            resp = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
            )
            return [d.embedding for d in resp.data]
        except Exception:
            return self._mock_embed(texts)

    @staticmethod
    def _mock_embed(texts: List[str]) -> List[List[float]]:
        """Generate deterministic mock embeddings for development."""
        embeddings = []
        for text in texts:
            import hashlib
            h = hashlib.sha256(text.encode()).digest()
            vec = np.array([float(b) / 255.0 for b in h[:32]], dtype=np.float64)
            vec = vec / (np.linalg.norm(vec) or 1.0)
            embeddings.append(vec.tolist())
        return embeddings


embedding_service = EmbeddingService()
