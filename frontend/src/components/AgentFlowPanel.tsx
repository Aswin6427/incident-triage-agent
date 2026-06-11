import React from 'react'
import { AgentSteps, AgentStepInfo, Incident } from '../types'

interface Props {
  incident: Incident
}

type NodeStatus = 'pending' | 'running' | 'completed' | 'failed'

interface FlowNode {
  id: string
  label: string
  icon: string
  sublabel?: string
}

const PARALLEL_IDS = new Set(['log_analyzer_node', 'past_ticket_node', 'runbook_node'])

const FLOW: FlowNode[] = [
  { id: 'ingest_node',       label: 'Ingest',        icon: '📥' },
  { id: 'log_analyzer_node', label: 'Log Analyzer',  icon: '📋', sublabel: 'Splunk / ELK' },
  { id: 'past_ticket_node',  label: 'Past Tickets',  icon: '🎫', sublabel: 'Jira + ServiceNow' },
  { id: 'runbook_node',      label: 'Runbook RAG',   icon: '📖', sublabel: 'FAISS search' },
  { id: 'root_cause_node',   label: 'Root Cause',    icon: '🔍', sublabel: 'LLM synthesis' },
  { id: 'report_node',       label: 'Report',        icon: '📊', sublabel: 'Slack + dashboard' },
]

const statusBg: Record<NodeStatus, string> = {
  pending:   'bg-slate-800/60 border-slate-600',
  running:   'bg-yellow-900/30 border-yellow-500',
  completed: 'bg-green-900/30 border-green-500',
  failed:    'bg-red-900/30 border-red-500',
}

const statusDot: Record<NodeStatus, string> = {
  pending:   'bg-slate-600',
  running:   'bg-yellow-400 animate-pulse',
  completed: 'bg-green-400',
  failed:    'bg-red-400',
}

const statusLabel: Record<NodeStatus, string> = {
  pending:   'text-slate-600',
  running:   'text-yellow-400',
  completed: 'text-green-400',
  failed:    'text-red-400',
}

function getStatus(steps: AgentSteps | undefined, nodeId: string): NodeStatus {
  return (steps?.[nodeId]?.status as NodeStatus) ?? 'pending'
}

