"""
Mock ServiceNow API — pre-populated past incidents + real-time ticket creation.
Run on port 8003:
    uvicorn backend.mocks.mock_servicenow:app --port 8003 --reload
"""
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI(title="Mock ServiceNow", version="2.0.0")

# Pre-populated incident store (includes past + open tickets)
_tickets: Dict[str, Dict[str, Any]] = {
    "SN-PAY001": {
        "ticket_id": "SN-PAY001",
        "title": "P1 - payment-service DB connection pool exhausted",
        "description": "HikariPool exhausted. CONN_TIMEOUT_5023 errors spiking.",
        "service": "payment-service",
        "alert_type": "DB_CONNECTION_TIMEOUT",
        "error_code": "CONN_TIMEOUT_5023",
        "severity": "P1",
        "status": "Resolved",
        "assigned_team": "Platform Team",
        "created_at": "2025-03-10T09:00:00Z",
        "resolved_at": "2025-03-10T09:35:00Z",
        "resolved_in_minutes": 35,
        "resolution": "Increased connection pool to 100, rolled back v2.2.8 which introduced the leak.",
        "link": "https://mock-servicenow.internal/incident/SN-PAY001",
    },
    "SN-PAY002": {
        "ticket_id": "SN-PAY002",
        "title": "P2 - payment-service latency spike after index drop",
        "description": "Transactions table missing index after migration. p99 latency 12s.",
        "service": "payment-service",
        "alert_type": "LATENCY_SPIKE",
        "error_code": "SLOW_QUERY",
        "severity": "P2",
        "status": "Resolved",
        "assigned_team": "DB Team",
        "created_at": "2025-02-15T14:00:00Z",
        "resolved_at": "2025-02-15T14:20:00Z",
        "resolved_in_minutes": 20,
        "resolution": "Recreated index concurrently. Latency back to normal.",
        "link": "https://mock-servicenow.internal/incident/SN-PAY002",
    },
    "SN-PAY003": {
        "ticket_id": "SN-PAY003",
        "title": "[OPEN] P1 - payment-service DB timeout recurrence post v2.3.1",
        "description": "DB connection timeouts recurring after v2.3.1 deploy. Actively investigating connection leak.",
        "service": "payment-service",
        "alert_type": "DB_CONNECTION_TIMEOUT",
        "error_code": "CONN_TIMEOUT_5023",
        "severity": "P1",
        "status": "Open",
        "assigned_team": "Platform Team",
        "created_at": "2025-05-26T10:05:00Z",
        "resolved_at": None,
        "resolved_in_minutes": None,
        "resolution": None,
        "link": "https://mock-servicenow.internal/incident/SN-PAY003",
        "notes": "Pool temporarily increased. Root cause investigation ongoing. v2.3.1 rollback being considered.",
    },
    "SN-AUTH001": {
        "ticket_id": "SN-AUTH001",
        "title": "P1 - auth-service Redis OOM causing session cache eviction",
        "description": "Redis maxmemory hit, evicting live session keys. All logins hitting primary DB.",
        "service": "auth-service",
        "alert_type": "HIGH_ERROR_RATE",
        "error_code": "CACHE_MISS_HIGH",
        "severity": "P1",
        "status": "Resolved",
        "assigned_team": "Infrastructure Team",
        "created_at": "2025-02-20T16:00:00Z",
        "resolved_at": "2025-02-20T16:45:00Z",
        "resolved_in_minutes": 45,
        "resolution": "Scaled Redis from 4GB to 8GB. Set maxmemory-policy allkeys-lru.",
        "link": "https://mock-servicenow.internal/incident/SN-AUTH001",
    },
    "SN-AUTH002": {
        "ticket_id": "SN-AUTH002",
        "title": "[IN PROGRESS] P1 - auth-service cache miss rate 89% — Redis scaling in progress",
        "description": "Redis memory pressure causing 89% cache miss. DB fallback overwhelming primary.",
        "service": "auth-service",
        "alert_type": "HIGH_ERROR_RATE",
        "error_code": "CACHE_MISS_HIGH",
        "severity": "P1",
        "status": "In Progress",
        "assigned_team": "Infrastructure Team",
        "created_at": "2025-05-27T08:05:00Z",
        "resolved_at": None,
        "resolved_in_minutes": None,
        "resolution": None,
        "link": "https://mock-servicenow.internal/incident/SN-AUTH002",
        "notes": "Redis scaling from 4GB to 8GB initiated. ETA 20 min. Monitoring cache hit rate.",
    },
    "SN-REC001": {
        "ticket_id": "SN-REC001",
        "title": "P1 - recommendation-engine JVM OOM — FeatureCache memory leak",
        "description": "JVM heap at 96%. FeatureCache retaining 2.1GB unreleased objects.",
        "service": "recommendation-engine",
        "alert_type": "MEMORY_LEAK",
        "error_code": "OOM_ERROR",
        "severity": "P1",
        "status": "Resolved",
        "assigned_team": "ML Platform Team",
        "created_at": "2025-01-08T10:00:00Z",
        "resolved_at": "2025-01-08T10:55:00Z",
        "resolved_in_minutes": 55,
        "resolution": "Rolled back to model v4.1. Implemented WeakReference in FeatureCache. Heap stabilised.",
        "link": "https://mock-servicenow.internal/incident/SN-REC001",
    },
    "SN-REC002": {
        "ticket_id": "SN-REC002",
        "title": "[OPEN] P1 - recommendation-engine heap growing — FeatureCache WeakRef fix incomplete",
        "description": "Heap growing at 200MB/hr despite previous fix. Weak reference implementation incomplete.",
        "service": "recommendation-engine",
        "alert_type": "MEMORY_LEAK",
        "error_code": "OOM_ERROR",
        "severity": "P1",
        "status": "Open",
        "assigned_team": "ML Platform Team",
        "created_at": "2025-05-25T14:10:00Z",
        "resolved_at": None,
        "resolved_in_minutes": None,
        "resolution": None,
        "link": "https://mock-servicenow.internal/incident/SN-REC002",
        "notes": "Heap dump under analysis. Refactored WeakReference PR in review. Scheduled restart as mitigation.",
    },
    "SN-CHK001": {
        "ticket_id": "SN-CHK001",
        "title": "P1 - checkout-service NPE regression v3.0.5",
        "description": "NullPointerException at CheckoutController:142 after deploy. 18% error rate.",
        "service": "checkout-service",
        "alert_type": "DEPLOY_REGRESSION",
        "error_code": "NPE_CHECKOUT",
        "severity": "P1",
        "status": "Resolved",
        "assigned_team": "Checkout Team",
        "created_at": "2025-04-03T11:00:00Z",
        "resolved_at": "2025-04-03T11:22:00Z",
        "resolved_in_minutes": 22,
        "resolution": "Rolled back to v3.0.4. Hotfix v3.0.6 with null guard deployed next day.",
        "link": "https://mock-servicenow.internal/incident/SN-CHK001",
    },
    "SN-CHK002": {
        "ticket_id": "SN-CHK002",
        "title": "[OPEN] P1 - checkout-service NPE v3.1.0 — hotfix in review",
        "description": "Same NPE pattern after v3.1.0 deploy. Hotfix PR #892 in code review.",
        "service": "checkout-service",
        "alert_type": "DEPLOY_REGRESSION",
        "error_code": "NPE_CHECKOUT",
        "severity": "P1",
        "status": "Open",
        "assigned_team": "Checkout Team",
        "created_at": "2025-05-27T11:10:00Z",
        "resolved_at": None,
        "resolved_in_minutes": None,
        "resolution": None,
        "link": "https://mock-servicenow.internal/incident/SN-CHK002",
        "notes": "PR #892 awaiting approval. Consider rollback to v3.0.9 if approval delayed.",
    },
    "SN-NOT001": {
        "ticket_id": "SN-NOT001",
        "title": "P2 - notification-service email provider outage — Sendgrid",
        "description": "Sendgrid regional outage. Queue depth 42k. SMS fallback active.",
        "service": "notification-service",
        "alert_type": "DEPENDENCY_FAILURE",
        "error_code": "DEPENDENCY_503",
        "severity": "P2",
        "status": "Resolved",
        "assigned_team": "Integrations Team",
        "created_at": "2025-03-20T15:00:00Z",
        "resolved_at": "2025-03-20T19:00:00Z",
        "resolved_in_minutes": 240,
        "resolution": "SMS fallback drained queue over 4hrs. Sendgrid recovered.",
        "link": "https://mock-servicenow.internal/incident/SN-NOT001",
    },
    "SN-NOT002": {
        "ticket_id": "SN-NOT002",
        "title": "[IN PROGRESS] P2 - notification-service email+SMS degraded — queue 42k",
        "description": "Both email and SMS providers degraded. Queue growing. Fallback mode partially active.",
        "service": "notification-service",
        "alert_type": "DEPENDENCY_FAILURE",
        "error_code": "DEPENDENCY_503",
        "severity": "P2",
        "status": "In Progress",
        "assigned_team": "Integrations Team",
        "created_at": "2025-05-27T15:38:00Z",
        "resolved_at": None,
        "resolved_in_minutes": None,
        "resolution": None,
        "link": "https://mock-servicenow.internal/incident/SN-NOT002",
        "notes": "SMS fallback active. Monitoring queue drain. Sendgrid support ticket raised.",
    },
}


