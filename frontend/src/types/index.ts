// ── Alert Types ───────────────────────────────────────────────

export interface AlertMetrics {
  error_rate?: string
  latency_p99?: string
  throughput_drop?: string
  cpu_usage?: string
  memory_usage?: string
}

export interface Alert {
  incident_id: string
  service: string
  alert_type: string
  severity: 'P1' | 'P2' | 'P3' | 'P4'
  region: string
  timestamp: string
  error_code?: string
  affected_endpoints?: string[]
  metrics?: AlertMetrics
  description?: string
  source?: string
}

// ── Triage Report Types ───────────────────────────────────────

export type ConfidenceLevel = 'High' | 'Medium' | 'Low'

export interface RootCauseHypothesis {
  rank: number
  hypothesis: string
  confidence: ConfidenceLevel
  evidence: string[]
  remediation_steps: string[]
}

export interface RemediationStep {
  priority: number
  action: string
  owner?: string
  estimated_time?: string
}

export interface SimilarIncident {
  ticket_id: string
  title: string
  service?: string
  root_cause?: string
  resolution?: string
  resolved_in_minutes?: number
  similarity_score?: number
  created_at?: string
  link?: string
  source?: 'jira' | 'servicenow'
  status?: string
}

export interface OpenTicket {
  ticket_id: string
  title: string
  source: 'jira' | 'servicenow'
  status: 'Open' | 'In Progress' | 'New' | string
  description?: string
  notes?: string
  assigned_team?: string
  link?: string
  created_at?: string
  severity?: string
}

export interface EscalationRecommendation {
  required: boolean
  priority: string
  team?: string
  reason?: string
}

// ── On-Call Types ─────────────────────────────────────────────

export interface OnCallEngineer {
  name: string
  email: string
  phone: string
  slack: string
  team: string
}

export interface OnCallEscalation {
  name: string
  title: string
  phone: string
  email: string
}

// ── Post-Mortem Types ─────────────────────────────────────────

export interface PostMortemActionItem {
  priority: number
  action: string
  owner: string
  due_days: number
}

export interface PostMortemTimelineEvent {
  time: string
  event: string
}

export interface PostMortem {
  incident_id: string
  title: string
  severity?: string
  service?: string
  duration_minutes?: number
  generated_at: string
  resolved_by?: string
  timeline: PostMortemTimelineEvent[]
  confirmed_root_cause: string
  contributing_factors: string[]
  impact: string
  resolution_summary: string
  action_items: PostMortemActionItem[]
  lessons_learned: string
  prevention_steps: string[]
}

// ── Triage Report ─────────────────────────────────────────────

export interface TriageReport {
  incident_id: string
  generated_at?: string
  elapsed_seconds?: number
  alert_summary: string
  root_cause_hypotheses: RootCauseHypothesis[]
  remediation_checklist: RemediationStep[]
  similar_past_incidents: SimilarIncident[]
  open_tickets?: OpenTicket[]
  escalation_recommendation?: EscalationRecommendation
  log_findings?: string
  runbook_context?: string
  oncall_engineer?: OnCallEngineer
  oncall_shift?: string
  oncall_escalation?: OnCallEscalation
}

// ── Predictive Alert ──────────────────────────────────────────

export interface Prediction {
  prediction_id: string
  service: string
  alert_type: string
  predicted: true
  confidence: 'High' | 'Medium' | 'Low'
  severity: 'P2' | 'P3'
  eta_minutes: number
  anomaly_score: number
  current_error_rate_pct: number
  baseline_error_rate_pct: number
  trend: string
  top_error_codes: string[]
  description: string
  detected_at: number
  data_points?: number[]
}

// ── Agent Flow Types ──────────────────────────────────────────

export type AgentNodeStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface AgentStepInfo {
  status: AgentNodeStatus
  label: string
  open_tickets_count?: number
}

export type AgentSteps = Record<string, AgentStepInfo>

// ── Incident State ────────────────────────────────────────────

export type IncidentStatus =
  | 'ingested' | 'analyzing' | 'correlating' | 'reasoning'
  | 'reporting' | 'done' | 'failed' | 'resolving'
  | 'generating_post_mortem' | 'resolved'

export interface Incident {
  incident_id: string
  status: IncidentStatus
  progress_pct: number
  current_step?: string
  alert?: Alert
  report?: TriageReport
  post_mortem?: PostMortem
  paged?: boolean
  oncall_info?: any
  error?: string
  received_at?: number
  agent_steps?: AgentSteps
}

// ── WebSocket Events ──────────────────────────────────────────

export interface WsEvent {
  event: 'connected' | 'new_alert' | 'incident_update' | 'prediction' | 'post_mortem_complete'
  incident_id?: string
  alert?: Alert
  status?: IncidentStatus
  progress_pct?: number
  current_step?: string
  report?: TriageReport
  post_mortem?: PostMortem
  error?: string
  active_incidents?: string[]
  agent_steps?: AgentSteps
  agent_step_update?: AgentSteps
  // prediction fields
  prediction_id?: string
  service?: string
  alert_type?: string
  predicted?: boolean
  confidence?: string
  severity?: string
  eta_minutes?: number
  anomaly_score?: number
  description?: string
  detected_at?: number
}
