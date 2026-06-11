import React from 'react'
import { Incident } from '../types'

interface Props {
  incident: Incident
}

const AGENTS = [
  { key: 'log_analyzer', label: 'Log Analyzer', icon: '📋', desc: 'Scanning Splunk/ELK logs' },
  { key: 'past_ticket',  label: 'Past Tickets',  icon: '🎫', desc: 'Searching Jira history' },
  { key: 'runbook',      label: 'Runbook RAG',   icon: '📖', desc: 'Retrieving runbook context' },
  { key: 'root_cause',   label: 'Root Cause',    icon: '🔍', desc: 'Synthesising hypotheses' },
]

const statusColors: Record<string, string> = {
  pending:   'text-slate-400',
  running:   'text-yellow-400',
  completed: 'text-green-400',
  failed:    'text-red-400',
}

const statusDot: Record<string, string> = {
  pending:   'bg-slate-600',
  running:   'bg-yellow-400 animate-pulse',
  completed: 'bg-green-400',
  failed:    'bg-red-400',
}

export const AgentStatusPanel: React.FC<Props> = ({ incident }) => {
  const report = incident.report

  // Derive agent statuses from incident state
  const agentStatus = (key: string): string => {
    if (!incident.status || incident.status === 'ingested') return 'pending'
    if (incident.status === 'done' || incident.status === 'failed') {
      if (key === 'root_cause' && incident.status === 'failed') return 'failed'
      return 'completed'
    }
    if (incident.status === 'analyzing') {
      return key === 'root_cause' ? 'pending' : 'running'
    }
    if (incident.status === 'reasoning') {
      return key === 'root_cause' ? 'running' : 'completed'
    }
    return 'running'
  }

  return (
    <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
      <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
        <span>🤖</span> Agent Pipeline
      </h3>

      <div className="space-y-3">
        {AGENTS.map((agent) => {
          const status = agentStatus(agent.key)
          return (
            <div key={agent.key} className="flex items-center gap-3">
              <span className="text-lg">{agent.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-200">{agent.label}</span>
                  <span className={`text-xs ${statusColors[status] || 'text-slate-400'}`}>
                    {status}
                  </span>
                </div>
                <p className="text-xs text-slate-500 truncate">{agent.desc}</p>
              </div>
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot[status] || 'bg-slate-600'}`} />
            </div>
          )
        })}
      </div>

      {/* Progress bar */}
      <div className="mt-4">
        <div className="flex justify-between text-xs text-slate-500 mb-1">
          <span>Progress</span>
          <span>{incident.progress_pct ?? 0}%</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-1.5">
          <div
            className="bg-red-500 h-1.5 rounded-full transition-all duration-500"
            style={{ width: `${incident.progress_pct ?? 0}%` }}
          />
        </div>
      </div>

      {incident.current_step && (
        <p className="mt-2 text-xs text-slate-400 italic">{incident.current_step}</p>
      )}

      {report?.elapsed_seconds && (
        <p className="mt-1 text-xs text-green-400 font-medium">
          ✅ Completed in {report.elapsed_seconds}s
        </p>
      )}
    </div>
  )
}
