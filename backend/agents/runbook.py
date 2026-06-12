"""
RunbookAgent — retrieves relevant runbook sections using RAG (pgvector
semantic search) and maps them to the current alert's failure pattern.
"""
import logging
from functools import lru_cache
from typing import Dict, Any

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.config import get_settings
from backend.rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are a senior SRE summarising runbook guidance for an on-call engineer.
Given runbook excerpts, return a structured plain-text summary with sections:
## Applicable Runbook Sections
## Diagnostic Steps
## Known Failure Modes
## Workarounds / Rollback Procedures"""


@lru_cache(maxsize=1)
def _get_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_chat_deployment,
        temperature=0,
        max_tokens=1000,  # plain-text runbook summary needs less than 1500
    )


class RunbookAgent:
    """Retrieves runbook context via RAG and summarises with Azure OpenAI."""

    def __init__(self, retriever: RAGRetriever):
        self.retriever = retriever
        self.llm = _get_llm()

    async def run(self, alert_payload: Dict[str, Any]) -> str:
        """Retrieve runbook context and return structured summary."""
        service = alert_payload.get("service", "unknown")
        alert_type = alert_payload.get("alert_type", "")
        error_code = alert_payload.get("error_code", "")

        logger.info(f"[RunbookAgent] Retrieving runbooks for service={service}, type={alert_type}")

        # ── Step 1: Build search query ────────────────────────
        query = f"{service} {alert_type} {error_code}".strip()

        # ── Step 2: Semantic search in pgvector ───────────────
        chunks = self.retriever.search(query, top_k=settings.top_k_retrieval)

        if not chunks:
            logger.warning(f"[RunbookAgent] No runbook chunks found for query: {query}")
            return "No relevant runbook sections found for this service and alert type."

        runbook_text = "\n\n---\n\n".join(
            [f"[Source: {c['source']}]\n{c['text']}" for c in chunks]
        )

        # ── Step 3: Summarise with LLM ────────────────────────
        user_message = f"""
Current Alert:
- Service: {service}
- Alert Type: {alert_type}
- Error Code: {error_code}
- Severity: {alert_payload.get('severity', 'N/A')}
- Affected Endpoints: {', '.join(alert_payload.get('affected_endpoints', []))}

Relevant Runbook Excerpts:
{runbook_text}

Please provide a structured runbook summary for the on-call engineer.
"""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]

        response = await self.llm.ainvoke(messages)
        logger.info(f"[RunbookAgent] Runbook summary complete for {service}")
        return response.content
