# Incident Triage & Root Cause AI Agent

> Automatically correlate logs, alerts and past tickets during live production incidents using a multi-agent AI pipeline.

---

## Architecture

```
Alert Source (push_alert.py)
       |
       v
FastAPI /alert  (main.py)
       |
       v
LangGraph Orchestrator  (orchestrator/graph.py)
       |
       +--[parallel]--+---------------------------+
       |              |                           |
       v              v                           v
LogAnalyzerAgent  PastTicketAgent            RunbookAgent
(Splunk 100k logs) (Jira + ServiceNow)       (FAISS RAG)
       |              |                           |
       |         [open ticket detection]          |
       +--[merge]-----+---------------------------+
                      |
                      v
               RootCauseAgent
          (LLM synthesis w/ open tickets)
                      |
                      v
               report_node
          (TriageReport + Slack post)
                      |
                      v
         WebSocket broadcast -> React UI
```

**Key design decisions:**
- All external calls go through the **MCP Gateway** — agents never call services directly
- Three agents run **in parallel** after ingest, then fan-in to root cause
- **Open ticket detection**: if Jira or ServiceNow has an active ticket for the same service/alert, the report explicitly references it
- **Real-time UI**: LangGraph `astream` streams per-node completions as WebSocket events

---

## Quick Start

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.8+ |
| Node.js | 16+ |
| Azure OpenAI | API access required |

### Option A — One-command startup (recommended)

```powershell
# Start all 6 services (mocks + backend + frontend)
.\start.ps1

# Stop all services
.\stop.ps1
```

`start.ps1` handles: venv creation, pip install, RAG index build, npm install, log file check, and launching all 6 services in separate windows.

### Option B — Manual setup

**1. Configure environment**
```powershell
copy .env.example .env
# Edit .env — fill in AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME
```

**2. Create virtual environment and install dependencies**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**3. Generate the 100k application log file**
```powershell
python scripts/generate_logs.py
# Writes 100,000 log entries to backend/data/logs/application.log (~23 MB)
```

**4. Build the RAG knowledge base**
```powershell
cd backend
python -m rag.pipeline
```

**5. Start mock services (4 separate terminals)**
```powershell
# Mock Jira (port 8001)
uvicorn backend.mocks.mock_jira:app --port 8001 --reload

# Mock Splunk/ELK (port 8002) — serves from 100k log file
uvicorn backend.mocks.mock_splunk:app --port 8002 --reload

# Mock ServiceNow (port 8003)
uvicorn backend.mocks.mock_servicenow:app --port 8003 --reload

# Mock Slack (port 8004)
uvicorn backend.mocks.mock_slack:app --port 8004 --reload
```

**6. Start main backend**
```powershell
$env:PYTHONPATH = "."
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**7. Start frontend**
```powershell
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

**8. Push test alerts**
```powershell
python scripts/push_alert.py --scenario db_timeout
```

---

## Alert Scenarios

Push any combination via `scripts/push_alert.py`:

| `--scenario` flag | Service | Alert Type | Severity |
|---|---|---|---|
| `db_timeout` | payment-service | DB_CONNECTION_TIMEOUT | P1 |
| `high_error_rate` | auth-service | HIGH_ERROR_RATE | P1 |
| `memory_leak` | recommendation-engine | MEMORY_LEAK | P1 |
| `deploy_regression` | checkout-service | DEPLOY_REGRESSION | P1 |
| `dependency_failure` | notification-service | DEPENDENCY_FAILURE | P2 |

Push all at once:
```powershell
foreach ($s in @("db_timeout","high_error_rate","memory_leak","deploy_regression","dependency_failure")) {
    python scripts/push_alert.py --scenario $s
    Start-Sleep -Seconds 5
}
```

---

## Service URLs

| Service | URL | Purpose |
|---|---|---|
| React UI | http://localhost:5173 | Live dashboard |
| FastAPI backend | http://localhost:8000 | Main API |
| Swagger / API docs | http://localhost:8000/docs | Interactive API explorer |
| Mock Jira | http://localhost:8001 | Past incident tickets |
| Mock Splunk | http://localhost:8002 | Log search (100k entries) |
| Mock ServiceNow | http://localhost:8003 | IT service management |
| Mock Slack | http://localhost:8004 | Report delivery |

---

## API Reference

### Backend (port 8000)

| Method | Path | Description |
|---|---|---|
| `POST` | `/alert` | Ingest an alert and start triage (returns 202 immediately) |
| `GET` | `/incidents` | List all incidents with full state including reports |
| `GET` | `/incidents/{id}` | Get full status and triage report for one incident |
| `GET` | `/health` | Health check |
| `WS` | `/ws` | WebSocket — live incident updates to the React UI |

### Mock Jira (port 8001)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/incidents/search` | Search past tickets by `service`, `alert_type`, `error_code` |
| `GET` | `/api/incidents/{ticket_id}` | Get a specific ticket |
| `GET` | `/health` | Health check |

