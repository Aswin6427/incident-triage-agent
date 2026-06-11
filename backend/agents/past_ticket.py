"""
PastTicketAgent — searches BOTH Jira and ServiceNow for similar past incidents,
detects currently open/in-progress tickets, and returns ranked results.
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

SYSTEM_PROMPT = """You are an incident management specialist.
Rank the combined Jira + ServiceNow incidents by relevance to the current alert.
Prioritise OPEN/IN-PROGRESS tickets highest.

Return ONLY valid JSON with two keys:
- "ranked_incidents": top 3-5 objects — {ticket_id, title, source, status, relevance_reason, root_cause, resolution, resolved_in_minutes, similarity_score}
- "open_tickets": all Open/In-Progress objects — {ticket_id, title, source, status, description, notes, assigned_team, link}"""

# Singleton LLM client
@lru_cache(maxsize=1)
def _get_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_deployment=settings.azure_openai_deployment_name,
        api_version=settings.azure_openai_api_version,
        api_key=settings.azure_openai_api_key,
        temperature=0,
        max_tokens=1500,  # ranked JSON output fits comfortably in 1500
    )

# Only send fields the LLM needs for ranking — drop large comment arrays, etc.
_TICKET_KEEP = {
    "ticket_id", "title", "service", "alert_type", "error_code",
    "status", "severity", "root_cause", "resolution",
    "resolved_in_minutes", "created_at", "source",
    "description", "notes", "assigned_team", "link",
}


def _slim_ticket(t: Dict) -> Dict:
    return {k: v for k, v in t.items() if k in _TICKET_KEEP and v is not None}


class PastTicketAgent:
    """Searches Jira + ServiceNow for past/open tickets and ranks them."""

    def __init__(self, mcp_gateway: MCPGateway):
        self.mcp = mcp_gateway
        self.llm = _get_llm()

    async def run(self, alert_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Search Jira + ServiceNow and return ranked incidents plus open tickets."""
        service = alert_payload.get("service", "unknown")
        alert_type = alert_payload.get("alert_type", "")
        error_code = alert_payload.get("error_code", "")

        logger.info("[PastTicketAgent] Searching Jira + ServiceNow for service=%s", service)

        # ── Step 1: Query Jira ────────────────────────────────
        try:
            jira_result = await self.mcp.call_tool(
                "search_past_incidents",
                {"service": service, "alert_type": alert_type, "error_code": error_code, "limit": 10},
            )
            jira_incidents = jira_result.get("incidents", jira_result) if isinstance(jira_result, dict) else jira_result
            for inc in jira_incidents:
                inc.setdefault("source", "jira")
        except Exception as exc:
            logger.warning("[PastTicketAgent] Jira search failed: %s", exc)
            jira_incidents = []

        # ── Step 2: Query ServiceNow ──────────────────────────
        try:
            snow_result = await self.mcp.call_tool(
                "search_servicenow_incidents",
                {"service": service, "alert_type": alert_type, "error_code": error_code, "limit": 10},
            )
            snow_incidents = snow_result.get("incidents", []) if isinstance(snow_result, dict) else []
            for inc in snow_incidents:
                inc.setdefault("source", "servicenow")
        except Exception as exc:
            logger.warning("[PastTicketAgent] ServiceNow search failed: %s", exc)
            snow_incidents = []

        all_incidents = jira_incidents + snow_incidents
        logger.info(
            "[PastTicketAgent] Found %d Jira + %d ServiceNow = %d total",
            len(jira_incidents), len(snow_incidents), len(all_incidents),
        )

        if not all_incidents:
            return {"incidents": [], "open_tickets": []}

        # ── Step 3: Quick pre-filter for open tickets ─────────
        open_statuses = {"open", "in progress", "new", "assigned"}
        pre_open = [
            i for i in all_incidents
            if str(i.get("status", "")).lower() in open_statuses
        ]
        logger.info("[PastTicketAgent] Pre-filtered %d open/in-progress tickets", len(pre_open))

        # ── Step 4: LLM ranking ───────────────────────────────
        slimmed = [_slim_ticket(t) for t in all_incidents]
        user_message = (
            f"Service: {service} | Alert: {alert_type} | Error: {error_code}\n\n"
            f"Incidents ({len(slimmed)} total):\n{json.dumps(slimmed)}"
        )
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_message)]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            if content.startswith("```"):
                parts = content.split("```")
                content = parts[1] if len(parts) > 1 else content
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)
            ranked = result.get("ranked_incidents", [])
            open_tickets = result.get("open_tickets", pre_open)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("[PastTicketAgent] LLM parse failed (%s), using raw data", exc)
            ranked = all_incidents[:5]
            open_tickets = pre_open

        logger.info(
            "[PastTicketAgent] Ranked %d incidents, %d open tickets for %s",
            len(ranked), len(open_tickets), service,
        )
        return {"incidents": ranked, "open_tickets": open_tickets}
