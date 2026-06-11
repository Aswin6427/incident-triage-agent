"""
Unit tests for AI agents (mocked LLM and MCP calls).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agents.log_analyzer import LogAnalyzerAgent
from backend.agents.past_ticket import PastTicketAgent
from backend.agents.runbook import RunbookAgent
from backend.agents.root_cause import RootCauseAgent
from backend.mcp.gateway import MCPGateway
from backend.rag.retriever import RAGRetriever

# ── Fixtures ──────────────────────────────────────────────────
SAMPLE_ALERT = {
    "incident_id": "INC-TEST-001",
    "service": "payment-service",
    "alert_type": "DB_CONNECTION_TIMEOUT",
    "severity": "P1",
    "region": "us-east-1",
    "timestamp": "2025-05-27T14:32:00Z",
    "error_code": "CONN_TIMEOUT_5023",
    "affected_endpoints": ["/api/checkout", "/api/payment"],
    "metrics": {"error_rate": "23%", "latency_p99": "8200ms"},
}

MOCK_LOGS = [
    {"timestamp": "2025-05-27T14:02:11Z", "level": "ERROR", "message": "Connection timeout", "code": "CONN_TIMEOUT_5023"},
    {"timestamp": "2025-05-27T14:05:01Z", "level": "WARN", "message": "Active connections: 50/50", "code": "POOL_FULL"},
]

MOCK_INCIDENTS = [
    {
        "ticket_id": "JIRA-4521",
        "title": "Payment service DB timeout",
        "service": "payment-service",
        "root_cause": "Connection pool exhausted",
        "resolution": "Rolled back, increased pool size",
        "resolved_in_minutes": 23,
        "similarity_score": 0.95,
    }
]

MOCK_ROOT_CAUSE_RESPONSE = """{
  "hypotheses": [
    {
      "rank": 1,
      "hypothesis": "Database connection pool exhaustion due to connection leak",
      "confidence": "High",
      "evidence": ["847 CONN_TIMEOUT errors in 5min", "Pool at 50/50", "Deploy v2.3.1 at 13:58"],
      "remediation_steps": ["Restart pods", "Increase pool size", "Roll back deploy"]
    },
    {
      "rank": 2,
      "hypothesis": "Database server overloaded with slow queries",
      "confidence": "Medium",
      "evidence": ["High p99 latency (8200ms)"],
      "remediation_steps": ["Check pg_stat_activity", "Kill long queries"]
    }
  ],
  "remediation_checklist": [
    {"priority": 1, "action": "Restart payment-service pods", "owner": "On-call Engineer", "estimated_time": "2 min"},
    {"priority": 2, "action": "Increase HikariCP pool size to 50", "owner": "On-call Engineer", "estimated_time": "5 min"}
  ],
  "escalation": {"required": true, "priority": "P1", "team": "DB Team", "reason": "Potential DB-level issue"}
}"""


@pytest.mark.asyncio
async def test_log_analyzer_agent():
    """LogAnalyzerAgent should call MCP search_logs and return LLM analysis."""
    mock_gateway = AsyncMock(spec=MCPGateway)
    mock_gateway.call_tool.return_value = MOCK_LOGS

    with patch("backend.agents.log_analyzer.AzureChatOpenAI") as mock_llm_cls:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content='{"summary": "Connection pool exhausted"}')
        mock_llm_cls.return_value = mock_llm

        agent = LogAnalyzerAgent(mcp_gateway=mock_gateway)
        result = await agent.run(SAMPLE_ALERT)

    mock_gateway.call_tool.assert_called_once_with(
        "search_logs",
        {"service": "payment-service", "timestamp": "2025-05-27T14:32:00Z", "window_minutes": 30},
    )
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_past_ticket_agent_returns_dict():
    """PastTicketAgent.run() should return {"incidents": [...], "open_tickets": [...]}."""
    mock_gateway = AsyncMock(spec=MCPGateway)
    mock_gateway.call_tool.return_value = MOCK_INCIDENTS

    with patch("backend.agents.past_ticket.AzureChatOpenAI") as mock_llm_cls:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"ranked_incidents": [{"ticket_id": "JIRA-4521", "hypothesis": "test", "similarity_score": 0.95, "root_cause": "Pool exhausted", "resolution": "Rolled back", "resolved_in_minutes": 23, "relevance_reason": "Same service"}], "open_tickets": []}'
        )
        mock_llm_cls.return_value = mock_llm

        agent = PastTicketAgent(mcp_gateway=mock_gateway)
        result = await agent.run(SAMPLE_ALERT)

    assert isinstance(result, dict)
    assert "incidents" in result and "open_tickets" in result
    assert isinstance(result["incidents"], list)


@pytest.mark.asyncio
async def test_runbook_agent_no_index():
    """RunbookAgent should handle missing FAISS index gracefully."""
    mock_retriever = MagicMock(spec=RAGRetriever)
    mock_retriever.search.return_value = []  # No chunks found

    agent = RunbookAgent(retriever=mock_retriever)
    result = await agent.run(SAMPLE_ALERT)

    assert "No relevant runbook sections" in result


@pytest.mark.asyncio
async def test_root_cause_agent_parses_json():
    """RootCauseAgent should return a dict with hypotheses, checklist, and escalation."""
    with patch("backend.agents.root_cause.AzureChatOpenAI") as mock_llm_cls:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content=MOCK_ROOT_CAUSE_RESPONSE)
        mock_llm_cls.return_value = mock_llm

        agent = RootCauseAgent()
        result = await agent.run(
            alert_payload=SAMPLE_ALERT,
            log_findings='{"summary": "Pool exhausted"}',
            past_incidents=MOCK_INCIDENTS,
            runbook_context="Runbook: check pool size",
        )

    assert "hypotheses" in result
    assert len(result["hypotheses"]) >= 2
    assert result["hypotheses"][0]["rank"] == 1
    assert result["hypotheses"][0]["confidence"] in ["High", "Medium", "Low"]
    assert "remediation_checklist" in result
    assert "escalation" in result


@pytest.mark.asyncio
async def test_root_cause_agent_fallback_on_bad_json():
    """RootCauseAgent should return a fallback structure if LLM returns invalid JSON."""
    with patch("backend.agents.root_cause.AzureChatOpenAI") as mock_llm_cls:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="This is not JSON at all.")
        mock_llm_cls.return_value = mock_llm

        agent = RootCauseAgent()
        result = await agent.run(
            alert_payload=SAMPLE_ALERT,
            log_findings="",
            past_incidents=[],
            runbook_context="",
        )

    assert "hypotheses" in result
    assert len(result["hypotheses"]) >= 1  # Fallback hypothesis present
