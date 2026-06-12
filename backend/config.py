"""Application configuration loaded from environment variables."""
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# Always resolve .env relative to this file's location (backend/), so it works
# regardless of the working directory uvicorn / scripts are launched from.
_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    # ── Azure OpenAI ──────────────────────────────────────────
    # Auth uses an API key. `azure_openai_endpoint` is the resource
    # endpoint, e.g. https://<resource>.openai.azure.com/. The chat and
    # embedding "models" below are Azure *deployment* names, not raw
    # model ids.
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    # ── Backend ───────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # ── Mock Services ─────────────────────────────────────────
    mock_jira_url: str = "http://localhost:8001"
    mock_splunk_url: str = "http://localhost:8002"
    mock_servicenow_url: str = "http://localhost:8003"
    mock_slack_url: str = "http://localhost:8004"
    mock_oncall_url: str = "http://localhost:8005"

    # ── RAG / Vector store (Azure Database for PostgreSQL + pgvector) ──
    # SQLAlchemy-style URL using the psycopg (v3) driver, e.g.
    #   postgresql+psycopg://user:pwd@host:5432/dbname?sslmode=require
    # Azure Postgres requires SSL (sslmode=require).
    database_url: str = ""
    pg_collection_name: str = "incident_triage_kb"
    chunk_size: int = 400
    chunk_overlap: int = 50
    top_k_retrieval: int = 5

    # ── Agent Behaviour ───────────────────────────────────────
    max_triage_timeout_seconds: int = 600
    log_window_minutes: int = 30
    max_similar_incidents: int = 5
    predictive_monitor_interval_seconds: int = 300  # 5 minutes

    class Config:
        env_file = str(_ENV_FILE)
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
