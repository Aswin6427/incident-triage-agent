"""
RAGRetriever — semantic similarity search over the Azure PostgreSQL
(pgvector) knowledge base populated by backend.rag.pipeline.
"""
import logging
from typing import List, Dict, Any, Optional

from langchain_postgres import PGVector

from backend.config import get_settings
from backend.rag.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGRetriever:
    """Semantic search over the pgvector knowledge base."""

    def __init__(self):
        # Connection is established lazily on first search so importing this
        # module (and constructing the agent graph) never requires a live DB.
        self._store: Optional[PGVector] = None

    def _get_store(self) -> Optional[PGVector]:
        if self._store is not None:
            return self._store
        try:
            self._store = get_vectorstore()
            logger.info("[RAGRetriever] Connected to pgvector collection '%s'", settings.pg_collection_name)
        except Exception as exc:
            logger.error(f"[RAGRetriever] Failed to connect to pgvector store: {exc}")
        return self._store

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Return top-k most relevant chunks for the query.

        Each result keeps the shape consumers expect:
        {text, source, distance, score}.
        """
        store = self._get_store()
        if store is None:
            logger.warning("[RAGRetriever] No vector store available, returning empty results")
            return []

        try:
            hits = store.similarity_search_with_score(query, k=top_k)
            results = []
            for doc, distance in hits:
                results.append(
                    {
                        "text": doc.page_content,
                        "source": doc.metadata.get("source", "unknown"),
                        "distance": float(distance),
                        "score": round(1.0 / (1.0 + float(distance)), 4),  # normalised similarity
                    }
                )
            return results

        except Exception as exc:
            logger.error(f"[RAGRetriever] Search failed: {exc}")
            return []
