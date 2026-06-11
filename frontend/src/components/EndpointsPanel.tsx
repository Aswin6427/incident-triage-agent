import React, { useState } from 'react'

interface Endpoint {
  method: 'GET' | 'POST' | 'WS' | 'DEL'
  path: string
  desc: string
  basePort: number
}

interface ServiceGroup {
  name: string
  port: number
  color: string
  icon: string
  endpoints: Endpoint[]
}

const SERVICES: ServiceGroup[] = [
  {
    name: 'Backend API',
    port: 8000,
    color: 'text-blue-400',
    icon: '⚙️',
    endpoints: [
      { method: 'POST', path: '/alert',                    desc: 'Ingest alert & start triage',        basePort: 8000 },
      { method: 'GET',  path: '/incidents',                desc: 'List all incidents',                 basePort: 8000 },
      { method: 'GET',  path: '/incidents/{id}',           desc: 'Get incident + report',              basePort: 8000 },
      { method: 'POST', path: '/incidents/{id}/resolve',   desc: 'Resolve + generate post-mortem',     basePort: 8000 },
      { method: 'GET',  path: '/predictions',              desc: 'Current predictive alerts',          basePort: 8000 },
      { method: 'GET',  path: '/post-mortems',             desc: 'All generated post-mortems',         basePort: 8000 },
      { method: 'GET',  path: '/post-mortems/{id}',        desc: 'Get post-mortem by incident ID',     basePort: 8000 },
      { method: 'GET',  path: '/health',                   desc: 'Health check',                       basePort: 8000 },
      { method: 'GET',  path: '/docs',                     desc: 'Swagger UI',                         basePort: 8000 },
      { method: 'WS',   path: '/ws',                       desc: 'Live WebSocket updates',             basePort: 8000 },
    ],
  },
  {
    name: 'Mock Jira',
    port: 8001,
    color: 'text-blue-300',
    icon: '🎫',
    endpoints: [
      { method: 'GET', path: '/api/incidents/search', desc: 'Search past incidents', basePort: 8001 },
      { method: 'GET', path: '/api/incidents/{id}',   desc: 'Get ticket by ID',      basePort: 8001 },
      { method: 'GET', path: '/health',               desc: 'Health check',          basePort: 8001 },
    ],
  },
  {
    name: 'Mock Splunk',
    port: 8002,
    color: 'text-orange-300',
    icon: '📋',
    endpoints: [
      { method: 'GET', path: '/api/logs/search', desc: 'Search log entries',          basePort: 8002 },
      { method: 'GET', path: '/api/logs/stats',  desc: 'Log index statistics',        basePort: 8002 },
      { method: 'GET', path: '/api/logs/trends', desc: 'Error rate trend data',       basePort: 8002 },
      { method: 'GET', path: '/health',          desc: 'Health check',                basePort: 8002 },
    ],
  },
  {
    name: 'Mock ServiceNow',
    port: 8003,
    color: 'text-purple-300',
    icon: '🔧',
    endpoints: [
      { method: 'GET',  path: '/api/incidents/search', desc: 'Search incidents',   basePort: 8003 },
      { method: 'GET',  path: '/api/incidents/{id}',   desc: 'Get ticket by ID',   basePort: 8003 },
      { method: 'POST', path: '/api/incidents',        desc: 'Create new ticket',  basePort: 8003 },
      { method: 'GET',  path: '/api/incidents',        desc: 'List all tickets',   basePort: 8003 },
      { method: 'GET',  path: '/health',               desc: 'Health check',       basePort: 8003 },
    ],
  },
  {
    name: 'Mock Slack',
    port: 8004,
    color: 'text-green-300',
    icon: '💬',
    endpoints: [
      { method: 'POST', path: '/api/slack/post',              desc: 'Post report message',  basePort: 8004 },
      { method: 'GET',  path: '/api/slack/messages',          desc: 'List all messages',    basePort: 8004 },
      { method: 'GET',  path: '/api/slack/messages/{id}',     desc: 'Get message by ID',    basePort: 8004 },
      { method: 'GET',  path: '/health',                      desc: 'Health check',         basePort: 8004 },
    ],
  },
  {
    name: 'Mock On-Call',
    port: 8005,
    color: 'text-red-300',
    icon: '📟',
    endpoints: [
      { method: 'GET',  path: '/api/oncall/current',            desc: 'Current on-call engineer',    basePort: 8005 },
      { method: 'GET',  path: '/api/oncall/schedule',           desc: 'Full team schedule',          basePort: 8005 },
      { method: 'GET',  path: '/api/oncall/by-service/{svc}',   desc: 'On-call by service name',     basePort: 8005 },
      { method: 'POST', path: '/api/oncall/page',               desc: 'Page on-call engineer',       basePort: 8005 },
      { method: 'GET',  path: '/api/oncall/pages',              desc: 'List page events',            basePort: 8005 },
      { method: 'GET',  path: '/health',                        desc: 'Health check',                basePort: 8005 },
    ],
  },
]

