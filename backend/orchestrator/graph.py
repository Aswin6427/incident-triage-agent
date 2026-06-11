"""
LangGraph state machine for incident triage.

Flow:
  START
    -> ingest_node
    -> [PARALLEL] log_analyzer_node | past_ticket_node | runbook_node
    -> root_cause_node
    -> report_node
    -> END
"""
import time
import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, START, END

from .state import IncidentState
from backend.agents.log_analyzer import LogAnalyzerAgent
from backend.agents.past_ticket import PastTicketAgent
from backend.agents.runbook import RunbookAgent
from backend.agents.root_cause import RootCauseAgent
from backend.mcp.gateway import MCPGateway
from backend.rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)


async def ingest_node(state: IncidentState) -> Dict[str, Any]:
    logger.info("[ingest] Processing alert %s", state["incident_id"])
    return {
        "current_step": "analyzing",
        "log_analyzer_status": "pending",
        "past_ticket_status": "pending",
        "runbook_status": "pending",
        "root_cause_status": "pending",
        "slack_posted": False,
        "paged": False,
        "oncall_info": None,
        "started_at": time.time(),
    }


async def log_analyzer_node(state: IncidentState) -> Dict[str, Any]:
    logger.info("[log_analyzer] Starting for %s", state["incident_id"])
    try:
        agent = LogAnalyzerAgent(mcp_gateway=MCPGateway())
        findings = await agent.run(state["alert_payload"])
        return {"log_findings": findings, "log_analyzer_status": "completed"}
    except Exception as exc:
        logger.error("[log_analyzer] Failed: %s", exc)
        return {"log_findings": f"Log analysis unavailable: {exc}", "log_analyzer_status": "failed"}


async def past_ticket_node(state: IncidentState) -> Dict[str, Any]:
    logger.info("[past_ticket] Starting for %s", state["incident_id"])
    try:
        agent = PastTicketAgent(mcp_gateway=MCPGateway())
        result = await agent.run(state["alert_payload"])
        incidents = result.get("incidents", [])
        open_tickets = result.get("open_tickets", [])
        logger.info(
            "[past_ticket] Found %d incidents, %d open tickets",
            len(incidents), len(open_tickets),
        )
        return {
            "past_incidents": incidents,
            "open_tickets": open_tickets,
            "past_ticket_status": "completed",
        }
    except Exception as exc:
        logger.error("[past_ticket] Failed: %s", exc)
        return {"past_incidents": [], "open_tickets": [], "past_ticket_status": "failed"}


async def runbook_node(state: IncidentState) -> Dict[str, Any]:
    logger.info("[runbook] Starting for %s", state["incident_id"])
    try:
        retriever = RAGRetriever()
        agent = RunbookAgent(retriever=retriever)
        context = await agent.run(state["alert_payload"])
        return {"runbook_context": context, "runbook_status": "completed"}
    except Exception as exc:
        logger.error("[runbook] Failed: %s", exc)
        return {"runbook_context": f"Runbook retrieval unavailable: {exc}", "runbook_status": "failed"}


async def root_cause_node(state: IncidentState) -> Dict[str, Any]:
    logger.info("[root_cause] Synthesising for %s", state["incident_id"])
    try:
        agent = RootCauseAgent()
        result = await agent.run(
            alert_payload=state["alert_payload"],
            log_findings=state.get("log_findings", ""),
            past_incidents=state.get("past_incidents", []),
            runbook_context=state.get("runbook_context", ""),
            open_tickets=state.get("open_tickets", []),
        )
        return {
            "root_cause_hypotheses": result.get("hypotheses", []),
            "remediation_checklist": result.get("remediation_checklist", []),
            "escalation": result.get("escalation"),
            "root_cause_status": "completed",
            "current_step": "reasoning",
        }
    except Exception as exc:
        logger.error("[root_cause] Failed: %s", exc)
        return {"root_cause_status": "failed", "error": str(exc)}


SERVICE_TEAMS = {
    "payment-service":       "platform",
    "auth-service":          "platform",
    "api-gateway":           "platform",
    "recommendation-engine": "ml_platform",
    "checkout-service":      "checkout",
    "notification-service":  "integrations",
}


