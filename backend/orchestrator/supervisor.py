"""
LangGraph supervisor / routing logic.

Determines which node to run next based on current state.
"""
from typing import Literal
from .state import IncidentState


def route_after_parallel(
    state: IncidentState,
) -> Literal["root_cause_node", "error_node"]:
    """Route to root cause analysis once all parallel agents complete."""
    statuses = [
        state.get("log_analyzer_status"),
        state.get("past_ticket_status"),
        state.get("runbook_status"),
    ]
    if any(s == "failed" for s in statuses):
        # Allow partial failures — still attempt root cause with what we have
        return "root_cause_node"
    return "root_cause_node"


def route_after_root_cause(
    state: IncidentState,
) -> Literal["report_node", "error_node"]:
    """Route to report generation after root cause analysis."""
    if state.get("root_cause_status") == "failed":
        return "error_node"
    return "report_node"


def route_after_report(
    state: IncidentState,
) -> Literal["__end__", "error_node"]:
    """Final routing — end the graph after report is posted."""
    if state.get("error"):
        return "error_node"
    return "__end__"
