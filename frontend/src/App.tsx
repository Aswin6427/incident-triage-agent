import React, { useState, useCallback, useEffect, useRef } from 'react'
import { AlertFeed } from './components/AlertFeed'
import { TriageReport } from './components/TriageReport'
import { AgentFlowPanel } from './components/AgentFlowPanel'
import { useWebSocket } from './hooks/useWebSocket'
import { Incident, Prediction, WsEvent, AgentSteps } from './types'

function mergeAgentSteps(existing: AgentSteps | undefined, update: AgentSteps | undefined): AgentSteps {
  if (!update) return existing ?? {}
  return { ...(existing ?? {}), ...update }
}

function App() {
  const [incidents,   setIncidents]   = useState<Record<string, Incident>>({})
  const [predictions, setPredictions] = useState<Record<string, Prediction>>({})
  const [selectedId,  setSelectedId]  = useState<string | null>(null)
  const prevConnected = useRef(false)

  const fetchIncidents = useCallback((autoSelect = false) => {
    fetch('/incidents')
      .then(r => r.json())
      .then((list: any[]) => {
        if (!list.length) return
        const map: Record<string, Incident> = {}
        list.forEach((inc: any) => { map[inc.incident_id] = inc })
        setIncidents(map)
        if (autoSelect) {
          const sorted = list.sort((a, b) => (b.received_at ?? 0) - (a.received_at ?? 0))
          setSelectedId(sorted[0].incident_id)
        }
      })
      .catch(() => {})
  }, [])

  const handleWsMessage = useCallback((event: WsEvent) => {
    if (event.event === 'connected') {
      fetchIncidents(false)
      return
    }

    if (event.event === 'prediction' && event.prediction_id) {
      const pred: Prediction = {
        prediction_id:           event.prediction_id,
        service:                 event.service ?? '',
        alert_type:              event.alert_type ?? '',
        predicted:               true,
        confidence:              (event.confidence as any) ?? 'Medium',
        severity:                (event.severity as any) ?? 'P3',
        eta_minutes:             event.eta_minutes ?? 15,
        anomaly_score:           event.anomaly_score ?? 0,
        current_error_rate_pct:  (event as any).current_error_rate_pct ?? 0,
        baseline_error_rate_pct: (event as any).baseline_error_rate_pct ?? 1,
        trend:                   (event as any).trend ?? 'stable',
        top_error_codes:         (event as any).top_error_codes ?? [],
        description:             event.description ?? '',
        detected_at:             event.detected_at ?? Date.now() / 1000,
        data_points:             (event as any).data_points,
      }
      setPredictions(prev => ({ ...prev, [event.prediction_id!]: pred }))
      return
    }

    if (event.event === 'post_mortem_complete' && event.incident_id && event.post_mortem) {
      setIncidents(prev => {
        const existing = prev[event.incident_id!]
        if (!existing) return prev
        return {
          ...prev,
          [event.incident_id!]: {
            ...existing,
            status:     'resolved',
            post_mortem: event.post_mortem,
          },
        }
      })
      return
    }

    if (event.event === 'new_alert' && event.incident_id && event.alert) {
      setIncidents(prev => ({
        ...prev,
        [event.incident_id!]: {
          incident_id: event.incident_id!,
          status:      event.status ?? 'ingested',
          progress_pct: 5,
          alert:       event.alert,
          report:      undefined,
          received_at: Date.now(),
          agent_steps: event.agent_steps ?? {},
        },
      }))
      setSelectedId(event.incident_id!)
    }

    if (event.event === 'incident_update' && event.incident_id) {
      setIncidents(prev => {
        const existing = prev[event.incident_id!]
        if (!existing) return prev
        const mergedSteps = event.agent_steps
          ? event.agent_steps
          : mergeAgentSteps(existing.agent_steps, event.agent_step_update)
        return {
          ...prev,
          [event.incident_id!]: {
            ...existing,
            status:      event.status ?? existing.status,
            progress_pct: event.progress_pct ?? existing.progress_pct,
            current_step: event.current_step ?? existing.current_step,
            report:      event.report ?? existing.report,
            error:       event.error ?? existing.error,
            agent_steps: mergedSteps,
          },
        }
      })
    }
  }, [fetchIncidents])

  const { isConnected } = useWebSocket(handleWsMessage)

  useEffect(() => {
    if (isConnected && !prevConnected.current) fetchIncidents(false)
    prevConnected.current = isConnected
  }, [isConnected, fetchIncidents])

  useEffect(() => { fetchIncidents(true) }, [])

  const handleResolve = useCallback(async (
    incidentId: string, resolution: string, rootCause: string, resolvedBy: string
  ) => {
    setIncidents(prev => ({
      ...prev,
      [incidentId]: { ...prev[incidentId], status: 'resolving', current_step: 'Generating post-mortem...' },
    }))
    try {
      await fetch(`/incidents/${incidentId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resolution_summary:   resolution,
          confirmed_root_cause: rootCause,
          resolved_by:          resolvedBy,
        }),
      })
    } catch (err) {
      console.error('Resolve failed:', err)
    }
  }, [])

  // Determine what to show in the center
  const selectedIncident  = selectedId ? incidents[selectedId]   : null
  const selectedPrediction = selectedId ? predictions[selectedId] : null

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">

      {/* LEFT: Incident feed + predictions + API endpoints tab */}
      <AlertFeed
        incidents={incidents}
        predictions={predictions}
        selectedId={selectedId}
        onSelect={setSelectedId}
        isConnected={isConnected}
      />

      {/* CENTER-LEFT: Agent flow (always visible) */}
      <div className="w-72 flex-shrink-0 border-r border-slate-700 bg-slate-900 overflow-y-auto">
        {selectedIncident ? (
          <div className="p-3">
            <AgentFlowPanel incident={selectedIncident} />
          </div>
        ) : selectedPrediction ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4 py-8">
            <p className="text-4xl mb-3">⚠️</p>
            <p className="text-sm font-medium text-orange-400">Predictive Alert</p>
            <p className="text-xs text-slate-500 mt-1">No agent flow — prediction detected before incident occurred</p>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center px-4 py-8">
            <p className="text-3xl mb-3">🤖</p>
            <p className="text-sm font-medium text-slate-400">Agent Flow</p>
            <p className="text-xs text-slate-600 mt-1">Select an incident to see the pipeline</p>
          </div>
        )}
      </div>

      {/* CENTER-RIGHT: Triage report / prediction detail */}
      <main className="flex-1 overflow-hidden">
        {selectedIncident ? (
          <TriageReport incident={selectedIncident} onResolve={handleResolve} />
        ) : selectedPrediction ? (
          <TriageReport prediction={selectedPrediction} />
        ) : (
          <div className="flex items-center justify-center h-full text-slate-500">
            <div className="text-center">
              <p className="text-5xl mb-4">🚨</p>
              <p className="text-lg font-medium text-slate-400">Incident Triage Agent</p>
              <p className="text-sm mt-2">Waiting for alerts...</p>
              <div className="mt-6 text-xs text-slate-600 space-y-1">
                <p>Push a test alert:</p>
                <code className="bg-slate-800 px-3 py-1.5 rounded block text-slate-400">
                  python scripts/push_alert.py --scenario db_timeout
                </code>
              </div>
              {!isConnected && (
                <p className="mt-4 text-xs text-red-400">Not connected to backend — is it running on port 8000?</p>
              )}
            </div>
          </div>
        )}
      </main>

    </div>
  )
}

export default App
