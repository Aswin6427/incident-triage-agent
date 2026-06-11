"""Application configuration loaded from environment variables."""
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# Always resolve .env relative to this file's location (backend/), so it works
# regardless of the working directory uvicorn / scripts are launched from.
_ENV_FILE = Path(__file__).parent.parent / ".env"
_DEFAULT_INDEX_PATH = str(Path(__file__).parent / "rag" / "faiss_index")


class Settings(BaseSettings):
    # ── Azure OpenAI ──────────────────────────────────────────
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment_name: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    azure_openai_api_version: str = "2024-02-15-preview"

    # ── Backend ───────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # ── Mock Services ─────────────────────────────────────────
    mock_jira_url: str = "http://localhost:8001"
    mock_splunk_url: str = "http://localhost:8002"
    mock_servicenow_url: str = "http://localhost:8003"
    mock_slack_url: str = "http://localhost:8004"
    mock_oncall_url: str = "http://localhost:8005"

    # ── RAG ───────────────────────────────────────────────────
    faiss_index_path: str = _DEFAULT_INDEX_PATH
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
