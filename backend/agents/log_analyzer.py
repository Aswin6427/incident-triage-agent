"""
LogAnalyzerAgent — queries mock Splunk/ELK for the 30-min pre-alert log window
and uses Azure OpenAI to identify anomalies.
"""
import json
import logging
from functools import lru_cache
from typing import Dict, Any, List

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.config import get_settings
from backend.mcp.gateway import MCPGateway

logger = logging.getLogger(__name__)
settings = get_settings()

# Kept concise — GPT-4o needs role + output schema only, not a tutorial
SYSTEM_PROMPT = """You are an expert SRE specialising in log analysis.
Analyse the provided log entries (pre-filtered to the most relevant) and return JSON with keys:
- error_rate_spikes: list of findings
- exceptions: list of top exception types with counts
- latency_anomalies: list of findings
- deployment_events: list of detected deploys/restarts
- dependency_issues: list of external dependency failures
- summary: 2-3 sentence plain English summary
Return ONLY valid JSON."""

# Singleton — one LLM client shared across all requests
@lru_cache(maxsize=1)
def _get_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_deployment=settings.azure_openai_deployment_name,
        api_version=settings.azure_openai_api_version,
        api_key=settings.azure_openai_api_key,
        temperature=0,
        max_tokens=1000,  # structured JSON output needs less than 1500
    )

# Priority order for log level filtering
_LEVEL_RANK = {"FATAL": 0, "ERROR": 1, "WARN": 2, "INFO": 3, "DEBUG": 4}
_MAX_LOGS = 30  # hard cap — beyond this, tokens spike with no quality gain


def _trim_logs(logs: List[Dict]) -> List[Dict]:
    """Keep the top MAX_LOGS entries prioritised by severity, then recency."""
    sorted_logs = sorted(
        logs,
        key=lambda e: (_LEVEL_RANK.get(e.get("level", "INFO"), 3),
                       -(hash(e.get("timestamp", "")) & 0xFFFF)),
    )
    trimmed = sorted_logs[:_MAX_LOGS]
    # Strip heavy/redundant fields the LLM doesn't need
    keep = {"timestamp", "level", "service", "message", "code", "thread"}
    return [{k: v for k, v in e.items() if k in keep} for e in trimmed]


class LogAnalyzerAgent:
    """Queries logs via MCP and analyses them with Azure OpenAI."""

    def __init__(self, mcp_gateway: MCPGateway):
        self.mcp = mcp_gateway
        self.llm = _get_llm()

    async def run(self, alert_payload: Dict[str, Any]) -> str:
        """Fetch logs, trim to budget, and return structured analysis string."""
        service    = alert_payload.get("service", "unknown")
        timestamp  = alert_payload.get("timestamp", "")
        alert_type = alert_payload.get("alert_type", "")

        logger.info("[LogAnalyzerAgent] Querying logs for service=%s", service)

        # ── Step 1: Fetch logs via MCP ────────────────────────
        log_data = await self.mcp.call_tool(
            "search_logs",
            {
                "service": service,
                "timestamp": str(timestamp),
                "window_minutes": settings.log_window_minutes,
            },
        )

        # ── Step 2: Trim payload to token budget ──────────────
        original_count = len(log_data)
        trimmed_logs   = _trim_logs(log_data)
        if original_count > _MAX_LOGS:
            logger.info(
                "[LogAnalyzerAgent] Trimmed logs %d → %d entries for %s",
                original_count, len(trimmed_logs), service,
            )

        # ── Step 3: Analyse with LLM ──────────────────────────
        user_message = (
            f"Service: {service} | Alert: {alert_type} | "
            f"Error code: {alert_payload.get('error_code', 'N/A')} | "
            f"Severity: {alert_payload.get('severity', 'N/A')}\n\n"
            f"Top {len(trimmed_logs)} log entries (FATAL/ERROR first):\n"
            f"{json.dumps(trimmed_logs)}"
        )

        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_message)]
        response = await self.llm.ainvoke(messages)
        logger.info("[LogAnalyzerAgent] Analysis complete for %s", service)
        return response.content
