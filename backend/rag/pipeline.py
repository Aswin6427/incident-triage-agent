"""
RAG Pipeline — chunks runbook documents and past incidents,
embeds them with Azure OpenAI, and stores in a FAISS index.

Run this script once (or when knowledge base changes):
    python -m backend.rag.pipeline
"""
import os
import json
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import faiss
from openai import AzureOpenAI

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

KB_DIR = Path(__file__).parent / "knowledge_base"
RUNBOOKS_DIR = KB_DIR / "runbooks"
PAST_INCIDENTS_FILE = KB_DIR / "past_incidents.json"
INDEX_PATH = Path(settings.faiss_index_path)


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


def load_documents() -> List[Dict[str, str]]:
    """Load all runbook Markdown files and past incidents JSON."""
    docs = []

    # ── Load runbooks ────────────────────────────────────────
    for md_file in RUNBOOKS_DIR.glob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        for i, chunk in enumerate(chunk_text(text, settings.chunk_size, settings.chunk_overlap)):
            docs.append({"text": chunk, "source": f"runbook:{md_file.stem}:{i}"})
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
            docs.append({"text": summary, "source": f"incident:{inc.get('ticket_id')}"})
        logger.info(f"Loaded {len(incidents)} past incidents")

    return docs


def embed_texts(texts: List[str]) -> np.ndarray:
    """Embed a list of texts using Azure OpenAI embeddings."""
    client = AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )

    embeddings = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(
            input=batch,
            model=settings.azure_openai_embedding_deployment,
        )
        embeddings.extend([e.embedding for e in response.data])
        logger.info(f"Embedded batch {i // batch_size + 1}")

    return np.array(embeddings, dtype=np.float32)


def build_index() -> None:
    """Build FAISS index from knowledge base documents."""
    logger.info("Building RAG index...")
    docs = load_documents()

    if not docs:
        logger.error("No documents found in knowledge base!")
        return

    texts = [d["text"] for d in docs]
    sources = [d["source"] for d in docs]

    logger.info(f"Embedding {len(texts)} chunks...")
    embeddings = embed_texts(texts)

    # Build FAISS flat L2 index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    # Persist index and metadata
    INDEX_PATH.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH / "index.faiss"))
    with open(INDEX_PATH / "metadata.pkl", "wb") as f:
        pickle.dump({"texts": texts, "sources": sources}, f)

    logger.info(f"✅ Index built with {index.ntotal} vectors → {INDEX_PATH}")


class RAGPipeline:
    """Wrapper to (re)build the FAISS index programmatically."""

    def build(self) -> None:
        build_index()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    build_index()
