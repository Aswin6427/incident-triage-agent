import React, { useState } from 'react'
import { Incident, Prediction } from '../types'
import { IncidentCard } from './IncidentCard'
import { PredictionCard } from './PredictionCard'
import { EndpointsPanel } from './EndpointsPanel'

interface Props {
  incidents: Record<string, Incident>
  predictions: Record<string, Prediction>
  selectedId: string | null
  onSelect: (id: string) => void
  isConnected: boolean
}

type Tab = 'feed' | 'endpoints'

export const AlertFeed: React.FC<Props> = ({
  incidents, predictions, selectedId, onSelect, isConnected,
}) => {
  const [activeTab, setActiveTab] = useState<Tab>('feed')

  const sortedIncidents = Object.values(incidents).sort(
    (a, b) => (b.received_at ?? 0) - (a.received_at ?? 0)
  )
  const sortedPredictions = Object.values(predictions).sort(
    (a, b) => (b.detected_at ?? 0) - (a.detected_at ?? 0)
  )
  const p1Count  = sortedIncidents.filter(i => i.alert?.severity === 'P1').length
  const predCount = sortedPredictions.length

  return (
    <aside className="w-80 flex-shrink-0 flex flex-col bg-slate-900 border-r border-slate-700 h-screen">

      {/* Header */}
      <div className="px-4 pt-4 pb-2 border-b border-slate-700 flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-base font-bold text-white flex items-center gap-2">
            🚨 Incident Triage
          </h1>
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-xs text-slate-400">{isConnected ? 'Live' : 'Offline'}</span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('feed')}
            className={`flex-1 text-xs font-medium py-1.5 rounded-md transition-colors ${
              activeTab === 'feed' ? 'bg-slate-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Incident Feed
            {(sortedIncidents.length + predCount) > 0 && (
              <span className="ml-1.5 text-xs bg-slate-500/50 px-1.5 py-0.5 rounded-full">
                {sortedIncidents.length + predCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('endpoints')}
            className={`flex-1 text-xs font-medium py-1.5 rounded-md transition-colors ${
              activeTab === 'endpoints' ? 'bg-slate-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            API Endpoints
          </button>
        </div>
      </div>

      {/* Tab: Incident Feed */}
      {activeTab === 'feed' && (
        <>
          <div className="px-4 py-2 flex items-center gap-3 border-b border-slate-700/50 flex-shrink-0">
            <p className="text-xs text-slate-500">
              {sortedIncidents.length} incident{sortedIncidents.length !== 1 ? 's' : ''}
            </p>
            {p1Count > 0 && (
              <span className="text-xs font-bold px-1.5 py-0.5 rounded border bg-red-500/20 text-red-400 border-red-500/40">
                {p1Count} P1
              </span>
            )}
            {predCount > 0 && (
              <span className="text-xs font-bold px-1.5 py-0.5 rounded border bg-orange-500/20 text-orange-400 border-orange-500/40 ml-auto">
                {predCount} predicted
              </span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {/* Predictions at top */}
            {sortedPredictions.length > 0 && (
              <div>
                <p className="text-xs text-orange-400 font-semibold mb-1.5 flex items-center gap-1">
                  <span>⚠️</span> Predicted Alerts
                </p>
                <div className="space-y-2">
                  {sortedPredictions.map(pred => (
                    <PredictionCard
                      key={pred.prediction_id}
                      prediction={pred}
                      isSelected={selectedId === pred.prediction_id}
                      onClick={() => onSelect(pred.prediction_id)}
                    />
                  ))}
                </div>
                {sortedIncidents.length > 0 && (
                  <div className="border-t border-slate-700/50 mt-3 mb-1" />
                )}
              </div>
            )}

            {/* Active incidents */}
            {sortedIncidents.length === 0 && predCount === 0 ? (
              <div className="text-center text-slate-500 text-sm mt-12 px-4">
                <p className="text-3xl mb-3">🟢</p>
                <p className="font-medium">No active incidents</p>
                <p className="text-xs mt-1">Push an alert to start triage:</p>
                <code className="text-xs text-slate-400 mt-2 block bg-slate-800 px-2 py-1 rounded">
                  python scripts/push_alert.py --scenario db_timeout
                </code>
              </div>
            ) : (
              sortedIncidents.map(inc => (
                <IncidentCard
                  key={inc.incident_id}
                  incident={inc}
                  isSelected={selectedId === inc.incident_id}
                  onClick={() => onSelect(inc.incident_id)}
                />
              ))
            )}
          </div>
        </>
      )}

      {/* Tab: API Endpoints */}
      {activeTab === 'endpoints' && (
        <div className="flex-1 overflow-hidden">
          <EndpointsPanel embedded />
        </div>
      )}

    </aside>
  )
}
