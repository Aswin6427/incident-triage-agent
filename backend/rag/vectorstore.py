"""
Shared Azure Database for PostgreSQL (+ pgvector) vector store.

Both the ingestion pipeline (backend.rag.pipeline) and the query-time
retriever (backend.rag.retriever) use the SAME collection, so embeddings
written by one are searchable by the other. Embeddings are produced by
Azure OpenAI; the collection dimension therefore matches the configured
embedding deployment (text-embedding-3-small → 1536).
"""
import logging
from functools import lru_cache

from langchain_openai import AzureOpenAIEmbeddings
from langchain_postgres import PGVector

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_embeddings() -> AzureOpenAIEmbeddings:
    """Azure OpenAI embeddings client (same config the agents use)."""
    return AzureOpenAIEmbeddings(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_embedding_deployment,
    )


@lru_cache(maxsize=1)
def get_vectorstore() -> PGVector:
    """Singleton PGVector store bound to the Azure Postgres collection.

    Raises if DATABASE_URL is unset so callers can degrade gracefully.
    """
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set — cannot connect to Postgres")
    return PGVector(
        embeddings=get_embeddings(),
        collection_name=settings.pg_collection_name,
        connection=settings.database_url,
        use_jsonb=True,
    )