### Mock Splunk (port 8002)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/logs/search` | Return logs for `service` within `window_minutes` |
| `GET` | `/api/logs/stats` | Show log index stats (total entries per service) |
| `GET` | `/health` | Health check |

### Mock ServiceNow (port 8003)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/incidents/search` | Search incidents by `service`, `alert_type`, `error_code` |
| `GET` | `/api/incidents/{ticket_id}` | Get a specific ticket |
| `POST` | `/api/incidents` | Create a new incident ticket |
| `GET` | `/api/incidents` | List all tickets |
| `GET` | `/health` | Health check |

### Mock Slack (port 8004)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/slack/post` | Post a formatted triage report |
| `GET` | `/api/slack/messages` | List all posted messages |
| `GET` | `/health` | Health check |

---

## Project Structure

```
incident-triage-agent/
|
|-- backend/
|   |-- main.py                  # FastAPI app, /alert endpoint, WebSocket, astream
|   |-- config.py                # Settings from .env (timeout, URLs, RAG config)
|   |-- models/
|   |   |-- alert.py             # AlertPayload, AlertType, AlertSeverity
|   |   +-- report.py            # TriageReport, RootCauseHypothesis, OpenTicket
|   |
|   |-- orchestrator/
|   |   |-- graph.py             # LangGraph nodes: ingest->parallel->root_cause->report
|   |   |-- state.py             # IncidentState TypedDict (incl. open_tickets)
|   |   +-- supervisor.py        # Routing logic between nodes
|   |
|   |-- agents/
|   |   |-- log_analyzer.py      # Queries Splunk, LLM analysis of logs
|   |   |-- past_ticket.py       # Queries Jira + ServiceNow, detects open tickets
|   |   |-- runbook.py           # FAISS RAG retrieval + LLM summarisation
|   |   +-- root_cause.py        # Synthesises all evidence incl. open tickets
|   |
|   |-- mcp/
|   |   |-- gateway.py           # Central tool dispatcher (all external calls go here)
|   |   +-- tools/
|   |       |-- splunk_tool.py   # search_logs()
|   |       |-- jira_tool.py     # search_past_incidents()
|   |       |-- servicenow_tool.py # search_servicenow_incidents(), create/get ticket
|   |       +-- slack_tool.py    # post_slack_report()
|   |
|   |-- mocks/
|   |   |-- mock_jira.py         # 13 tickets (8 resolved + 5 open/in-progress)
|   |   |-- mock_splunk.py       # Serves from 100k log file + scenario anchors
|   |   |-- mock_servicenow.py   # 11 pre-populated tickets (incl. open ones) + search
|   |   +-- mock_slack.py        # In-memory message store
|   |
|   |-- rag/
|   |   |-- pipeline.py          # Build FAISS index from runbooks + past incidents
|   |   +-- retriever.py         # Semantic search at runtime
|   |
|   +-- data/
|       +-- logs/
|           +-- application.log  # 100,000 generated log entries (~23 MB, JSON Lines)
|
|-- frontend/
|   +-- src/
|       |-- App.tsx              # 3-panel layout, WS reconnect re-fetch, tab state
|       |-- types/index.ts       # Alert, TriageReport, OpenTicket, AgentSteps types
|       |-- components/
|       |   |-- AlertFeed.tsx    # Left sidebar with Incident Feed / API Endpoints tabs
|       |   |-- AgentFlowPanel.tsx # Always-visible agent flow (vertical layout)
|       |   |-- TriageReport.tsx # Center report: open tickets, hypotheses, remediation
|       |   |-- EndpointsPanel.tsx # Embeddable API endpoint navigator
|       |   +-- IncidentCard.tsx # Single incident card in the feed
|       +-- hooks/
|           +-- useWebSocket.ts  # Auto-reconnecting WebSocket hook
|
|-- scripts/
|   |-- generate_logs.py         # Generate 100k application logs
|   +-- push_alert.py            # Push test alerts to /alert endpoint
|
|-- start.ps1                    # Start all 6 services
|-- stop.ps1                     # Stop all 6 services (handles uvicorn --reload orphans)
|-- requirements.txt
+-- .env.example
```

---

## UI Layout

```
+------------------+------------------+-----------------------------+
|  LEFT SIDEBAR    | CENTER-LEFT      | CENTER-RIGHT                |
|  (320px)         | (288px)          | (flex)                      |
|                  |                  |                             |
| [Incident Feed]  | Agent Flow       | Triage Report               |
| [API Endpoints]  | (always visible) |                             |
|                  |                  | - Active Open Tickets        |
| Tab: Feed        | INGEST           | - Escalation Banner         |
|  - Incident list | -- parallel --   | - Root Cause Hypotheses     |
|  - P1 badge      | LOG ANALYZER     | - Remediation Checklist     |
|  - Live dot      | PAST TICKETS     | - Similar Past Incidents    |
|                  |  [Jira][SN]      |                             |
| Tab: Endpoints   | RUNBOOK RAG      |                             |
|  - All API URLs  | -- merge --      |                             |
|  - Method badges | ROOT CAUSE       |                             |
|  - Clickable GET | REPORT           |                             |
|                  |                  |                             |
|                  | Progress bar     |                             |
+------------------+------------------+-----------------------------+
```

