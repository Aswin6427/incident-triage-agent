#!/bin/sh
# Selects which FastAPI app to run and binds to the platform's $PORT.
#
# The RAG knowledge base now lives in Azure Postgres (pgvector) and is built
# by a SEPARATE one-off job (the `triage-index-build` ACA Job, or
# `python -m backend.rag.pipeline` from inside Azure). The backend must NOT
# rebuild it on boot — the pipeline uses pre_delete_collection=True, so a
# boot-time rebuild would wipe and re-embed the collection on every restart.
set -e

APP_MODULE="${APP_MODULE:-main:app}"
PORT="${PORT:-8000}"

echo "[entrypoint] Starting uvicorn '$APP_MODULE' on 0.0.0.0:$PORT"
exec uvicorn "$APP_MODULE" --host 0.0.0.0 --port "$PORT"
