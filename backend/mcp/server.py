"""
Real MCP Server — exposes all 9 project tools over the MCP protocol.

Run with:
    python -m backend.mcp.server            (stdio mode — for MCP Inspector)
    python -m backend.mcp.server --sse      (HTTP/SSE mode — port 8006)

MCP Inspector usage:
    npx @modelcontextprotocol/inspector python -m backend.mcp.server
"""
import asyncio
import sys
import os
import logging

# Ensure project root is on path when run as a module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from backend.mcp.tools.splunk_tool      import search_logs, get_log_trends
from backend.mcp.tools.jira_tool        import search_past_incidents
from backend.mcp.tools.servicenow_tool  import (
    search_servicenow_incidents,
    get_incident_details,
    create_incident_ticket,
)
from backend.mcp.tools.slack_tool       import post_slack_report
from backend.mcp.tools.oncall_tool      import get_oncall_engineer, page_oncall_engineer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Build the MCP server ──────────────────────────────────────
app = Server("incident-triage-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_logs",
            description="Query Splunk/ELK logs within a time window before the alert.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service":        {"type": "string", "description": "Service name to query"},
                    "timestamp":      {"type": "string", "description": "Alert timestamp (ISO 8601)"},
                    "window_minutes": {"type": "integer", "default": 30, "description": "Look-back window in minutes"},
                },
                "required": ["service", "timestamp"],
            },
        ),
        Tool(
            name="get_log_trends",
            description="Get error-rate trend and anomaly score for a service (predictive alerting).",
            inputSchema={
                "type": "object",
                "properties": {
                    "service":        {"type": "string", "description": "Service name"},
                    "window_minutes": {"type": "integer", "default": 30},
                },
                "required": ["service"],
            },
        ),
        Tool(
            name="search_past_incidents",
            description="Search Jira for historical incident tickets similar to the current alert.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service":    {"type": "string"},
                    "alert_type": {"type": "string"},
                    "error_code": {"type": "string"},
                    "limit":      {"type": "integer", "default": 10},
                },
                "required": ["service"],
            },
        ),
        Tool(
            name="search_servicenow_incidents",
            description="Search ServiceNow for past and currently open incident tickets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service":    {"type": "string"},
                    "alert_type": {"type": "string"},
                    "error_code": {"type": "string"},
                    "limit":      {"type": "integer", "default": 10},
                },
                "required": ["service"],
            },
        ),
        Tool(
            name="get_incident_details",
            description="Get full details for a specific ServiceNow or Jira ticket by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "Ticket ID, e.g. JIRA-4788 or SN-PAY003"},
                },
                "required": ["ticket_id"],
            },
        ),
        Tool(
            name="create_incident_ticket",
            description="Create a new incident ticket in ServiceNow.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title":       {"type": "string"},
                    "description": {"type": "string"},
                    "severity":    {"type": "string", "enum": ["P1", "P2", "P3"]},
                    "service":     {"type": "string"},
                },
                "required": ["title", "description", "severity", "service"],
            },
        ),
        Tool(
            name="post_slack_report",
            description="Post the formatted triage report to the incident Slack channel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "report": {"type": "object", "description": "Full triage report dict"},
                },
                "required": ["report"],
            },
        ),
        Tool(
            name="get_oncall_engineer",
            description="Get the current on-call engineer for a given service.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {"type": "string", "description": "Service name to resolve team"},
                },
                "required": ["service"],
            },
        ),
        Tool(
            name="page_oncall_engineer",
            description="Page the on-call engineer for a P1/P2 incident.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service":     {"type": "string"},
                    "incident_id": {"type": "string"},
                    "severity":    {"type": "string", "enum": ["P1", "P2", "P3"]},
                    "message":     {"type": "string"},
                },
                "required": ["service", "incident_id", "severity", "message"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls to the underlying implementation functions."""
    import json

    try:
        if name == "search_logs":
            result = await search_logs(**arguments)
        elif name == "get_log_trends":
            result = await get_log_trends(**arguments)
        elif name == "search_past_incidents":
            result = await search_past_incidents(**arguments)
        elif name == "search_servicenow_incidents":
            result = await search_servicenow_incidents(**arguments)
        elif name == "get_incident_details":
            result = await get_incident_details(**arguments)
        elif name == "create_incident_ticket":
            result = await create_incident_ticket(**arguments)
        elif name == "post_slack_report":
            result = await post_slack_report(**arguments)
        elif name == "get_oncall_engineer":
            result = await get_oncall_engineer(**arguments)
        elif name == "page_oncall_engineer":
            result = await page_oncall_engineer(**arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    except Exception as exc:
        logger.error("[MCPServer] Tool %s failed: %s", name, exc)
        return [TextContent(type="text", text=f"ERROR: {exc}")]


# ── Entry point ───────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        logger.info("[MCPServer] Starting in stdio mode — 9 tools registered")
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
