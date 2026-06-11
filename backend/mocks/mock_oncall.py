"""
Mock On-Call Schedule API — shift-based engineer routing for CVS Health teams.
Run on port 8005:
    uvicorn backend.mocks.mock_oncall:app --port 8005 --reload
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="Mock On-Call Scheduler", version="1.0.0")

# ── Shift windows (UTC hour ranges) ──────────────────────────
# Morning: 06-14, Afternoon: 14-22, Night: 22-06
SHIFTS = {
    "morning":   (6,  14),
    "afternoon": (14, 22),
    "night":     (22, 6),
}

# ── Team on-call roster ───────────────────────────────────────
TEAMS: Dict[str, Dict] = {
    "platform": {
        "description": "Platform & Infrastructure Team",
        "services": ["payment-service", "auth-service", "api-gateway"],
        "shifts": {
            "morning":   {"name": "Alice Chen",     "email": "alice.chen@cvs.com",     "phone": "+1-555-0101", "slack": "@alice.chen"},
            "afternoon": {"name": "Bob Martinez",   "email": "bob.martinez@cvs.com",   "phone": "+1-555-0102", "slack": "@bob.martinez"},
            "night":     {"name": "Carol White",    "email": "carol.white@cvs.com",    "phone": "+1-555-0103", "slack": "@carol.white"},
        },
        "escalation": {"name": "David Kim",       "title": "VP Engineering",   "phone": "+1-555-0100", "email": "david.kim@cvs.com"},
    },
    "ml_platform": {
        "description": "ML Platform & Data Science Team",
        "services": ["recommendation-engine"],
        "shifts": {
            "morning":   {"name": "Eva Patel",      "email": "eva.patel@cvs.com",      "phone": "+1-555-0201", "slack": "@eva.patel"},
            "afternoon": {"name": "Frank Liu",      "email": "frank.liu@cvs.com",      "phone": "+1-555-0202", "slack": "@frank.liu"},
            "night":     {"name": "Grace Okonkwo",  "email": "grace.okonkwo@cvs.com",  "phone": "+1-555-0203", "slack": "@grace.okonkwo"},
        },
        "escalation": {"name": "Henry Zhao",      "title": "Head of ML Engineering", "phone": "+1-555-0200", "email": "henry.zhao@cvs.com"},
    },
    "checkout": {
        "description": "Checkout & Orders Team",
        "services": ["checkout-service"],
        "shifts": {
            "morning":   {"name": "Irene Santos",   "email": "irene.santos@cvs.com",   "phone": "+1-555-0301", "slack": "@irene.santos"},
            "afternoon": {"name": "James Nguyen",   "email": "james.nguyen@cvs.com",   "phone": "+1-555-0302", "slack": "@james.nguyen"},
            "night":     {"name": "Karen Smith",    "email": "karen.smith@cvs.com",    "phone": "+1-555-0303", "slack": "@karen.smith"},
        },
        "escalation": {"name": "Leo Park",        "title": "Director of Engineering", "phone": "+1-555-0300", "email": "leo.park@cvs.com"},
    },
    "integrations": {
        "description": "Integrations & Notifications Team",
        "services": ["notification-service"],
        "shifts": {
            "morning":   {"name": "Maya Rodriguez", "email": "maya.rodriguez@cvs.com", "phone": "+1-555-0401", "slack": "@maya.rodriguez"},
            "afternoon": {"name": "Noah Johnson",   "email": "noah.johnson@cvs.com",   "phone": "+1-555-0402", "slack": "@noah.johnson"},
            "night":     {"name": "Olivia Brown",   "email": "olivia.brown@cvs.com",   "phone": "+1-555-0403", "slack": "@olivia.brown"},
        },
        "escalation": {"name": "Paul Davis",      "title": "Director of Integrations", "phone": "+1-555-0400", "email": "paul.davis@cvs.com"},
    },
    "db": {
        "description": "Database & Storage Team",
        "services": [],
        "shifts": {
            "morning":   {"name": "Quinn Wilson",   "email": "quinn.wilson@cvs.com",   "phone": "+1-555-0501", "slack": "@quinn.wilson"},
            "afternoon": {"name": "Rachel Moore",   "email": "rachel.moore@cvs.com",   "phone": "+1-555-0502", "slack": "@rachel.moore"},
            "night":     {"name": "Sam Taylor",     "email": "sam.taylor@cvs.com",     "phone": "+1-555-0503", "slack": "@sam.taylor"},
        },
        "escalation": {"name": "Tina Hall",       "title": "Head of Data Engineering", "phone": "+1-555-0500", "email": "tina.hall@cvs.com"},
    },
}

SERVICE_TEAM_MAP: Dict[str, str] = {
    "payment-service":       "platform",
    "auth-service":          "platform",
    "api-gateway":           "platform",
    "recommendation-engine": "ml_platform",
    "checkout-service":      "checkout",
    "notification-service":  "integrations",
    "user-service":          "platform",
}

# In-memory page log
_pages: List[Dict[str, Any]] = []


def _get_shift(hour: int) -> str:
    if 6 <= hour < 14:
        return "morning"
    elif 14 <= hour < 22:
        return "afternoon"
    return "night"


def _resolve_team(service_or_team: str) -> Optional[str]:
    """Accept either a team name directly or a service name."""
    if service_or_team in TEAMS:
        return service_or_team
    return SERVICE_TEAM_MAP.get(service_or_team)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-oncall", "teams": list(TEAMS.keys())}


@app.get("/api/oncall/current")
async def get_current_oncall(
    team: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
):
    """Return the current on-call engineer for a team or service."""
    resolved = _resolve_team(team or service or "platform")
    if not resolved or resolved not in TEAMS:
        return {"error": f"Unknown team/service: {team or service}"}

    now = datetime.now(timezone.utc)
    shift = _get_shift(now.hour)
    team_data = TEAMS[resolved]
    engineer = team_data["shifts"][shift]

    return {
        "team": resolved,
        "team_description": team_data["description"],
        "shift": shift,
        "current_time_utc": now.isoformat(),
        "engineer": {**engineer, "team": resolved},
        "escalation_contact": team_data["escalation"],
    }


@app.get("/api/oncall/schedule")
async def get_full_schedule():
    """Return current on-call engineers across all teams."""
    now = datetime.now(timezone.utc)
    shift = _get_shift(now.hour)
    schedule = []
    for team_name, team_data in TEAMS.items():
        engineer = team_data["shifts"][shift]
        schedule.append({
            "team": team_name,
            "description": team_data["description"],
            "services": team_data["services"],
            "shift": shift,
            "engineer": {**engineer, "team": team_name},
        })
    return {"shift": shift, "timestamp_utc": now.isoformat(), "schedule": schedule}


@app.get("/api/oncall/by-service/{service}")
async def get_oncall_by_service(service: str):
    """Resolve on-call engineer for a specific service name."""
    team = SERVICE_TEAM_MAP.get(service, "platform")
    return await get_current_oncall(team=team)


class PageRequest(BaseModel):
    team: str
    service: str
    incident_id: str
    severity: str
    message: str
    paged_by: str = "triage-agent"


@app.post("/api/oncall/page", status_code=201)
async def page_oncall(req: PageRequest):
    """Log a page event and return confirmation."""
    now = datetime.now(timezone.utc)
    shift = _get_shift(now.hour)
    team_name = _resolve_team(req.team) or "platform"
    team_data = TEAMS[team_name]
    engineer = team_data["shifts"][shift]

    page_event = {
        "page_id": f"PAGE-{len(_pages) + 1:04d}",
        "incident_id": req.incident_id,
        "service": req.service,
        "severity": req.severity,
        "team": team_name,
        "engineer_paged": engineer,
        "message": req.message,
        "paged_by": req.paged_by,
        "paged_at": now.isoformat(),
        "status": "delivered",
        "channel": "sms+slack",
    }
    _pages.append(page_event)
    print(f"[MockOnCall] Paged {engineer['name']} ({req.severity}) for {req.incident_id}")
    return page_event


@app.get("/api/oncall/pages")
async def list_pages(incident_id: Optional[str] = Query(None)):
    if incident_id:
        return {"pages": [p for p in _pages if p["incident_id"] == incident_id]}
    return {"pages": _pages, "total": len(_pages)}
