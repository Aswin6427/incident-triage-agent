"""
Incident Triage & Root Cause AI Agent -- Main FastAPI Application

Endpoints:
  POST /alert                     -- Ingest alert, start triage
  GET  /incidents                 -- List all incidents (full state)
  GET  /incidents/{id}            -- Status + report for a specific incident
  POST /incidents/{id}/resolve    -- Resolve incident + generate post-mortem
  GET  /predictions               -- Current predictive alerts
  GET  /post-mortems              -- All generated post-mortems
  WS   /ws                        -- WebSocket for live updates
"""
import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import get_settings
from backend.models.alert import AlertPayload
from backend.orchestrator.graph import build_triage_graph
from backend.agents.predictive_monitor import PredictiveMonitorAgent
from backend.agents.post_mortem import PostMortemAgent
from backend.mcp.gateway import MCPGateway

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

incidents:    Dict[str, Dict[str, Any]] = {}
predictions:  Dict[str, Dict[str, Any]] = {}
post_mortems: Dict[str, Dict[str, Any]] = {}

_NODE_META = {
    "ingest_node":        ("Alert ingested",                         10),
    "log_analyzer_node":  ("Analyzing Splunk logs",                  35),
    "past_ticket_node":   ("Searching Jira + ServiceNow tickets",    40),
    "runbook_node":       ("Retrieving runbook context",             35),
    "root_cause_node":    ("Synthesizing root cause",                80),
    "report_node":        ("Generating report + paging on-call",     95),
}
_PARALLEL_NODES = {"log_analyzer_node", "past_ticket_node", "runbook_node"}


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: Dict[str, Any]):
        text = json.dumps(message, default=str)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)


manager = ConnectionManager()


# ── Predictive Monitor ────────────────────────────────────────

async def run_predictive_monitor():
    """Background task: polls Splunk trends every N seconds and fires predictions."""
    interval = settings.predictive_monitor_interval_seconds
    logger.info("[PredictiveMonitor] Starting -- interval=%ds", interval)
    await asyncio.sleep(15)  # give mocks time to start
    while True:
        try:
            agent = PredictiveMonitorAgent(mcp_gateway=MCPGateway())
            found = await agent.run()
            for pred in found:
                pred_id = f"PRED-{uuid.uuid4().hex[:6].upper()}"
                pred["prediction_id"] = pred_id
                pred["detected_at"]   = time.time()
                predictions[pred_id]  = pred
                await manager.broadcast({
                    "event":        "prediction",
                    "prediction_id": pred_id,
                    **pred,
                })
                logger.info("[PredictiveMonitor] Prediction fired: %s (%s)", pred_id, pred["service"])
        except Exception as exc:
            logger.error("[PredictiveMonitor] Cycle failed: %s", exc)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(run_predictive_monitor())
    logger.info("Incident Triage Agent v2 starting up...")
    yield
    task.cancel()
    logger.info("Incident Triage Agent shutting down...")