async def report_node(state: IncidentState) -> Dict[str, Any]:
    logger.info("[report] Generating report for %s", state["incident_id"])
    elapsed = time.time() - state.get("started_at", time.time())
    alert   = state["alert_payload"]
    service = alert.get("service", "unknown-service")
    gateway = MCPGateway()

    # ── On-call lookup ────────────────────────────────────────
    oncall_info: Dict[str, Any] = {}
    paged = False
    try:
        oncall_info = await gateway.call_tool("get_oncall_engineer", {"service": service})
        logger.info("[report] On-call: %s", oncall_info.get("engineer", {}).get("name"))
    except Exception as exc:
        logger.warning("[report] On-call lookup failed: %s", exc)

    report = {
        "incident_id": state["incident_id"],
        "elapsed_seconds": round(elapsed, 1),
        "alert_summary": (
            f"[{alert.get('severity','?')}] {alert.get('alert_type','Unknown')} "
            f"on {service} in {alert.get('region','unknown-region')}"
        ),
        "root_cause_hypotheses":  state.get("root_cause_hypotheses", []),
        "remediation_checklist":  state.get("remediation_checklist", []),
        "similar_past_incidents": state.get("past_incidents", []),
        "open_tickets":           state.get("open_tickets", []),
        "escalation_recommendation": state.get("escalation"),
        "log_findings":    state.get("log_findings"),
        "runbook_context": state.get("runbook_context"),
        "oncall_engineer": oncall_info.get("engineer"),
        "oncall_shift":    oncall_info.get("shift"),
        "oncall_escalation": oncall_info.get("escalation_contact"),
    }

    # ── Auto-page on P1 escalation ────────────────────────────
    escalation = state.get("escalation") or {}
    if escalation.get("required") and alert.get("severity") == "P1" and oncall_info.get("engineer"):
        try:
            page_msg = (
                f"P1 INCIDENT {state['incident_id']} on {service}: "
                f"{alert.get('alert_type')}. "
                f"Top hypothesis: {(state.get('root_cause_hypotheses') or [{}])[0].get('hypothesis', 'N/A')}. "
                f"Escalation: {escalation.get('reason', '')}."
            )
            await gateway.call_tool("page_oncall_engineer", {
                "service":     service,
                "incident_id": state["incident_id"],
                "severity":    alert.get("severity", "P1"),
                "message":     page_msg,
            })
            paged = True
            logger.info("[report] Paged on-call engineer for P1 incident %s", state["incident_id"])
        except Exception as exc:
            logger.warning("[report] Paging failed: %s", exc)

    # ── Post to Slack ─────────────────────────────────────────
    slack_posted = False
    try:
        await gateway.call_tool("post_slack_report", {"report": report})
        slack_posted = True
    except Exception as exc:
        logger.warning("[report] Slack post failed: %s", exc)

    return {
        "triage_report": report,
        "oncall_info":   oncall_info,
        "paged":         paged,
        "slack_posted":  slack_posted,
        "current_step":  "done",
        "elapsed_seconds": elapsed,
    }


async def error_node(state: IncidentState) -> Dict[str, Any]:
    logger.error("[error] Incident %s failed: %s", state["incident_id"], state.get("error"))
    return {"current_step": "failed"}


def build_triage_graph() -> StateGraph:
    graph = StateGraph(IncidentState)

    graph.add_node("ingest_node", ingest_node)
    graph.add_node("log_analyzer_node", log_analyzer_node)
    graph.add_node("past_ticket_node", past_ticket_node)
    graph.add_node("runbook_node", runbook_node)
    graph.add_node("root_cause_node", root_cause_node)
    graph.add_node("report_node", report_node)
    graph.add_node("error_node", error_node)

    graph.add_edge(START, "ingest_node")

    # Fan-out: 3 agents in parallel
    graph.add_edge("ingest_node", "log_analyzer_node")
    graph.add_edge("ingest_node", "past_ticket_node")
    graph.add_edge("ingest_node", "runbook_node")

    # Fan-in: all -> root cause
    graph.add_edge("log_analyzer_node", "root_cause_node")
    graph.add_edge("past_ticket_node", "root_cause_node")
    graph.add_edge("runbook_node", "root_cause_node")

    graph.add_edge("root_cause_node", "report_node")
    graph.add_edge("report_node", END)
    graph.add_edge("error_node", END)

    return graph.compile()