const methodColors: Record<string, string> = {
  GET:  'bg-green-500/20 text-green-300 border-green-500/40',
  POST: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
  WS:   'bg-yellow-500/20 text-yellow-300 border-yellow-500/40',
  DEL:  'bg-red-500/20 text-red-300 border-red-500/40',
}

function EndpointRow({ ep }: { ep: Endpoint }) {
  const url = `http://localhost:${ep.basePort}${ep.path.replace(/{.*?}/g, '1')}`
  const displayUrl = `http://localhost:${ep.basePort}${ep.path}`
  const isClickable = ep.method === 'GET'

  return (
    <div className="flex items-start gap-2 py-1 group">
      <span className={`text-xs px-1 py-0.5 rounded border flex-shrink-0 font-mono ${methodColors[ep.method]}`}>
        {ep.method}
      </span>
      <div className="flex-1 min-w-0">
        {isClickable ? (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-mono text-slate-300 hover:text-white break-all leading-tight block"
            title={displayUrl}
          >
            {ep.path}
          </a>
        ) : (
          <span className="text-xs font-mono text-slate-400 break-all leading-tight block">
            {ep.path}
          </span>
        )}
        <p className="text-xs text-slate-600 leading-tight mt-0.5">{ep.desc}</p>
      </div>
    </div>
  )
}

function ServiceSection({ svc }: { svc: ServiceGroup }) {
  const [open, setOpen] = useState(true)
  const healthUrl = `http://localhost:${svc.port}/health`

  return (
    <div className="mb-3">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 text-left mb-1 group"
      >
        <span className="text-sm">{svc.icon}</span>
        <span className={`text-xs font-semibold ${svc.color} flex-1`}>{svc.name}</span>
        <a
          href={healthUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={e => e.stopPropagation()}
          className="text-xs text-slate-600 hover:text-green-400 mr-1"
          title="Health check"
        >
          :{svc.port}
        </a>
        <span className="text-slate-600 text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="pl-1 border-l border-slate-700 space-y-0.5">
          {svc.endpoints.map((ep) => (
            <EndpointRow key={`${ep.method}${ep.path}`} ep={ep} />
          ))}
        </div>
      )}
    </div>
  )
}

interface PanelProps {
  embedded?: boolean  // true = no fixed width/border, fills parent
}

export const EndpointsPanel: React.FC<PanelProps> = ({ embedded = false }) => {
  const outer = embedded
    ? 'flex flex-col h-full overflow-hidden'
    : 'w-60 flex-shrink-0 border-l border-slate-700 bg-slate-900 flex flex-col overflow-hidden'

  return (
    <div className={outer}>
      {!embedded && (
        <div className="px-3 py-3 border-b border-slate-700 flex-shrink-0">
          <h2 className="text-xs font-semibold text-slate-300 flex items-center gap-2">
            <span>🔌</span> API Endpoints
          </h2>
          <p className="text-xs text-slate-600 mt-0.5">Click GET paths to open</p>
        </div>
      )}

      {embedded && (
        <div className="px-3 py-2 border-b border-slate-700/50 flex-shrink-0">
          <p className="text-xs text-slate-500">Click GET paths to open in browser</p>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-3 py-2">
        {SERVICES.map((svc) => (
          <ServiceSection key={svc.name} svc={svc} />
        ))}
      </div>

      {/* Quick links */}
      <div className="border-t border-slate-700 px-3 py-2 flex-shrink-0 space-y-1">
        <p className="text-xs text-slate-500 font-medium mb-1">Quick Links</p>
        <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300">
          <span>📖</span> Swagger UI
        </a>
        <a href="http://localhost:5173" target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300">
          <span>🖥️</span> React UI
        </a>
      </div>
    </div>
  )
}