app = FastAPI(
    title="Incident Triage & Root Cause AI Agent",
    description="AI-powered incident triage with LangGraph + Azure OpenAI",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

triage_graph = build_triage_graph()


async def _update_incident(incident_id: str, update: Dict[str, Any]):
    if incident_id in incidents:
        incidents[incident_id].update(update)
    await manager.broadcast({"event": "incident_update", "incident_id": incident_id, **update})


async def run_triage(incident_id: str, alert: AlertPayload):
    started_at = time.time()
    alert_dict = alert.model_dump(mode="json")

    initial_state = {
        "incident_id":          incident_id,
        "alert_payload":        alert_dict,
        "started_at":           started_at,
        "log_findings":         None,
        "past_incidents":       None,
        "open_tickets":         None,
        "runbook_context":      None,
        "root_cause_hypotheses": None,
        "remediation_checklist": None,
        "escalation":           None,
        "oncall_info":          None,
        "paged":                False,
        "log_analyzer_status":  "pending",
        "past_ticket_status":   "pending",
        "runbook_status":       "pending",
        "root_cause_status":    "pending",
        "triage_report":        None,
        "slack_posted":         False,
        "current_step":         "ingested",
        "error":                None,
        "elapsed_seconds":      None,
    }

    await _update_incident(incident_id, {
        "status":       "analyzing",
        "progress_pct": 10,
        "current_step": "Querying logs, tickets (Jira+ServiceNow) and runbooks in parallel...",
        "agent_steps": {
            "ingest_node":       {"status": "completed", "label": "Alert ingested"},
            "log_analyzer_node": {"status": "running",   "label": "Analyzing Splunk logs"},
            "past_ticket_node":  {"status": "running",   "label": "Searching Jira + ServiceNow"},
            "runbook_node":      {"status": "running",   "label": "Retrieving runbook context"},
            "root_cause_node":   {"status": "pending",   "label": "Synthesizing root cause"},
            "report_node":       {"status": "pending",   "label": "Generating report"},
        },
    })

    try:
        final_state: Dict[str, Any] = {}
        completed_parallel: set = set()

        async def _stream():
            async for chunk in triage_graph.astream(initial_state):
                for node_name, node_output in chunk.items():
                    if isinstance(node_output, dict):
                        final_state.update(node_output)

                    label, progress = _NODE_META.get(node_name, (node_name, 50))
                    step_update: Dict[str, Any] = {"status": "completed", "label": label}

                    if node_name == "past_ticket_node" and isinstance(node_output, dict):
                        open_count = len(node_output.get("open_tickets", []))
                        step_update["open_tickets_count"] = open_count

                    next_steps: Dict[str, Any] = {}
                    if node_name in _PARALLEL_NODES:
                        completed_parallel.add(node_name)
                        if _PARALLEL_NODES.issubset(completed_parallel):
                            next_steps["root_cause_node"] = {"status": "running", "label": "Synthesizing root cause"}

                    if node_name == "root_cause_node":
                        next_steps["report_node"] = {"status": "running", "label": "Generating report + paging on-call"}

                    merged = {node_name: step_update, **next_steps}
                    await _update_incident(incident_id, {
                        "status":            "analyzing" if node_name != "report_node" else "reporting",
                        "progress_pct":      progress,
                        "current_step":      label,
                        "agent_step_update": merged,
                    })

        await asyncio.wait_for(_stream(), timeout=settings.max_triage_timeout_seconds)

        elapsed    = time.time() - started_at
        report     = final_state.get("triage_report", {})
        open_count = len(final_state.get("open_tickets") or [])
        paged      = final_state.get("paged", False)
        oncall     = final_state.get("oncall_info", {})
        engineer   = oncall.get("engineer", {}) if oncall else {}

        await _update_incident(incident_id, {
            "status":       "done",
            "progress_pct": 100,
            "current_step": f"Triage complete ({open_count} open ticket(s) | oncall: {engineer.get('name', 'N/A')})",
            "report":       report,
            "paged":        paged,
            "oncall_info":  oncall,
            "elapsed_seconds": round(elapsed, 1),
            "agent_steps": {
                "ingest_node":       {"status": "completed", "label": "Alert ingested"},
                "log_analyzer_node": {"status": "completed", "label": "Logs analyzed"},
                "past_ticket_node":  {"status": "completed", "label": f"Tickets searched ({open_count} open)", "open_tickets_count": open_count},
                "runbook_node":      {"status": "completed", "label": "Runbook retrieved"},
                "root_cause_node":   {"status": "completed", "label": "Root cause synthesized"},
                "report_node":       {"status": "completed", "label": f"Report generated{' + paged' if paged else ''}"},
            },
        })
        logger.info("Triage complete for %s in %.1fs", incident_id, elapsed)

    except asyncio.TimeoutError:
        await _update_incident(incident_id, {
            "status": "failed",
            "error":  f"Triage exceeded {settings.max_triage_timeout_seconds // 60} min SLA",
            "progress_pct": 0,
        })
    except Exception as exc:
        logger.error("Triage failed for %s: %s", incident_id, exc, exc_info=True)
        await _update_incident(incident_id, {"status": "failed", "error": str(exc), "progress_pct": 0})


# ── Post-Mortem generation ────────────────────────────────────

class ResolveRequest(BaseModel):
    resolution_summary:    str
    confirmed_root_cause:  str
    resolved_by:           str = "On-Call Engineer"


async def generate_post_mortem(incident_id: str, req: ResolveRequest):
    await manager.broadcast({
        "event":       "incident_update",
        "incident_id": incident_id,
        "status":      "generating_post_mortem",
        "current_step": "Generating post-mortem and updating knowledge base...",
    })
    try:
        report = incidents.get(incident_id, {}).get("report", {})
        agent  = PostMortemAgent()
        pm = await agent.run(
            incident_id=incident_id,
            triage_report=report,
            resolution_summary=req.resolution_summary,
            confirmed_root_cause=req.confirmed_root_cause,
            resolved_by=req.resolved_by,
        )
        post_mortems[incident_id] = pm
        if incident_id in incidents:
            incidents[incident_id]["post_mortem"] = pm
            incidents[incident_id]["status"]      = "resolved"

        await manager.broadcast({
            "event":          "post_mortem_complete",
            "incident_id":    incident_id,
            "post_mortem":    pm,
        })
        logger.info("[PostMortem] Generated for %s", incident_id)
    except Exception as exc:
        logger.error("[PostMortem] Failed for %s: %s", incident_id, exc)
        await manager.broadcast({
            "event":       "incident_update",
            "incident_id": incident_id,
            "error":       f"Post-mortem generation failed: {exc}",
        })


# ── API Routes ────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status":  "healthy",
        "service": "incident-triage-agent",
        "version": "2.0.0",
        "active_incidents":  len(incidents),
        "active_predictions": len(predictions),
        "post_mortems": len(post_mortems),
    }


