"""
RAG Pipeline — chunks runbook documents and past incidents, embeds them
with Azure OpenAI, and stores them in the Azure Database for PostgreSQL
(pgvector) knowledge base.

Run this script once (or when the knowledge base changes):
    python -m backend.rag.pipeline

Requires DATABASE_URL to point at a Postgres server with the `vector`
extension available (on Azure: allowlist it via the `azure.extensions`
server parameter, then `CREATE EXTENSION IF NOT EXISTS vector;`).
"""
import json
import logging
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_postgres import PGVector

from backend.config import get_settings
from backend.rag.vectorstore import get_embeddings

logger = logging.getLogger(__name__)
settings = get_settings()

KB_DIR = Path(__file__).parent / "knowledge_base"
RUNBOOKS_DIR = KB_DIR / "runbooks"
PAST_INCIDENTS_FILE = KB_DIR / "past_incidents.json"


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks


def load_documents() -> List[Document]:
    """Load all runbook Markdown files and past incidents as LangChain Documents."""
    docs: List[Document] = []

    # ── Load runbooks ────────────────────────────────────────
    for md_file in RUNBOOKS_DIR.glob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        for i, chunk in enumerate(chunk_text(text, settings.chunk_size, settings.chunk_overlap)):
            docs.append(Document(page_content=chunk, metadata={"source": f"runbook:{md_file.stem}:{i}"}))
        logger.info(f"Loaded runbook: {md_file.name}")

    # ── Load past incidents ──────────────────────────────────
    if PAST_INCIDENTS_FILE.exists():
        incidents = json.loads(PAST_INCIDENTS_FILE.read_text(encoding="utf-8"))
        for inc in incidents:
            summary = (
                f"Ticket: {inc.get('ticket_id')} | {inc.get('title')} | "
                f"Service: {inc.get('service')} | "
                f"Root Cause: {inc.get('root_cause')} | "
                f"Resolution: {inc.get('resolution')}"
            )
            docs.append(Document(page_content=summary, metadata={"source": f"incident:{inc.get('ticket_id')}"}))
        logger.info(f"Loaded {len(incidents)} past incidents")

    return docs


def build_index() -> None:
    """(Re)build the pgvector collection from knowledge base documents."""
    logger.info("Building RAG index in Azure Postgres (pgvector)...")

    if not settings.database_url:
        logger.error("DATABASE_URL is not set — cannot build the pgvector index.")
        return

    docs = load_documents()
    if not docs:
        logger.error("No documents found in knowledge base!")
        return

    logger.info(f"Embedding {len(docs)} chunks via Azure OpenAI and writing to pgvector...")
    # pre_delete_collection=True gives a clean rebuild each run (idempotent).
    PGVector.from_documents(
        documents=docs,
        embedding=get_embeddings(),
        collection_name=settings.pg_collection_name,
        connection=settings.database_url,
        use_jsonb=True,
        pre_delete_collection=True,
    )

    logger.info(
        "Index built: %d chunks -> pgvector collection '%s'",
        len(docs),
        settings.pg_collection_name,
    )


class RAGPipeline:
    """Wrapper to (re)build the pgvector index programmatically."""

    def build(self) -> None:
        build_index()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    build_index()
