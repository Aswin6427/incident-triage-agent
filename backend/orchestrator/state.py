"""
LangGraph shared state schema for the incident triage workflow.
"""
from typing import TypedDict, Optional, List, Dict, Any


class IncidentState(TypedDict):
    # ── Input ──────────────────────────────────────────────────
    incident_id: str
    alert_payload: Dict[str, Any]
    started_at: float

    # ── Parallel agent findings ────────────────────────────────
    log_findings: Optional[str]
    past_incidents: Optional[List[Dict]]
    open_tickets: Optional[List[Dict]]        # open/in-progress tickets from Jira+SN
    runbook_context: Optional[str]

    # ── Root cause output ──────────────────────────────────────
    root_cause_hypotheses: Optional[List[Dict[str, Any]]]
    remediation_checklist: Optional[List[Dict[str, Any]]]
    escalation: Optional[Dict[str, Any]]

    # ── Agent status tracking ──────────────────────────────────
    log_analyzer_status: str
    past_ticket_status: str
    runbook_status: str
    root_cause_status: str

    # ── On-call routing ───────────────────────────────────────
    oncall_info: Optional[Dict[str, Any]]          # current on-call engineer
    paged: bool                                     # whether engineer was paged

    # ── Final output ───────────────────────────────────────────
    triage_report: Optional[Dict[str, Any]]
    slack_posted: bool

    # ── Control ───────────────────────────────────────────────
    current_step: str
    error: Optional[str]
    elapsed_seconds: Optional[float]
