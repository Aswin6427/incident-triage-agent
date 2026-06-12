"""
RootCauseAgent — synthesises log findings, past incidents, open tickets, and
runbook context into ranked root-cause hypotheses and a remediation checklist.
"""
import json
import logging
from functools import lru_cache
from typing import Dict, Any, List, Optional

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Tightened: removed tutorial prose, kept schema contract.
# GPT-4o infers the SRE role from context; explicit numbered lists waste tokens.
SYSTEM_PROMPT = """You are a principal SRE synthesising evidence to identify root cause.
Evidence sources: log analysis, past Jira/ServiceNow incidents, open tickets, runbook guidance.
Reference open ticket IDs in evidence and remediation where relevant.

Return ONLY valid JSON:
{
  "hypotheses": [{"rank":1,"hypothesis":"...","confidence":"High|Medium|Low","evidence":[...],"remediation_steps":[...]}],
  "remediation_checklist": [{"priority":1,"action":"...","owner":"...","estimated_time":"..."}],
  "escalation": {"required":true,"priority":"P1|P2|P3","team":"...","reason":"..."}
}"""


@lru_cache(maxsize=1)
def _get_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_chat_deployment,
        temperature=0,
        max_tokens=2000,  # 3 hypotheses + 10 checklist items fit in 2000
    )

_MAX_LOG_FINDINGS_CHARS = 2000   # cap upstream log analysis text before feeding forward
_MAX_RUNBOOK_CHARS      = 1500   # cap RAG runbook context


class RootCauseAgent:
    def __init__(self):
        self.llm = _get_llm()

    async def run(
        self,
        alert_payload: Dict[str, Any],
        log_findings: str,
        past_incidents: List[Dict[str, Any]],
        runbook_context: str,
        open_tickets: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        service = alert_payload.get("service", "unknown")
        logger.info("[RootCauseAgent] Synthesising evidence for %s", service)

        open_tickets = open_tickets or []

        # Trim large upstream outputs to stay within token budget
        log_text     = (log_findings     or "")[:_MAX_LOG_FINDINGS_CHARS]
        runbook_text = (runbook_context  or "")[:_MAX_RUNBOOK_CHARS]
        open_section = json.dumps(open_tickets) if open_tickets else "None"

        user_message = (
            f"=== ALERT ===\n"
            f"ID:{alert_payload.get('incident_id','N/A')} Service:{service} "
            f"Type:{alert_payload.get('alert_type','N/A')} Sev:{alert_payload.get('severity','N/A')} "
            f"Code:{alert_payload.get('error_code','N/A')} Region:{alert_payload.get('region','N/A')}\n"
            f"Endpoints:{', '.join(alert_payload.get('affected_endpoints',[]))}\n"
            f"Metrics:{json.dumps(alert_payload.get('metrics',{}))}\n\n"
            f"=== LOG FINDINGS ===\n{log_text or 'unavailable'}\n\n"
            f"=== PAST INCIDENTS ===\n{json.dumps(past_incidents or [])}\n\n"
            f"=== OPEN TICKETS ===\n{open_section}\n\n"
            f"=== RUNBOOK ===\n{runbook_text or 'unavailable'}"
        )
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_message)]
        response = await self.llm.ainvoke(messages)
        logger.info("[RootCauseAgent] Analysis complete for %s", service)

        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
        except (json.JSONDecodeError, IndexError) as exc:
            logger.error("[RootCauseAgent] JSON parse error: %s", exc)
            return {
                "hypotheses": [{"rank": 1, "hypothesis": "Unable to parse analysis", "confidence": "Low",
                                 "evidence": [response.content[:500]], "remediation_steps": ["Review logs manually"]}],
                "remediation_checklist": [
                    {"priority": 1, "action": "Check service health dashboard", "owner": "On-call Engineer", "estimated_time": "2 min"},
                    {"priority": 2, "action": "Review recent deployments", "owner": "On-call Engineer", "estimated_time": "5 min"},
                ],
                "escalation": {"required": True, "priority": "P2", "team": "Platform Team", "reason": "Analysis inconclusive"},
            }
