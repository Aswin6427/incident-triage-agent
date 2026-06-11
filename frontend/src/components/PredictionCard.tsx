import React from 'react'
import { Prediction } from '../types'

interface Props {
  prediction: Prediction
  isSelected: boolean
  onClick: () => void
}

const confidenceColor: Record<string, string> = {
  High:   'text-orange-300',
  Medium: 'text-yellow-300',
  Low:    'text-slate-400',
}

export const PredictionCard: React.FC<Props> = ({ prediction, isSelected, onClick }) => {
  const etaLabel = prediction.eta_minutes < 10
    ? `${prediction.eta_minutes}m (critical!)`
    : `~${prediction.eta_minutes}m`

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg border transition-all duration-200 ${
        isSelected
          ? 'border-orange-500/60 bg-orange-500/10'
          : 'border-orange-800/50 bg-orange-950/30 hover:border-orange-600/50'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs px-1.5 py-0.5 rounded border font-bold bg-orange-500/20 text-orange-300 border-orange-500/40">
              PREDICTED
            </span>
            <span className="text-xs text-slate-400 truncate">{prediction.prediction_id}</span>
          </div>
          <p className="text-sm font-medium text-slate-200 truncate">{prediction.service}</p>
          <p className="text-xs text-slate-500 truncate mt-0.5">{prediction.alert_type}</p>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <span className={`text-xs font-medium ${confidenceColor[prediction.confidence] ?? 'text-slate-400'}`}>
            {prediction.confidence}
          </span>
          <span className="text-xs text-orange-400">ETA {etaLabel}</span>
        </div>
      </div>

      {/* Anomaly bar */}
      <div className="mt-2">
        <div className="flex justify-between text-xs text-slate-600 mb-0.5">
          <span>Anomaly</span>
          <span>{Math.round(prediction.anomaly_score * 100)}%</span>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-0.5">
          <div
            className="bg-orange-400 h-0.5 rounded-full transition-all duration-500"
            style={{ width: `${prediction.anomaly_score * 100}%` }}
          />
        </div>
      </div>
    </button>
  )
}
