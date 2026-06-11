"""
Mock Jira API — past incident tickets including open/in-progress ones.
Run on port 8001:
    uvicorn backend.mocks.mock_jira:app --port 8001 --reload
"""
from fastapi import FastAPI, Query
from typing import Optional, List, Dict, Any

app = FastAPI(title="Mock Jira", version="2.0.0")

# status: Resolved | Open | In Progress | Closed
PAST_INCIDENTS: List[Dict[str, Any]] = [
    {
        "ticket_id": "JIRA-4521",
        "title": "Payment service DB timeouts — connection pool exhausted",
        "service": "payment-service",
        "alert_type": "DB_CONNECTION_TIMEOUT",
        "error_code": "CONN_TIMEOUT_5023",
        "root_cause": "Connection pool limit (10) hit after deploy v2.3.0 introduced a connection leak in PaymentRepository",
        "resolution": "Rolled back to v2.2.9, increased pool size from 10 to 50, added connection leak detection",
        "resolved_in_minutes": 23,
        "created_at": "2025-03-15T09:12:00Z",
        "severity": "P1",
        "status": "Resolved",
        "assignee": "alice@company.com",
    },
    {
        "ticket_id": "JIRA-4389",
        "title": "Auth service Redis cache failure causing login latency",
        "service": "auth-service",
        "alert_type": "HIGH_ERROR_RATE",
        "error_code": "CACHE_MISS_HIGH",
        "root_cause": "Redis instance ran out of memory, evicting session keys, forcing all auth requests to hit DB",
        "resolution": "Increased Redis maxmemory, set eviction policy to allkeys-lru, restarted Redis cluster",
        "resolved_in_minutes": 35,
        "created_at": "2025-02-28T14:22:00Z",
        "severity": "P2",
        "status": "Resolved",
        "assignee": "bob@company.com",
    },
    {
        "ticket_id": "JIRA-4102",
        "title": "Recommendation engine OOM — heap exhaustion after model update",
        "service": "recommendation-engine",
        "alert_type": "MEMORY_LEAK",
        "error_code": "OOM_ERROR",
        "root_cause": "New ML model v4.2 loaded feature cache eagerly, retaining 2.1GB per worker. GC unable to collect.",
        "resolution": "Rolled back model to v4.1, implemented lazy loading, increased JVM heap from 4GB to 8GB",
        "resolved_in_minutes": 45,
        "created_at": "2025-01-10T08:30:00Z",
        "severity": "P1",
        "status": "Resolved",
        "assignee": "carol@company.com",
    },
    {
        "ticket_id": "JIRA-4601",
        "title": "Checkout service regression after deploy v3.0.5",
        "service": "checkout-service",
        "alert_type": "DEPLOY_REGRESSION",
        "error_code": "NPE_CHECKOUT",
        "root_cause": "NullPointerException in v3.0.5 — PromoCodeValidator not null-checked when promo is absent",
        "resolution": "Immediate rollback to v3.0.4, hotfix deployed in v3.0.6 with null guard",
        "resolved_in_minutes": 18,
        "created_at": "2025-04-05T11:15:00Z",
        "severity": "P1",
        "status": "Resolved",
        "assignee": "dave@company.com",
    },
    {
        "ticket_id": "JIRA-4450",
        "title": "Notification service failure — email provider outage",
        "service": "notification-service",
        "alert_type": "DEPENDENCY_FAILURE",
        "error_code": "DEPENDENCY_503",
        "root_cause": "Third-party email provider (Sendgrid) regional outage, cascading queue backup",
        "resolution": "Activated fallback SMS-only mode, drained queue over 4 hours as provider recovered",
        "resolved_in_minutes": 240,
        "created_at": "2025-03-22T15:45:00Z",
        "severity": "P2",
        "status": "Resolved",
        "assignee": "eve@company.com",
    },
    {
        "ticket_id": "JIRA-4210",
        "title": "Payment service slow queries after schema migration",
        "service": "payment-service",
        "alert_type": "LATENCY_SPIKE",
        "error_code": "SLOW_QUERY",
        "root_cause": "Missing index on transactions.created_at after DB migration, causing full table scans",
        "resolution": "Added index CREATE INDEX CONCURRENTLY on transactions(created_at, service_id)",
        "resolved_in_minutes": 12,
        "created_at": "2025-02-10T16:00:00Z",
        "severity": "P2",
        "status": "Resolved",
        "assignee": "alice@company.com",
    },
    {
        "ticket_id": "JIRA-3980",
        "title": "Auth service JWT secret rotation broke token validation",
        "service": "auth-service",
        "alert_type": "HIGH_ERROR_RATE",
        "error_code": "JWT_SIG_INVALID",
        "root_cause": "JWT secret rotated in vault but old tokens still in circulation; validation fails for ~30 min",
        "resolution": "Added dual-key validation window (old + new secret), extended token expiry grace period",
        "resolved_in_minutes": 28,
        "created_at": "2024-12-18T09:00:00Z",
        "severity": "P1",
        "status": "Resolved",
        "assignee": "bob@company.com",
    },
    {
        "ticket_id": "JIRA-4055",
        "title": "Checkout service CPU spike — infinite loop in discount calculation",
        "service": "checkout-service",
        "alert_type": "CPU_SPIKE",
        "error_code": "CPU_100",
        "root_cause": "Circular discount rule reference caused infinite loop in DiscountEngine",
        "resolution": "Emergency patch with cycle detection, rule engine refactored",
        "resolved_in_minutes": 32,
        "created_at": "2025-01-20T14:00:00Z",
        "severity": "P1",
        "status": "Resolved",
        "assignee": "carol@company.com",
    },
    # ── OPEN TICKETS (actively being worked) ──────────────────
    {
        "ticket_id": "JIRA-4788",
        "title": "[OPEN] Payment service intermittent DB connection timeouts — recurrence investigation",
        "service": "payment-service",
        "alert_type": "DB_CONNECTION_TIMEOUT",
        "error_code": "CONN_TIMEOUT_5023",
        "root_cause": "Root cause under investigation — suspected connection leak in v2.3.1",
        "resolution": None,
        "resolved_in_minutes": None,
        "created_at": "2025-05-26T10:00:00Z",
        "severity": "P1",
        "status": "Open",
        "assignee": "alice@company.com",
        "description": "Payment service is experiencing DB connection timeouts again after deploy of v2.3.1. Pool exhaustion observed. Ticket open for ongoing investigation.",
        "comments": [
            {"author": "alice", "time": "2025-05-26T10:30:00Z", "text": "Pool size increased to 100 as temporary mitigation. Root cause still unknown."},
            {"author": "db-team", "time": "2025-05-26T12:00:00Z", "text": "Reviewing slow query logs. Suspected missing index on payments_v2 table."},
        ],
    },
    {
        "ticket_id": "JIRA-4791",
        "title": "[IN PROGRESS] Auth service cache miss spike — Redis memory pressure",
        "service": "auth-service",
        "alert_type": "HIGH_ERROR_RATE",
        "error_code": "CACHE_MISS_HIGH",
        "root_cause": "Redis maxmemory too low for current session volume; evictions causing cascading DB load",
        "resolution": None,
        "resolved_in_minutes": None,
        "created_at": "2025-05-27T08:00:00Z",
        "severity": "P1",
        "status": "In Progress",
        "assignee": "bob@company.com",
        "description": "Auth service Redis cache miss rate spiked to 89%. Current session volume exceeds Redis memory limit.",
        "comments": [
            {"author": "bob", "time": "2025-05-27T08:30:00Z", "text": "Scaling Redis from 4GB to 8GB. ETA 20 min."},
        ],
    },
    {
        "ticket_id": "JIRA-4793",
        "title": "[OPEN] Recommendation engine memory leak — FeatureCache not releasing objects",
        "service": "recommendation-engine",
        "alert_type": "MEMORY_LEAK",
        "error_code": "OOM_ERROR",
        "root_cause": "FeatureCache holding strong references to user model objects across GC cycles",
        "resolution": None,
        "resolved_in_minutes": None,
        "created_at": "2025-05-25T14:00:00Z",
        "severity": "P1",
        "status": "Open",
        "assignee": "carol@company.com",
        "description": "JVM heap growing steadily. FeatureCache identified as primary culprit. Fix being developed.",
        "comments": [
            {"author": "carol", "time": "2025-05-25T15:00:00Z", "text": "Heap dump taken. FeatureCache retaining 2.4GB. Working on weak-reference refactor."},
        ],
    },
    {
        "ticket_id": "JIRA-4795",
        "title": "[OPEN] Checkout service NPE after v3.1.0 deploy — recurring on new promo codes",
        "service": "checkout-service",
        "alert_type": "DEPLOY_REGRESSION",
        "error_code": "NPE_CHECKOUT",
        "root_cause": "CheckoutController.java:142 NPE when promo_code field is absent from cart payload",
        "resolution": None,
        "resolved_in_minutes": None,
        "created_at": "2025-05-27T11:05:00Z",
        "severity": "P1",
        "status": "Open",
        "assignee": "dave@company.com",
        "description": "Post-deploy v3.1.0 NPE observed at high rate. 18% error rate on /api/cart/checkout. Hotfix in review.",
        "comments": [
            {"author": "dave", "time": "2025-05-27T11:15:00Z", "text": "Hotfix PR #892 raised. Awaiting code review before deploy."},
        ],
    },
    {
        "ticket_id": "JIRA-4797",
        "title": "[IN PROGRESS] Notification service email provider 503 — queue backlog growing",
        "service": "notification-service",
        "alert_type": "DEPENDENCY_FAILURE",
        "error_code": "DEPENDENCY_503",
        "root_cause": "Email provider Sendgrid returning 503 since 15:28 UTC. SMS gateway also degraded.",
        "resolution": None,
        "resolved_in_minutes": None,
        "created_at": "2025-05-27T15:35:00Z",
        "severity": "P2",
        "status": "In Progress",
        "assignee": "eve@company.com",
        "description": "Active incident: email provider down, queue at 42k messages. Activating fallback mode.",
        "comments": [
            {"author": "eve", "time": "2025-05-27T15:40:00Z", "text": "SMS-only fallback activated. Working with Sendgrid support."},
        ],
    },
]


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-jira", "total_tickets": len(PAST_INCIDENTS)}


