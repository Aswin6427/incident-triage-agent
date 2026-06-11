"""
RAGRetriever — loads the pre-built FAISS index and performs
semantic similarity search at query time.
"""
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import faiss
from openai import AzureOpenAI

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

INDEX_PATH = Path(settings.faiss_index_path)


class RAGRetriever:
    """Semantic search over the pre-built FAISS knowledge base."""

    def __init__(self):
        self._index: Optional[faiss.Index] = None
        self._texts: List[str] = []
        self._sources: List[str] = []
        self._client: Optional[AzureOpenAI] = None
        self._load_index()

    def _get_client(self) -> Optional[AzureOpenAI]:
        if self._client is not None:
            return self._client
        if not settings.azure_openai_api_key or not settings.azure_openai_endpoint:
            logger.warning("[RAGRetriever] Azure OpenAI credentials not configured")
            return None
        try:
            self._client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
        except Exception as exc:
            logger.error(f"[RAGRetriever] Failed to create OpenAI client: {exc}")
        return self._client

    def _load_index(self) -> None:
        """Load FAISS index and metadata from disk."""
        index_file = INDEX_PATH / "index.faiss"
        meta_file = INDEX_PATH / "metadata.pkl"

        if not index_file.exists():
            logger.warning(
                f"FAISS index not found at {index_file}. "
                "Run: python -m backend.rag.pipeline"
            )
            return

        try:
            self._index = faiss.read_index(str(index_file))
            with open(meta_file, "rb") as f:
                meta = pickle.load(f)
            self._texts = meta["texts"]
            self._sources = meta["sources"]
            logger.info(f"✅ FAISS index loaded: {self._index.ntotal} vectors")
        except Exception as exc:
            logger.error(f"Failed to load FAISS index: {exc}")

    def _embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string."""
        client = self._get_client()
        if client is None:
            raise RuntimeError("OpenAI client not available")
        response = client.embeddings.create(
            input=[query],
            model=settings.azure_openai_embedding_deployment,
        )
        return np.array([response.data[0].embedding], dtype=np.float32)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Return top-k most relevant chunks for the query."""
        if self._index is None or self._index.ntotal == 0:
            logger.warning("[RAGRetriever] Index not available, returning empty results")
            return []

        if self._get_client() is None:
            logger.warning("[RAGRetriever] No OpenAI client, returning empty results")
            return []

        try:
            query_vec = self._embed_query(query)
            distances, indices = self._index.search(query_vec, top_k)

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(self._texts):
                    continue
                results.append(
                    {
                        "text": self._texts[idx],
                        "source": self._sources[idx],
                        "distance": float(dist),
                        "score": round(1.0 / (1.0 + float(dist)), 4),  # normalised similarity
                    }
                )
            return results

        except Exception as exc:
            logger.error(f"[RAGRetriever] Search failed: {exc}")
            return []