class CreateTicketRequest(BaseModel):
    title: str
    description: str
    severity: str
    service: str
    assigned_team: Optional[str] = None


@app.get("/health")
async def health():
    open_count = sum(1 for t in _tickets.values() if t.get("status") in ("Open", "In Progress"))
    return {
        "status": "ok",
        "service": "mock-servicenow",
        "total_tickets": len(_tickets),
        "open_tickets": open_count,
    }


@app.get("/api/incidents/search")
async def search_incidents(
    service: str = Query(...),
    alert_type: Optional[str] = Query(None),
    error_code: Optional[str] = Query(None),
    limit: int = Query(10),
):
    """Search pre-populated ServiceNow incidents by service/alert_type/error_code."""
    results = list(_tickets.values())

    # Filter by service
    results = [t for t in results if service.lower() in t.get("service", "").lower()]

    # Filter by alert_type if provided
    if alert_type:
        type_matches = [t for t in results if alert_type.lower() in t.get("alert_type", "").lower()]
        if type_matches:
            results = type_matches

    # Filter by error_code if provided
    if error_code:
        code_matches = [t for t in results if error_code.lower() in t.get("error_code", "").lower()]
        if code_matches:
            results = code_matches

    # Fallback
    if not results:
        results = list(_tickets.values())[:3]

    return {
        "incidents": results[:limit],
        "total": len(results),
        "open_count": sum(1 for t in results if t.get("status") in ("Open", "In Progress")),
        "source": "servicenow",
    }


@app.get("/api/incidents/{ticket_id}")
async def get_incident(ticket_id: str):
    if ticket_id in _tickets:
        return _tickets[ticket_id]
    raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")


@app.post("/api/incidents", status_code=201)
async def create_incident(req: CreateTicketRequest):
    ticket_id = f"SN-{uuid.uuid4().hex[:6].upper()}"
    ticket = {
        "ticket_id": ticket_id,
        "title": req.title,
        "description": req.description,
        "severity": req.severity,
        "service": req.service,
        "alert_type": "UNKNOWN",
        "error_code": None,
        "assigned_team": req.assigned_team or "On-Call Team",
        "status": "Open",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "resolved_at": None,
        "resolved_in_minutes": None,
        "resolution": None,
        "link": f"https://mock-servicenow.internal/incident/{ticket_id}",
    }
    _tickets[ticket_id] = ticket
    print(f"[MockServiceNow] Created ticket: {ticket_id} -- {req.title}")
    return ticket


@app.get("/api/incidents")
async def list_incidents():
    return {"incidents": list(_tickets.values()), "total": len(_tickets)}
