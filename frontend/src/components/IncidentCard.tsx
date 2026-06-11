import React from 'react'
import { Incident } from '../types'

interface Props {
  incident: Incident
  isSelected: boolean
  onClick: () => void
}

const severityColors: Record<string, string> = {
  P1: 'bg-red-500/20 text-red-400 border-red-500/40',
  P2: 'bg-orange-500/20 text-orange-400 border-orange-500/40',
  P3: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
  P4: 'bg-blue-500/20 text-blue-400 border-blue-500/40',
}

const statusColors: Record<string, string> = {
  ingested:   'text-slate-400',
  analyzing:  'text-yellow-400',
  correlating:'text-yellow-400',
  reasoning:  'text-blue-400',
  reporting:  'text-blue-400',
  done:       'text-green-400',
  failed:     'text-red-400',
}

const statusEmoji: Record<string, string> = {
  ingested:   '📥',
  analyzing:  '🔄',
  correlating:'🔄',
  reasoning:  '🧠',
  reporting:  '📝',
  done:       '✅',
  failed:     '❌',
}

export const IncidentCard: React.FC<Props> = ({ incident, isSelected, onClick }) => {
  const alert = incident.alert
  const severity = alert?.severity ?? 'P2'
  const status = incident.status

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg border transition-all duration-200 ${
        isSelected
          ? 'border-red-500/60 bg-red-500/10'
          : 'border-slate-700 bg-slate-800 hover:border-slate-600 hover:bg-slate-750'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`text-xs px-1.5 py-0.5 rounded border font-bold ${severityColors[severity] || severityColors['P2']}`}
            >
              {severity}
            </span>
            <span className="text-xs text-slate-400 truncate">{incident.incident_id}</span>
          </div>

          <p className="text-sm font-medium text-slate-200 truncate">
            {alert?.service ?? 'Unknown Service'}
          </p>
          <p className="text-xs text-slate-500 truncate mt-0.5">
            {alert?.alert_type ?? 'Unknown Alert'}
          </p>
        </div>

        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <span className={`text-xs font-medium ${statusColors[status] || 'text-slate-400'}`}>
            {statusEmoji[status]} {status}
          </span>
          {incident.progress_pct !== undefined && status !== 'done' && status !== 'failed' && (
            <span className="text-xs text-slate-500">{incident.progress_pct}%</span>
          )}
        </div>
      </div>

      {/* Mini progress bar */}
      {status !== 'ingested' && status !== 'done' && status !== 'failed' && (
        <div className="mt-2 w-full bg-slate-700 rounded-full h-0.5">
          <div
            className="bg-red-500 h-0.5 rounded-full transition-all duration-500"
            style={{ width: `${incident.progress_pct ?? 0}%` }}
          />
        </div>
      )}
    </button>
  )
}
