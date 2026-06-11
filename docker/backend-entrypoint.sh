#!/bin/sh
# Selects which FastAPI app to run and binds to Cloud Run's $PORT.
set -e

APP_MODULE="${APP_MODULE:-main:app}"
PORT="${PORT:-8000}"

# Only the main backend needs the RAG index. Build it on first boot if it is
# missing (e.g. if the index was not committed into the image).
if [ "$APP_MODULE" = "main:app" ] && [ ! -f /app/backend/rag/faiss_index/index.faiss ]; then
  echo "[entrypoint] FAISS index not found — building RAG pipeline..."
  python -m rag.pipeline || echo "[entrypoint] RAG build failed; continuing (RAG features limited)"
fi

echo "[entrypoint] Starting uvicorn '$APP_MODULE' on 0.0.0.0:$PORT"
exec uvicorn "$APP_MODULE" --host 0.0.0.0 --port "$PORT"
