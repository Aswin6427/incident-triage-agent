"""
Integration tests for the LangGraph orchestrator.
Tests the full graph flow with mocked agents.
"""
import pytest
import time
from unittest.mock import AsyncMock, patch

from backend.orchestrator.state import IncidentState


SAMPLE_ALERT = {
    "incident_id": "INC-ORCH-001",
    "service": "payment-service",
    "alert_type": "DB_CONNECTION_TIMEOUT",
    "severity": "P1",
    "region": "us-east-1",
    "timestamp": "2025-05-27T14:32:00Z",
    "error_code": "CONN_TIMEOUT_5023",
    "affected_endpoints": ["/api/checkout"],
    "metrics": {"error_rate": "23%"},
}

INITIAL_STATE: IncidentState = {
    "incident_id": "INC-ORCH-001",
    "alert_payload": SAMPLE_ALERT,
    "started_at": time.time(),
    "log_findings": None,
    "past_incidents": None,
    "runbook_context": None,
    "root_cause_hypotheses": None,
    "remediation_checklist": None,
    "escalation": None,
    "log_analyzer_status": "pending",
    "past_ticket_status": "pending",
    "runbook_status": "pending",
    "root_cause_status": "pending",
    "triage_report": None,
    "slack_posted": False,
    "current_step": "ingested",
    "error": None,
    "elapsed_seconds": None,
}


@pytest.mark.asyncio
async def test_graph_reaches_done_state():
    """Full graph should run from START to END and produce a triage report."""
    with (
        patch("backend.orchestrator.graph.LogAnalyzerAgent") as MockLog,
        patch("backend.orchestrator.graph.PastTicketAgent") as MockTicket,
        patch("backend.orchestrator.graph.RunbookAgent") as MockRunbook,
        patch("backend.orchestrator.graph.RootCauseAgent") as MockRoot,
        patch("backend.orchestrator.graph.MCPGateway"),
        patch("backend.orchestrator.graph.RAGRetriever"),
    ):
        # Set up mock agents
        MockLog.return_value.run = AsyncMock(return_value='{"summary": "Pool exhausted"}')
        MockTicket.return_value.run = AsyncMock(return_value={"incidents": [{"ticket_id": "JIRA-4521"}], "open_tickets": []})
        MockRunbook.return_value.run = AsyncMock(return_value="Runbook: Check pool size")
        MockRoot.return_value.run = AsyncMock(return_value={
            "hypotheses": [
                {
                    "rank": 1,
                    "hypothesis": "Connection pool exhausted",
                    "confidence": "High",
                    "evidence": ["847 timeouts"],
                    "remediation_steps": ["Restart pods", "Increase pool size"],
                }
            ],
            "remediation_checklist": [
                {"priority": 1, "action": "Restart pods", "owner": "Engineer", "estimated_time": "2 min"}
            ],
            "escalation": {"required": True, "priority": "P1", "team": "DB Team", "reason": "P1 incident"},
        })

        # Mock MCP gateway to avoid actual HTTP calls
        with patch("backend.mcp.gateway.MCPGateway.call_tool", new_callable=AsyncMock) as mock_tool:
            mock_tool.return_value = {"status": "posted"}

            from backend.orchestrator.graph import build_triage_graph
            graph = build_triage_graph()
            final_state = await graph.ainvoke(INITIAL_STATE)

    assert final_state["current_step"] == "done"
    assert final_state["triage_report"] is not None
    assert "incident_id" in final_state["triage_report"]


@pytest.mark.asyncio
async def test_graph_handles_agent_failure_gracefully():
    """Graph should continue even if one parallel agent fails."""
    with (
        patch("backend.orchestrator.graph.LogAnalyzerAgent") as MockLog,
        patch("backend.orchestrator.graph.PastTicketAgent") as MockTicket,
        patch("backend.orchestrator.graph.RunbookAgent") as MockRunbook,
        patch("backend.orchestrator.graph.RootCauseAgent") as MockRoot,
        patch("backend.orchestrator.graph.MCPGateway"),
        patch("backend.orchestrator.graph.RAGRetriever"),
    ):
        # LogAnalyzer fails
        MockLog.return_value.run = AsyncMock(side_effect=Exception("Splunk timeout"))
        MockTicket.return_value.run = AsyncMock(return_value={"incidents": [{"ticket_id": "JIRA-4521"}], "open_tickets": []})
        MockRunbook.return_value.run = AsyncMock(return_value="Runbook context")
        MockRoot.return_value.run = AsyncMock(return_value={
            "hypotheses": [{"rank": 1, "hypothesis": "Unknown", "confidence": "Low", "evidence": [], "remediation_steps": []}],
            "remediation_checklist": [],
            "escalation": {"required": False, "priority": "P2", "team": None, "reason": None},
        })

        with patch("backend.mcp.gateway.MCPGateway.call_tool", new_callable=AsyncMock) as mock_tool:
            mock_tool.return_value = {"status": "posted"}

            from backend.orchestrator.graph import build_triage_graph
            graph = build_triage_graph()
            final_state = await graph.ainvoke(INITIAL_STATE)

    # Should still complete with partial data
    assert final_state["log_analyzer_status"] == "failed"
    assert final_state["past_ticket_status"] == "completed"
    assert final_state["triage_report"] is not None
