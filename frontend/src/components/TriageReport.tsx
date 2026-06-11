import React, { useState } from 'react'
import {
  Incident, Prediction, RootCauseHypothesis, RemediationStep,
  SimilarIncident, OpenTicket, PostMortem,
} from '../types'

interface Props {
  incident?: Incident
  prediction?: Prediction
  onResolve?: (incidentId: string, resolution: string, rootCause: string, resolvedBy: string) => void
}

// ── Confidence colours ────────────────────────────────────────
const confidenceColors = {
  High:   'bg-red-500/20 text-red-300 border-red-500/40',
  Medium: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40',
  Low:    'bg-slate-600/50 text-slate-300 border-slate-500/40',
}
const confidenceEmoji = { High: '🔴', Medium: '🟡', Low: '🟢' }

// ── Sub-components ────────────────────────────────────────────

const HypothesisCard: React.FC<{ h: RootCauseHypothesis }> = ({ h }) => {
  const [expanded, setExpanded] = useState(h.rank === 1)
  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-3 flex items-center gap-3 hover:bg-slate-700/50 transition-colors"
      >
        <span className="text-lg">{confidenceEmoji[h.confidence] ?? '⚪'}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-400">#{h.rank}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded border ${confidenceColors[h.confidence] ?? ''}`}>
              {h.confidence}
            </span>
          </div>
          <p className="text-sm font-medium text-slate-200 mt-0.5">{h.hypothesis}</p>
        </div>
        <span className="text-slate-500 text-sm">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <div className="px-4 pb-4 bg-slate-800/50 space-y-3">
          {h.evidence?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 mb-1">Evidence</p>
              <ul className="space-y-1">
                {h.evidence.map((ev, i) => (
                  <li key={i} className="text-xs text-slate-300 flex gap-2">
                    <span className="text-slate-500 flex-shrink-0">›</span><span>{ev}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {h.remediation_steps?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 mb-1">Remediation Steps</p>
              <ol className="space-y-1">
                {h.remediation_steps.map((step, i) => (
                  <li key={i} className="text-xs text-slate-300 flex gap-2">
                    <span className="text-slate-500 flex-shrink-0">{i + 1}.</span><span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const OpenTicketCard: React.FC<{ ticket: OpenTicket }> = ({ ticket }) => {
  const srcColor = ticket.source === 'jira'
    ? 'bg-blue-500/20 text-blue-300 border-blue-500/40'
    : 'bg-purple-500/20 text-purple-300 border-purple-500/40'
  const stColor = ticket.status === 'Open'
    ? 'bg-red-500/20 text-red-300 border-red-500/40'
    : 'bg-orange-500/20 text-orange-300 border-orange-500/40'
  return (
    <div className="p-3 bg-red-900/10 rounded-lg border border-red-500/30">
      <div className="flex items-center gap-2 mb-1 flex-wrap">
        <span className={`text-xs px-1.5 py-0.5 rounded border font-mono ${srcColor}`}>
          {ticket.source?.toUpperCase()}
        </span>
        <span className="text-xs font-mono text-red-300">{ticket.ticket_id}</span>
        <span className={`text-xs px-1.5 py-0.5 rounded border ${stColor}`}>{ticket.status}</span>
        {ticket.severity && <span className="text-xs text-slate-500">{ticket.severity}</span>}
      </div>
      <p className="text-xs font-medium text-slate-200">{ticket.title}</p>
      {ticket.description && <p className="text-xs text-slate-400 mt-1">{ticket.description}</p>}
      {ticket.notes && <p className="text-xs text-orange-300/80 mt-1 italic">Note: {ticket.notes}</p>}
      <div className="flex gap-3 mt-1.5 flex-wrap">
        {ticket.assigned_team && <span className="text-xs text-slate-500">👤 {ticket.assigned_team}</span>}
        {ticket.link && (
          <a href={ticket.link} target="_blank" rel="noopener noreferrer"
            className="text-xs text-blue-400 hover:text-blue-300 underline">
            View ticket
          </a>
        )}
      </div>
    </div>
  )
}

const PostMortemView: React.FC<{ pm: PostMortem }> = ({ pm }) => (
  <div className="space-y-4 p-4 bg-slate-800/50 rounded-lg border border-green-500/30">
    <div className="flex items-center gap-2">
      <span className="text-green-400 font-bold text-sm">Post-Mortem Report</span>
      {pm.duration_minutes && (
        <span className="text-xs text-slate-500">Duration: {pm.duration_minutes}min</span>
      )}
    </div>

    <div>
      <p className="text-xs font-semibold text-slate-400 mb-1">Confirmed Root Cause</p>
      <p className="text-xs text-slate-200 bg-slate-900/50 p-2 rounded">{pm.confirmed_root_cause}</p>
    </div>

    {pm.impact && (
      <div>
        <p className="text-xs font-semibold text-slate-400 mb-1">Impact</p>
        <p className="text-xs text-slate-300">{pm.impact}</p>
      </div>
    )}

    {pm.timeline?.length > 0 && (
      <div>
        <p className="text-xs font-semibold text-slate-400 mb-1">Timeline</p>
        <div className="space-y-1">
          {pm.timeline.map((e, i) => (
            <div key={i} className="flex gap-2 text-xs">
              <span className="text-slate-500 flex-shrink-0 font-mono">{e.time}</span>
              <span className="text-slate-300">{e.event}</span>
            </div>
          ))}
        </div>
      </div>
    )}

    {pm.action_items?.length > 0 && (
      <div>
        <p className="text-xs font-semibold text-slate-400 mb-1">Action Items</p>
        <div className="space-y-1">
          {pm.action_items.map((item, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className="text-slate-500 flex-shrink-0 w-4">{item.priority}.</span>
              <div>
                <span className="text-slate-200">{item.action}</span>
                <span className="text-slate-500 ml-2">({item.owner} · {item.due_days}d)</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    )}

    {pm.lessons_learned && (
      <div>
        <p className="text-xs font-semibold text-slate-400 mb-1">Lessons Learned</p>
        <p className="text-xs text-slate-300 italic">{pm.lessons_learned}</p>
      </div>
    )}
  </div>
)

// ── Resolve form ──────────────────────────────────────────────

const ResolveForm: React.FC<{ incidentId: string; onSubmit: (r: string, rc: string, by: string) => void; onCancel: () => void }> = ({
  incidentId, onSubmit, onCancel,
}) => {
  const [resolution, setResolution] = useState('')
  const [rootCause, setRootCause]   = useState('')
  const [resolvedBy, setResolvedBy] = useState('On-Call Engineer')

  return (
    <div className="bg-slate-800 rounded-lg border border-green-500/30 p-4 space-y-3">
      <p className="text-sm font-semibold text-green-300">Mark {incidentId} as Resolved</p>
      <div>
        <label className="text-xs text-slate-400 block mb-1">Confirmed Root Cause</label>
        <textarea
          value={rootCause} onChange={e => setRootCause(e.target.value)}
          className="w-full text-xs bg-slate-900 border border-slate-600 rounded p-2 text-slate-200 resize-none h-16 focus:outline-none focus:border-green-500/60"
          placeholder="What actually caused the incident?"
        />
      </div>
      <div>
        <label className="text-xs text-slate-400 block mb-1">Resolution Summary</label>
        <textarea
          value={resolution} onChange={e => setResolution(e.target.value)}
          className="w-full text-xs bg-slate-900 border border-slate-600 rounded p-2 text-slate-200 resize-none h-16 focus:outline-none focus:border-green-500/60"
          placeholder="What steps were taken to resolve it?"
        />
      </div>
      <div>
        <label className="text-xs text-slate-400 block mb-1">Resolved By</label>
        <input
          value={resolvedBy} onChange={e => setResolvedBy(e.target.value)}
          className="w-full text-xs bg-slate-900 border border-slate-600 rounded p-2 text-slate-200 focus:outline-none focus:border-green-500/60"
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => onSubmit(resolution, rootCause, resolvedBy)}
          disabled={!resolution.trim() || !rootCause.trim()}
          className="flex-1 text-xs py-1.5 rounded bg-green-600 hover:bg-green-500 text-white font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Generate Post-Mortem
        </button>
        <button
          onClick={onCancel}
          className="text-xs px-3 py-1.5 rounded border border-slate-600 text-slate-400 hover:text-slate-200 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

// ── Prediction detail view ────────────────────────────────────

const PredictionDetail: React.FC<{ prediction: Prediction }> = ({ prediction }) => (
  <div className="flex-1 h-screen overflow-y-auto p-6 space-y-6">
    <div className="flex items-start justify-between">
      <div>
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <span className="text-orange-400">⚠️</span> Predicted Incident
        </h2>
        <p className="text-slate-400 text-sm mt-0.5">
          {prediction.service} · {prediction.alert_type}
        </p>
      </div>
      <div className="text-right">
        <span className="text-sm font-bold px-2 py-1 rounded bg-orange-500/20 text-orange-400">
          {prediction.severity}
        </span>
        <p className="text-xs text-orange-300 mt-1">ETA ~{prediction.eta_minutes}min</p>
      </div>
    </div>

    <div className="bg-orange-900/20 border border-orange-500/30 rounded-lg p-4">
      <p className="text-xs font-semibold text-orange-300 mb-1">Predictive Alert</p>
      <p className="text-sm text-slate-200">{prediction.description}</p>
    </div>

    <div className="grid grid-cols-2 gap-3">
      <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
        <p className="text-xs text-slate-400">Current Error Rate</p>
        <p className="text-lg font-bold text-orange-300">{prediction.current_error_rate_pct?.toFixed(1)}%</p>
        <p className="text-xs text-slate-500">baseline: {prediction.baseline_error_rate_pct?.toFixed(1)}%</p>
      </div>
      <div className="bg-slate-800 rounded-lg p-3 border border-slate-700">
        <p className="text-xs text-slate-400">Anomaly Score</p>
        <p className="text-lg font-bold text-orange-300">{Math.round(prediction.anomaly_score * 100)}%</p>
        <p className="text-xs text-slate-500">trend: {prediction.trend}</p>
      </div>
    </div>

    {prediction.top_error_codes?.length > 0 && (
      <div>
        <p className="text-sm font-semibold text-slate-300 mb-2">Top Error Codes</p>
        <div className="flex gap-2 flex-wrap">
          {prediction.top_error_codes.map(code => (
            <span key={code} className="text-xs font-mono bg-slate-800 border border-slate-700 px-2 py-1 rounded text-slate-300">
              {code}
            </span>
          ))}
        </div>
      </div>
    )}

    {prediction.data_points && prediction.data_points.length > 0 && (
      <div>
        <p className="text-sm font-semibold text-slate-300 mb-2">Error Rate Trend (last 10 samples)</p>
        <div className="flex items-end gap-1 h-16 bg-slate-800 rounded-lg p-3 border border-slate-700">
          {prediction.data_points.map((val, i) => {
            const max = Math.max(...prediction.data_points!)
            const pct = max > 0 ? (val / max) * 100 : 0
            return (
              <div key={i} className="flex-1 bg-orange-400/60 rounded-sm" style={{ height: `${pct}%` }} title={`${val.toFixed(1)}%`} />
            )
          })}
        </div>
      </div>
    )}

    <div className="bg-slate-800 rounded-lg p-4 border border-orange-500/20">
      <p className="text-xs font-semibold text-orange-300 mb-2">Recommended Actions</p>
      <ul className="space-y-1">
        <li className="text-xs text-slate-300 flex gap-2"><span className="text-orange-400">1.</span> Check {prediction.service} dashboard immediately</li>
        <li className="text-xs text-slate-300 flex gap-2"><span className="text-orange-400">2.</span> Review recent deployments for {prediction.service}</li>
        <li className="text-xs text-slate-300 flex gap-2"><span className="text-orange-400">3.</span> Monitor error codes: {prediction.top_error_codes?.join(', ')}</li>
        <li className="text-xs text-slate-300 flex gap-2"><span className="text-orange-400">4.</span> Consider pre-emptive scaling or circuit breaker</li>
      </ul>
    </div>
  </div>
)

// ── Main TriageReport ─────────────────────────────────────────

export const TriageReport: React.FC<Props> = ({ incident, prediction, onResolve }) => {
  const [showResolveForm, setShowResolveForm] = useState(false)

  if (prediction && !incident) {
    return <PredictionDetail prediction={prediction} />
  }

  if (!incident) return null

  const report       = incident.report
  const alert        = incident.alert
  const openTickets  = report?.open_tickets ?? []
  const oncall       = report?.oncall_engineer
  const isDone       = incident.status === 'done'
  const isResolved   = incident.status === 'resolved'
  const isResolving  = incident.status === 'resolving' || incident.status === 'generating_post_mortem'
  const postMortem   = incident.post_mortem

  const handleResolve = (resolution: string, rootCause: string, resolvedBy: string) => {
    setShowResolveForm(false)
    onResolve?.(incident.incident_id, resolution, rootCause, resolvedBy)
  }

  return (
    <div className="flex-1 h-screen overflow-y-auto p-6 space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            {incident.incident_id}
            {isResolved && <span className="text-xs text-green-400 font-normal">resolved</span>}
          </h2>
          <p className="text-slate-400 text-sm mt-0.5">
            {alert?.service} · {alert?.alert_type} · {alert?.region}
          </p>
        </div>
        <div className="text-right">
          <span className={`text-sm font-bold px-2 py-1 rounded ${
            alert?.severity === 'P1' ? 'bg-red-500/20 text-red-400' : 'bg-orange-500/20 text-orange-400'
          }`}>
            {alert?.severity}
          </span>
          {report?.elapsed_seconds && (
            <p className="text-xs text-green-400 mt-1">⚡ {report.elapsed_seconds}s</p>
          )}
        </div>
      </div>

      {/* Alert summary */}
      {report?.alert_summary && (
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <p className="text-xs font-semibold text-slate-400 mb-1">Alert Summary</p>
          <p className="text-sm text-slate-200">{report.alert_summary}</p>
        </div>
      )}

      {/* On-call engineer */}
      {oncall && (
        <div className={`rounded-lg p-3 border ${incident.paged ? 'bg-red-900/10 border-red-500/30' : 'bg-slate-800 border-slate-700'}`}>
          <p className="text-xs font-semibold text-slate-400 mb-1 flex items-center gap-2">
            📟 On-Call Engineer
            {incident.paged && (
              <span className="text-xs text-red-300 bg-red-500/20 border border-red-500/30 px-1.5 py-0.5 rounded">PAGED</span>
            )}
            {report?.oncall_shift && (
              <span className="text-xs text-slate-500 capitalize">{report.oncall_shift} shift</span>
            )}
          </p>
          <div className="flex items-center gap-4 flex-wrap">
            <span className="text-sm font-medium text-slate-200">{oncall.name}</span>
            <span className="text-xs text-blue-400">{oncall.slack}</span>
            <span className="text-xs text-slate-500">{oncall.phone}</span>
          </div>
          {report?.oncall_escalation && (
            <p className="text-xs text-slate-500 mt-1">
              Escalation: {report.oncall_escalation.name} ({report.oncall_escalation.title}) · {report.oncall_escalation.phone}
            </p>
          )}
        </div>
      )}

      {/* Open tickets */}
      {openTickets.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-red-300 mb-3 flex items-center gap-2">
            🔥 Active Open Tickets
            <span className="text-xs bg-red-500/20 text-red-300 px-1.5 py-0.5 rounded border border-red-500/40">
              {openTickets.length} related
            </span>
          </h3>
          <div className="space-y-2">
            {openTickets.map(t => <OpenTicketCard key={t.ticket_id} ticket={t as OpenTicket} />)}
          </div>
        </div>
      )}

      {/* Escalation */}
      {report?.escalation_recommendation?.required && (
        <div className="bg-red-500/10 border border-red-500/40 rounded-lg p-4">
          <p className="text-red-400 font-bold text-sm">
            ⚠️ ESCALATION REQUIRED — {report.escalation_recommendation.priority}
          </p>
          <p className="text-red-300 text-xs mt-1">
            Team: {report.escalation_recommendation.team} · {report.escalation_recommendation.reason}
          </p>
        </div>
      )}

      {/* Root causes */}
      {report?.root_cause_hypotheses && report.root_cause_hypotheses.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            🔍 Root Cause Hypotheses
            <span className="text-xs text-slate-500 font-normal">(ranked by likelihood)</span>
          </h3>
          <div className="space-y-2">
            {report.root_cause_hypotheses.map(h => <HypothesisCard key={h.rank} h={h} />)}
          </div>
        </div>
      )}

      {/* Remediation */}
      {report?.remediation_checklist && report.remediation_checklist.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-300 mb-3">🛠 Remediation Checklist</h3>
          <div className="space-y-2">
            {report.remediation_checklist.map((step: RemediationStep) => (
              <div key={step.priority} className="flex items-start gap-3 p-3 bg-slate-800 rounded-lg border border-slate-700">
                <span className="text-xs text-slate-400 font-bold flex-shrink-0 w-5 text-center">{step.priority}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200">{step.action}</p>
                  <div className="flex gap-3 mt-1">
                    {step.owner && <span className="text-xs text-slate-500">👤 {step.owner}</span>}
                    {step.estimated_time && <span className="text-xs text-slate-500">⏱ {step.estimated_time}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Similar past incidents */}
      {report?.similar_past_incidents && report.similar_past_incidents.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-300 mb-3">📂 Similar Past Incidents</h3>
          <div className="space-y-2">
            {report.similar_past_incidents.slice(0, 5).map((inc: SimilarIncident) => (
              <div key={inc.ticket_id} className="p-3 bg-slate-800 rounded-lg border border-slate-700">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="text-xs font-mono text-blue-400">{inc.ticket_id}</span>
                  {inc.source && (
                    <span className={`text-xs px-1 py-0.5 rounded border ${
                      inc.source === 'jira'
                        ? 'bg-blue-500/20 text-blue-300 border-blue-500/30'
                        : 'bg-purple-500/20 text-purple-300 border-purple-500/30'
                    }`}>{inc.source}</span>
                  )}
                  {inc.resolved_in_minutes && <span className="text-xs text-slate-500">✓ {inc.resolved_in_minutes}min</span>}
                  {inc.similarity_score !== undefined && (
                    <span className="text-xs text-slate-500 ml-auto">{Math.round(inc.similarity_score * 100)}% match</span>
                  )}
                </div>
                <p className="text-xs font-medium text-slate-300">{inc.title}</p>
                {inc.root_cause && <p className="text-xs text-slate-500 mt-1">Root cause: {inc.root_cause}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Post-mortem (if generated) */}
      {postMortem && (
        <div>
          <h3 className="text-sm font-semibold text-green-300 mb-3 flex items-center gap-2">
            📋 Post-Mortem
            <span className="text-xs text-slate-500 font-normal">{postMortem.generated_at?.slice(0, 10)}</span>
          </h3>
          <PostMortemView pm={postMortem} />
        </div>
      )}

      {/* Resolve button / form */}
      {isDone && !isResolved && !isResolving && !showResolveForm && (
        <div className="border-t border-slate-700 pt-4">
          <button
            onClick={() => setShowResolveForm(true)}
            className="w-full text-xs py-2 rounded-lg border border-green-600/50 text-green-400 hover:bg-green-600/10 transition-colors font-medium"
          >
            ✅ Mark as Resolved & Generate Post-Mortem
          </button>
        </div>
      )}

      {showResolveForm && (
        <ResolveForm
          incidentId={incident.incident_id}
          onSubmit={handleResolve}
          onCancel={() => setShowResolveForm(false)}
        />
      )}

      {isResolving && (
        <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4">
          <p className="text-xs text-green-300 animate-pulse">
            Generating post-mortem and updating knowledge base...
          </p>
        </div>
      )}

      {/* Error state */}
      {incident.status === 'failed' && incident.error && (
        <div className="bg-red-500/10 border border-red-500/40 rounded-lg p-4">
          <p className="text-red-400 font-bold text-sm">❌ Triage Failed</p>
          <p className="text-red-300 text-xs mt-1 font-mono">{incident.error}</p>
        </div>
      )}
    </div>
  )
}