---

## Key Features

### 1. 100k Log File
`scripts/generate_logs.py` produces 100,000 realistic JSON Lines log entries across 7 services with a weighted distribution (DEBUG 8%, INFO 52%, WARN 22%, ERROR 16%, FATAL 2%). The Mock Splunk service loads this file in a background thread on startup and blends it with scenario-specific anchor logs when responding to search queries.

### 2. Dual Ticket Source (Jira + ServiceNow)
`PastTicketAgent` queries both Jira (port 8001) and ServiceNow (port 8003) in parallel. Results are labelled with their source and fed to the LLM for combined ranking.

### 3. Open Ticket Detection
Both mock services contain pre-populated **open and in-progress tickets** for every service. When the past-ticket agent finds a ticket with status `Open` or `In Progress`, it is surfaced as `open_tickets` in the state and flows through to:
- The root cause agent (instructed to reference ticket IDs in its analysis)
- The final report (`open_tickets` field)
- The UI (red "Active Open Tickets" section at the top of the report)

### 4. Real-Time Agent Flow Visualization
`main.py` uses LangGraph `astream` to stream per-node completions as WebSocket `agent_step_update` events. The `AgentFlowPanel` renders a live flow diagram:
- Full-width vertical stacked nodes (no cramped grid layout)
- Parallel nodes shown under a bracket with a left-border group
- Color-coded status: grey=pending, yellow+pulse=running, green=done, red=failed
- Open ticket count badge on the Past Tickets node after completion

### 5. Report Persistence
The backend's in-memory `incidents` store is restored in the frontend on every WebSocket reconnect (the backend sends a `connected` event which triggers a re-fetch of `GET /incidents`). The list endpoint returns full incident objects including the report, so reports survive browser refreshes and backend reloads.

### 6. Triage Timeout
Configurable via `.env`:
```
MAX_TRIAGE_TIMEOUT_SECONDS=600   # 10 minutes (default)
```

---

## Configuration (.env)

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Mock services
MOCK_JIRA_URL=http://localhost:8001
MOCK_SPLUNK_URL=http://localhost:8002
MOCK_SERVICENOW_URL=http://localhost:8003
MOCK_SLACK_URL=http://localhost:8004

# RAG
FAISS_INDEX_PATH=./rag/faiss_index
CHUNK_SIZE=400
CHUNK_OVERLAP=50
TOP_K_RETRIEVAL=5

# Agent behaviour
MAX_TRIAGE_TIMEOUT_SECONDS=600
LOG_WINDOW_MINUTES=30
MAX_SIMILAR_INCIDENTS=5
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI orchestration | LangGraph 1.2 |
| LLM | Azure OpenAI (GPT-4o) |
| Embeddings | Azure OpenAI (text-embedding-3-small) |
| Vector store | FAISS |
| Backend API | FastAPI + Uvicorn |
| Mock services | FastAPI (x4) |
| HTTP client | HTTPX (async) |
| Frontend | React 18 + TypeScript + Vite |
| Styling | Tailwind CSS |
| Real-time | WebSocket |

---

## Triage Report Output

```json
{
  "incident_id": "INC-2CC393",
  "elapsed_seconds": 47.2,
  "alert_summary": "[P1] DB_CONNECTION_TIMEOUT on payment-service in us-east-1",
  "open_tickets": [
    {
      "ticket_id": "SN-PAY003",
      "source": "servicenow",
      "status": "Open",
      "title": "[OPEN] P1 - payment-service DB timeout recurrence post v2.3.1",
      "notes": "Pool temporarily increased. Root cause investigation ongoing.",
      "assigned_team": "Platform Team"
    },
    {
      "ticket_id": "JIRA-4788",
      "source": "jira",
      "status": "Open",
      "title": "[OPEN] Payment service intermittent DB connection timeouts"
    }
  ],
  "root_cause_hypotheses": [
    {
      "rank": 1,
      "hypothesis": "Connection pool exhaustion — v2.3.1 introduced a connection leak",
      "confidence": "High",
      "evidence": [
        "847 CONN_TIMEOUT_5023 errors in 5-minute window",
        "Active connections: 50/50 (pool exhausted)",
        "Open ticket SN-PAY003 confirms recurrence post v2.3.1 deploy",
        "Similar to resolved JIRA-4521 (v2.3.0 leak, fixed by rollback)"
      ],
      "remediation_steps": [
        "Check open ticket SN-PAY003 for current mitigation status",
        "Consider rolling back v2.3.1 to v2.3.0",
        "Increase HikariPool size as temporary mitigation",
        "Run connection leak detection on v2.3.1 diff"
      ]
    }
  ],
  "remediation_checklist": [...],
  "escalation_recommendation": {
    "required": true,
    "priority": "P1",
    "team": "Platform Team",
    "reason": "Active open ticket SN-PAY003 — DB Team already engaged"
  }
}
```