@app.post("/alert", status_code=202)
async def ingest_alert(alert: AlertPayload, background_tasks: BackgroundTasks):
    incident_id = alert.incident_id or f"INC-{uuid.uuid4().hex[:8].upper()}"
    alert.incident_id = incident_id
    logger.info("Alert received: %s | %s | %s", incident_id, alert.service, alert.alert_type)

    incidents[incident_id] = {
        "incident_id":  incident_id,
        "status":       "ingested",
        "progress_pct": 5,
        "current_step": "Alert ingested",
        "alert":        alert.model_dump(mode="json"),
        "report":       None,
        "post_mortem":  None,
        "paged":        False,
        "oncall_info":  None,
        "error":        None,
        "received_at":  time.time(),
        "agent_steps": {
            "ingest_node":       {"status": "running",  "label": "Ingesting alert"},
            "log_analyzer_node": {"status": "pending",  "label": "Analyzing Splunk logs"},
            "past_ticket_node":  {"status": "pending",  "label": "Searching Jira + ServiceNow"},
            "runbook_node":      {"status": "pending",  "label": "Retrieving runbook context"},
            "root_cause_node":   {"status": "pending",  "label": "Synthesizing root cause"},
            "report_node":       {"status": "pending",  "label": "Generating report"},
        },
    }

    await manager.broadcast({
        "event":       "new_alert",
        "incident_id": incident_id,
        "alert":       alert.model_dump(mode="json"),
        "status":      "ingested",
        "agent_steps": incidents[incident_id]["agent_steps"],
    })

    background_tasks.add_task(run_triage, incident_id, alert)
    return {"incident_id": incident_id, "message": "Alert ingested. Triage started.", "track_url": f"/incidents/{incident_id}"}


@app.get("/incidents", response_model=list)
async def list_incidents():
    return list(incidents.values())


@app.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return incidents[incident_id]


@app.post("/incidents/{incident_id}/resolve", status_code=202)
async def resolve_incident(incident_id: str, req: ResolveRequest, background_tasks: BackgroundTasks):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    if incidents[incident_id]["status"] not in ("done", "failed"):
        raise HTTPException(status_code=400, detail="Incident must be in done/failed state to resolve")

    incidents[incident_id]["status"]       = "resolving"
    incidents[incident_id]["current_step"] = "Generating post-mortem..."
    background_tasks.add_task(generate_post_mortem, incident_id, req)
    return {"incident_id": incident_id, "message": "Post-mortem generation started."}


@app.get("/predictions")
async def list_predictions():
    return {"predictions": list(predictions.values()), "total": len(predictions)}


@app.get("/post-mortems")
async def list_post_mortems():
    return {"post_mortems": list(post_mortems.values()), "total": len(post_mortems)}


@app.get("/post-mortems/{incident_id}")
async def get_post_mortem(incident_id: str):
    if incident_id not in post_mortems:
        raise HTTPException(status_code=404, detail=f"No post-mortem for {incident_id}")
    return post_mortems[incident_id]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_text(json.dumps({
            "event":            "connected",
            "active_incidents": list(incidents.keys()),
        }, default=str))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.backend_host, port=settings.backend_port, reload=True)
