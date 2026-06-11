"""
MCP Gateway -- single bridge between agents and all external systems.

Registered tools:
  search_logs                 -> Mock Splunk/ELK
  get_log_trends              -> Mock Splunk/ELK (trend/anomaly data)
  search_past_incidents       -> Mock Jira
  search_servicenow_incidents -> Mock ServiceNow (search)
  get_incident_details        -> Mock ServiceNow (fetch by ID)
  create_incident_ticket      -> Mock ServiceNow (create)
  post_slack_report           -> Mock Slack
  get_oncall_engineer         -> Mock On-Call (current on-call lookup)
  page_oncall_engineer        -> Mock On-Call (page the on-call engineer)
"""
import logging
from typing import Dict, Any

from backend.mcp.tools.splunk_tool import search_logs, get_log_trends
from backend.mcp.tools.jira_tool import search_past_incidents
from backend.mcp.tools.servicenow_tool import (
    search_servicenow_incidents,
    get_incident_details,
    create_incident_ticket,
)
from backend.mcp.tools.slack_tool import post_slack_report
from backend.mcp.tools.oncall_tool import get_oncall_engineer, page_oncall_engineer

logger = logging.getLogger(__name__)

TOOL_REGISTRY: Dict[str, Any] = {
    "search_logs":                search_logs,
    "get_log_trends":             get_log_trends,
    "search_past_incidents":      search_past_incidents,
    "search_servicenow_incidents": search_servicenow_incidents,
    "get_incident_details":       get_incident_details,
    "create_incident_ticket":     create_incident_ticket,
    "post_slack_report":          post_slack_report,
    "get_oncall_engineer":        get_oncall_engineer,
    "page_oncall_engineer":       page_oncall_engineer,
}

TOOL_SCHEMAS = [
    {
        "name": "search_logs",
        "description": "Query Splunk/ELK logs within a time window before the alert.",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "timestamp": {"type": "string"},
                "window_minutes": {"type": "integer", "default": 30},
            },
            "required": ["service", "timestamp"],
        },
    },
    {
        "name": "get_log_trends",
        "description": "Get error-rate trend and anomaly score for a service (used for predictive alerting).",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "window_minutes": {"type": "integer", "default": 30},
            },
            "required": ["service"],
        },
    },
    {
        "name": "search_past_incidents",
        "description": "Search Jira for historical incident tickets similar to the current alert.",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "alert_type": {"type": "string"},
                "error_code": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["service"],
        },
    },
    {
        "name": "search_servicenow_incidents",
        "description": "Search ServiceNow for past and currently open incident tickets.",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "alert_type": {"type": "string"},
                "error_code": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["service"],
        },
    },
    {
        "name": "get_incident_details",
        "description": "Get full details for a specific ServiceNow or Jira ticket by ID.",
        "parameters": {
            "type": "object",
            "properties": {"ticket_id": {"type": "string"}},
            "required": ["ticket_id"],
        },
    },
    {
        "name": "post_slack_report",
        "description": "Post the formatted triage report to the incident Slack channel.",
        "parameters": {
            "type": "object",
            "properties": {"report": {"type": "object"}},
            "required": ["report"],
        },
    },
    {
        "name": "create_incident_ticket",
        "description": "Create a new incident ticket in ServiceNow.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "severity": {"type": "string"},
                "service": {"type": "string"},
            },
            "required": ["title", "description", "severity", "service"],
        },
    },
    {
        "name": "get_oncall_engineer",
        "description": "Get the current on-call engineer for a given service.",
        "parameters": {
            "type": "object",
            "properties": {"service": {"type": "string"}},
            "required": ["service"],
        },
    },
    {
        "name": "page_oncall_engineer",
        "description": "Page the on-call engineer for a P1/P2 incident.",
        "parameters": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "incident_id": {"type": "string"},
                "severity": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["service", "incident_id", "severity", "message"],
        },
    },
]


class MCPGateway:
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        if tool_name not in TOOL_REGISTRY:
            raise ValueError(f"Unknown tool: '{tool_name}'. Available: {list(TOOL_REGISTRY)}")
        logger.info("[MCPGateway] -> %s(%s)", tool_name, list(params.keys()))
        try:
            result = await TOOL_REGISTRY[tool_name](**params)
            logger.info("[MCPGateway] <- %s returned successfully", tool_name)
            return result
        except Exception as exc:
            logger.error("[MCPGateway] Tool '%s' failed: %s", tool_name, exc)
            raise

    def get_tool_schemas(self):
        return TOOL_SCHEMAS
