"""Pydantic models for triage report outputs."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RootCauseHypothesis(BaseModel):
    rank: int
    hypothesis: str
    confidence: ConfidenceLevel
    evidence: List[str] = Field(default_factory=list)
    remediation_steps: List[str] = Field(default_factory=list)


class RemediationStep(BaseModel):
    priority: int
    action: str
    owner: Optional[str] = None
    estimated_time: Optional[str] = None


class SimilarIncident(BaseModel):
    ticket_id: str
    title: str
    service: str
    root_cause: str
    resolution: str
    resolved_in_minutes: Optional[int] = None
    similarity_score: Optional[float] = None
    created_at: Optional[datetime] = None
    link: Optional[str] = None


class EscalationRecommendation(BaseModel):
    required: bool
    priority: str
    team: Optional[str] = None
    reason: Optional[str] = None


class AgentStatus(BaseModel):
    agent_name: str
    status: str  # "pending" | "running" | "completed" | "failed"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class TriageReport(BaseModel):
    incident_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    elapsed_seconds: Optional[float] = None
    alert_summary: str = ""
    root_cause_hypotheses: List[RootCauseHypothesis] = Field(default_factory=list)
    remediation_checklist: List[RemediationStep] = Field(default_factory=list)
    similar_past_incidents: List[SimilarIncident] = Field(default_factory=list)
    escalation_recommendation: Optional[EscalationRecommendation] = None
    log_findings: Optional[str] = None
    runbook_context: Optional[str] = None
    slack_message: Optional[str] = None
    agent_statuses: List[AgentStatus] = Field(default_factory=list)


class IncidentStatus(BaseModel):
    incident_id: str
    status: str  # "ingested|analyzing|correlating|reasoning|reporting|done|failed"
    progress_pct: int = 0
    current_step: Optional[str] = None
    report: Optional[TriageReport] = None
    error: Optional[str] = None
