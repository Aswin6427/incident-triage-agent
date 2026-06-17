import React, { useState } from 'react'

// Mirrors backend AlertType / AlertSeverity enums (backend/models/alert.py)
const ALERT_TYPES = [
  'DB_CONNECTION_TIMEOUT', 'HIGH_ERROR_RATE', 'MEMORY_LEAK', 'DEPLOY_REGRESSION',
  'DEPENDENCY_FAILURE', 'LATENCY_SPIKE', 'CPU_SPIKE', 'DISK_FULL',
]
const SEVERITIES = ['P1', 'P2', 'P3', 'P4']

function genId(): string {
  return `INC-${Math.random().toString(36).slice(2, 8).toUpperCase()}`
}

const inputCls =
  'w-full bg-slate-800 border border-slate-700 rounded-md px-2.5 py-1.5 text-sm text-slate-100 ' +
  'focus:outline-none focus:border-blue-500'
const labelCls = 'text-xs text-slate-400 block mb-1'

interface Props {
  onClose: () => void
  onCreated?: (incidentId: string) => void
}

/** Form that POSTs a manual alert to /alert (mirrors AlertPayload). */
export const NewAlertModal: React.FC<Props> = ({ onClose, onCreated }) => {
  const [incidentId, setIncidentId] = useState(genId())
  const [service, setService] = useState('')
  const [alertType, setAlertType] = useState(ALERT_TYPES[0])
  const [severity, setSeverity] = useState('P1')
  const [region, setRegion] = useState('us-east-1')
  const [errorCode, setErrorCode] = useState('')
  const [endpoints, setEndpoints] = useState('')
  const [errorRate, setErrorRate] = useState('')
  const [latency, setLatency] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!service.trim()) { setError('Service is required'); return }
    setSubmitting(true)
    setError(null)

    const metrics: Record<string, string> = {}
    if (errorRate.trim()) metrics.error_rate = errorRate.trim()
    if (latency.trim()) metrics.latency_p99 = latency.trim()

    const payload: Record<string, unknown> = {
      incident_id: incidentId.trim() || genId(),
      service: service.trim(),
      alert_type: alertType,
      severity,
      region: region.trim() || 'us-east-1',
      source: 'manual-ui',
    }
    if (errorCode.trim()) payload.error_code = errorCode.trim()
    if (endpoints.trim()) {
      payload.affected_endpoints = endpoints.split(',').map(s => s.trim()).filter(Boolean)
    }
    if (Object.keys(metrics).length) payload.metrics = metrics
    if (description.trim()) payload.description = description.trim()

    try {
      const res = await fetch('/alert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`)
      }
      onCreated?.(payload.incident_id as string)
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to post alert')
      setSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-700 sticky top-0 bg-slate-900 z-10">
          <h2 className="text-base font-bold text-white flex items-center gap-2">🚨 New Alert</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl leading-none">×</button>
        </div>

        <form onSubmit={submit} className="p-5 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Incident ID</label>
              <input className={inputCls} value={incidentId} onChange={e => setIncidentId(e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Service <span className="text-red-400">*</span></label>
              <input className={inputCls} value={service} placeholder="payment-service"
                     onChange={e => setService(e.target.value)} required />
            </div>
            <div>
              <label className={labelCls}>Alert Type <span className="text-red-400">*</span></label>
              <select className={inputCls} value={alertType} onChange={e => setAlertType(e.target.value)}>
                {ALERT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Severity</label>
              <select className={inputCls} value={severity} onChange={e => setSeverity(e.target.value)}>
                {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Region</label>
              <input className={inputCls} value={region} onChange={e => setRegion(e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Error Code</label>
              <input className={inputCls} value={errorCode} placeholder="CONN_TIMEOUT_5023"
                     onChange={e => setErrorCode(e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Error Rate</label>
              <input className={inputCls} value={errorRate} placeholder="23%"
                     onChange={e => setErrorRate(e.target.value)} />
            </div>
            <div>
              <label className={labelCls}>Latency p99</label>
              <input className={inputCls} value={latency} placeholder="8200ms"
                     onChange={e => setLatency(e.target.value)} />
            </div>
          </div>

          <div>
            <label className={labelCls}>Affected Endpoints <span className="text-slate-600">(comma-separated)</span></label>
            <input className={inputCls} value={endpoints} placeholder="/api/checkout, /api/payment"
                   onChange={e => setEndpoints(e.target.value)} />
          </div>

          <div>
            <label className={labelCls}>Description</label>
            <textarea className={inputCls} rows={2} value={description}
                      placeholder="Database connection pool exhausted…"
                      onChange={e => setDescription(e.target.value)} />
          </div>

          {error && (
            <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded px-2 py-1.5">{error}</p>
          )}

          <div className="flex gap-2 pt-1">
            <button type="button" onClick={onClose}
                    className="flex-1 text-sm py-2 rounded-md border border-slate-600 text-slate-300 hover:bg-slate-800">
              Cancel
            </button>
            <button type="submit" disabled={submitting}
                    className="flex-1 text-sm py-2 rounded-md bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-50">
              {submitting ? 'Posting…' : 'Post Alert'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