@app.get("/api/incidents/search")
async def search_incidents(
    service: str = Query(...),
    alert_type: Optional[str] = Query(None),
    error_code: Optional[str] = Query(None),
    limit: int = Query(10),
    include_open: bool = Query(True),
):
    """Return past incidents matching the query. Open tickets are always included."""
    results = PAST_INCIDENTS

    # Filter by service
    results = [i for i in results if service.lower() in i["service"].lower()]

    # Filter by alert type if provided
    if alert_type:
        type_matches = [i for i in results if alert_type.lower() in i.get("alert_type", "").lower()]
        if type_matches:
            results = type_matches

    # Filter by error code if provided
    if error_code:
        code_matches = [i for i in results if error_code.lower() in i.get("error_code", "").lower()]
        if code_matches:
            results = code_matches

    # Fallback: return all if no service matches
    if not results:
        results = PAST_INCIDENTS[:5]

    return {
        "incidents": results[:limit],
        "total": len(results),
        "open_count": sum(1 for i in results if i.get("status") in ("Open", "In Progress")),
        "source": "jira",
    }


@app.get("/api/incidents/{ticket_id}")
async def get_incident(ticket_id: str):
    for incident in PAST_INCIDENTS:
        if incident["ticket_id"] == ticket_id:
            return incident
    return {"error": f"Ticket {ticket_id} not found"}