function NodeBox({ node, info, compact = false }: { node: FlowNode; info?: AgentStepInfo; compact?: boolean }) {
  const status = (info?.status as NodeStatus) ?? 'pending'
  const label  = info?.label || node.label

  return (
    <div className={`rounded-lg border transition-all duration-300 ${statusBg[status]} ${compact ? 'px-2.5 py-1.5' : 'px-3 py-2'}`}>
      {/* Main row */}
      <div className="flex items-center gap-2">
        <span className={compact ? 'text-sm' : 'text-base flex-shrink-0'}>{node.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 justify-between">
            <p className="text-xs font-semibold text-slate-200 leading-tight truncate">{label}</p>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <span className={`text-xs ${statusLabel[status]}`}>
                {status === 'running' ? '…' : status === 'completed' ? '✓' : status === 'failed' ? '✕' : ''}
              </span>
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${statusDot[status]}`} />
            </div>
          </div>
          {node.sublabel && (
            <p className="text-xs text-slate-500 leading-tight">{node.sublabel}</p>
          )}
        </div>
      </div>

      {/* Past ticket extras */}
      {node.id === 'past_ticket_node' && status === 'running' && (
        <div className="mt-1.5 flex gap-1.5 pl-6">
          <span className="text-xs bg-blue-500/20 text-blue-300 border border-blue-400/30 px-1.5 py-0.5 rounded animate-pulse">Jira</span>
          <span className="text-xs bg-purple-500/20 text-purple-300 border border-purple-400/30 px-1.5 py-0.5 rounded animate-pulse">ServiceNow</span>
        </div>
      )}
      {node.id === 'past_ticket_node' && status === 'completed' && info?.open_tickets_count !== undefined && (
        <div className="mt-1.5 pl-6">
          {info.open_tickets_count > 0 ? (
            <span className="text-xs bg-red-500/20 text-red-300 border border-red-500/40 px-1.5 py-0.5 rounded">
              {info.open_tickets_count} open ticket{info.open_tickets_count !== 1 ? 's' : ''}
            </span>
          ) : (
            <span className="text-xs text-slate-500">No open tickets</span>
          )}
        </div>
      )}
    </div>
  )
}

function VConnector({ active }: { active: boolean }) {
  return (
    <div className="flex justify-center h-3">
      <div className={`w-0.5 h-full rounded-full transition-colors duration-300 ${active ? 'bg-green-500/50' : 'bg-slate-700'}`} />
    </div>
  )
}

function ParallelBracket({ active, label }: { active: boolean; label: string }) {
  const c = active ? 'border-green-500/40 text-green-500/70' : 'border-slate-700 text-slate-600'
  return (
    <div className={`flex items-center gap-1.5 my-0.5`}>
      <div className={`flex-1 border-t ${active ? 'border-green-500/40' : 'border-slate-700'}`} />
      <span className={`text-xs font-medium px-1.5 ${c}`}>{label}</span>
      <div className={`flex-1 border-t ${active ? 'border-green-500/40' : 'border-slate-700'}`} />
    </div>
  )
}

export const AgentFlowPanel: React.FC<Props> = ({ incident }) => {
  const steps     = incident.agent_steps
  const report    = incident.report
  const isDone    = incident.status === 'done'
  const isFailed  = incident.status === 'failed'
  const isRunning = !isDone && !isFailed && incident.status !== 'ingested'

  const ingestDone   = getStatus(steps, 'ingest_node') === 'completed'
  const parallelDone = [...PARALLEL_IDS].every(id => getStatus(steps, id) === 'completed')
  const rcDone       = getStatus(steps, 'root_cause_node') === 'completed'

  const openTicketsCount = report?.open_tickets?.length
    ?? steps?.past_ticket_node?.open_tickets_count
    ?? 0

  return (
    <div className="bg-slate-800 rounded-xl p-3 border border-slate-700">

      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm">🤖</span>
        <h3 className="text-sm font-semibold text-slate-300 flex-1">Agent Flow</h3>
        {isDone    && <span className="text-xs text-green-400 font-medium">✓ {report?.elapsed_seconds}s</span>}
        {isFailed  && <span className="text-xs text-red-400 font-medium">failed</span>}
        {isRunning && <span className="text-xs text-yellow-400 font-medium animate-pulse">running</span>}
      </div>

      {/* INGEST */}
      <NodeBox node={FLOW[0]} info={steps?.ingest_node} />
      <VConnector active={ingestDone} />

      {/* Parallel section */}
      <ParallelBracket active={ingestDone} label="parallel" />
      <div className="space-y-1.5 pl-2 border-l-2 border-slate-700 ml-1">
        <NodeBox node={FLOW[1]} info={steps?.log_analyzer_node} compact />
        <NodeBox node={FLOW[2]} info={steps?.past_ticket_node}  compact />
        <NodeBox node={FLOW[3]} info={steps?.runbook_node}      compact />
      </div>
      <ParallelBracket active={parallelDone} label="merge" />

      <VConnector active={parallelDone} />

      {/* ROOT CAUSE */}
      <NodeBox node={FLOW[4]} info={steps?.root_cause_node} />
      <VConnector active={rcDone} />

      {/* REPORT */}
      <NodeBox node={FLOW[5]} info={steps?.report_node} />

      {/* Open tickets summary */}
      {openTicketsCount > 0 && isDone && (
        <div className="mt-2.5 p-2 rounded-lg bg-red-500/10 border border-red-500/30">
          <p className="text-xs text-red-300 font-medium">
            🔥 {openTicketsCount} open ticket{openTicketsCount !== 1 ? 's' : ''} found
          </p>
          <p className="text-xs text-red-400/70 mt-0.5">Related incidents already tracked</p>
        </div>
      )}

      {/* Progress bar */}
      <div className="mt-3">
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
        <p className="mt-2 text-xs text-slate-400 italic truncate" title={incident.current_step}>
          {incident.current_step}
        </p>
      )}
    </div>
  )
}
