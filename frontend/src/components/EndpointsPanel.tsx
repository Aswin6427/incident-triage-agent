import React, { useState } from 'react'

interface Endpoint {
  method: 'GET' | 'POST' | 'WS' | 'DEL'
  path: string
  desc: string
}

interface ServiceGroup {
  name: string
  port: number
  color: string
  icon: string
  app?: boolean   // true = this app's own API (browser-reachable via the proxy)
  endpoints: Endpoint[]
}

const SERVICES: ServiceGroup[] = [
  {
    name: 'Backend API',
    port: 8000,
    color: 'text-blue-400',
    icon: '⚙️',
    app: true,
    endpoints: [
      { method: 'POST', path: '/alert',                  desc: 'Ingest alert & start triage (opens the form)' },
      { method: 'GET',  path: '/incidents',              desc: 'List all incidents' },
      { method: 'GET',  path: '/incidents/{id}',         desc: 'Get incident + report (select a card)' },
      { method: 'POST', path: '/incidents/{id}/resolve', desc: 'Resolve + post-mortem (Resolve button)' },
      { method: 'GET',  path: '/predictions',            desc: 'Current predictive alerts' },
      { method: 'GET',  path: '/post-mortems',           desc: 'All generated post-mortems' },
      { method: 'GET',  path: '/post-mortems/{id}',      desc: 'Get post-mortem by incident ID' },
      { method: 'GET',  path: '/health',                 desc: 'Health check' },
      { method: 'GET',  path: '/docs',                   desc: 'Swagger UI' },
      { method: 'WS',   path: '/ws',                     desc: 'Live WebSocket updates' },
    ],
  },
  {
    name: 'Mock Jira',
    port: 8001, color: 'text-blue-300', icon: '🎫',
    endpoints: [
      { method: 'GET', path: '/api/incidents/search', desc: 'Search past incidents' },
      { method: 'GET', path: '/api/incidents/{id}',   desc: 'Get ticket by ID' },
    ],
  },
  {
    name: 'Mock Splunk',
    port: 8002, color: 'text-orange-300', icon: '📋',
    endpoints: [
      { method: 'GET', path: '/api/logs/search', desc: 'Search log entries' },
      { method: 'GET', path: '/api/logs/trends', desc: 'Error rate trend data' },
    ],
  },
  {
    name: 'Mock ServiceNow',
    port: 8003, color: 'text-purple-300', icon: '🔧',
    endpoints: [
      { method: 'GET',  path: '/api/incidents/search', desc: 'Search incidents' },
      { method: 'POST', path: '/api/incidents',        desc: 'Create new ticket' },
    ],
  },
  {
    name: 'Mock Slack',
    port: 8004, color: 'text-green-300', icon: '💬',
    endpoints: [
      { method: 'POST', path: '/api/slack/post',     desc: 'Post report message' },
      { method: 'GET',  path: '/api/slack/messages', desc: 'List all messages' },
    ],
  },
  {
    name: 'Mock On-Call',
    port: 8005, color: 'text-red-300', icon: '📟',
    endpoints: [
      { method: 'GET',  path: '/api/oncall/current', desc: 'Current on-call engineer' },
      { method: 'POST', path: '/api/oncall/page',    desc: 'Page on-call engineer' },
    ],
  },
]

const methodColors: Record<string, string> = {
  GET:  'bg-green-500/20 text-green-300 border-green-500/40',
  POST: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
  WS:   'bg-yellow-500/20 text-yellow-300 border-yellow-500/40',
  DEL:  'bg-red-500/20 text-red-300 border-red-500/40',
}

function EndpointRow({ ep, isApp, onNewAlert }: { ep: Endpoint; isApp: boolean; onNewAlert?: () => void }) {
  // App GET endpoints without a path param are browser-reachable via relative paths
  // (nginx proxy in prod, Vite proxy in dev). Mock endpoints are internal-only.
  const linkable = isApp && ep.method === 'GET' && !ep.path.includes('{')
  const isAlert  = isApp && ep.method === 'POST' && ep.path === '/alert'

  return (
    <div className="flex items-start gap-2 py-1">
      <span className={`text-xs px-1 py-0.5 rounded border flex-shrink-0 font-mono ${methodColors[ep.method]}`}>
        {ep.method}
      </span>
      <div className="flex-1 min-w-0">
        {isAlert && onNewAlert ? (
          <button onClick={onNewAlert}
                  className="text-xs font-mono text-blue-400 hover:text-blue-300 hover:underline break-all leading-tight block text-left">
            {ep.path}  ➜ open form
          </button>
        ) : linkable ? (
          <a href={ep.path} target="_blank" rel="noopener noreferrer"
             className="text-xs font-mono text-slate-300 hover:text-white break-all leading-tight block">
            {ep.path}
          </a>
        ) : (
          <span className="text-xs font-mono text-slate-400 break-all leading-tight block">{ep.path}</span>
        )}
        <p className="text-xs text-slate-600 leading-tight mt-0.5">{ep.desc}</p>
      </div>
    </div>
  )
}

function ServiceSection({ svc, onNewAlert }: { svc: ServiceGroup; onNewAlert?: () => void }) {
  const [open, setOpen] = useState(svc.app === true)

  return (
    <div className="mb-3">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-2 text-left mb-1">
        <span className="text-sm">{svc.icon}</span>
        <span className={`text-xs font-semibold ${svc.color} flex-1`}>{svc.name}</span>
        {!svc.app && <span className="text-xs text-slate-600 mr-1">internal</span>}
        <span className="text-slate-600 text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="pl-1 border-l border-slate-700 space-y-0.5">
          {!svc.app && (
            <p className="text-xs text-slate-600 italic py-0.5">Called server-side by the agents — not from the browser.</p>
          )}
          {svc.endpoints.map((ep) => (
            <EndpointRow key={`${ep.method}${ep.path}`} ep={ep} isApp={svc.app === true} onNewAlert={onNewAlert} />
          ))}
        </div>
      )}
    </div>
  )
}

interface PanelProps {
  embedded?: boolean
  onNewAlert?: () => void
}

export const EndpointsPanel: React.FC<PanelProps> = ({ embedded = false, onNewAlert }) => {
  const outer = embedded
    ? 'flex flex-col h-full overflow-hidden'
    : 'w-60 flex-shrink-0 border-l border-slate-700 bg-slate-900 flex flex-col overflow-hidden'

  return (
    <div className={outer}>
      <div className="px-3 py-2 border-b border-slate-700/50 flex-shrink-0">
        <p className="text-xs text-slate-500">App API is interactive · GET paths open in a new tab</p>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-2">
        {SERVICES.map((svc) => (
          <ServiceSection key={svc.name} svc={svc} onNewAlert={onNewAlert} />
        ))}
      </div>

      <div className="border-t border-slate-700 px-3 py-2 flex-shrink-0 space-y-1">
        <p className="text-xs text-slate-500 font-medium mb-1">Quick Links</p>
        <a href="/docs" target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300">
          <span>📖</span> Swagger UI (/docs)
        </a>
        {onNewAlert && (
          <button onClick={onNewAlert} className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300">
            <span>🚨</span> New Alert (POST /alert)
          </button>
        )}
      </div>
    </div>
  )
}
