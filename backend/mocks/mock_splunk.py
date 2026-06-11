"""
Mock Splunk/ELK API — loads the 1-lakh log file and serves filtered results.
Run on port 8002:
    uvicorn backend.mocks.mock_splunk:app --port 8002 --reload
"""
import json
import logging
import os
from typing import Optional, Dict, List, Any

from fastapi import FastAPI, Query

logger = logging.getLogger(__name__)
app = FastAPI(title="Mock Splunk/ELK", version="2.0.0")

# ── Log file path ─────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_LOG_FILE = os.path.join(_HERE, "..", "..", "backend", "data", "logs", "application.log")
_LOG_FILE = os.path.normpath(_LOG_FILE)

# In-memory index: service -> list of log dicts
_index: Dict[str, List[Dict[str, Any]]] = {}


def _load():
    global _index
    if not os.path.exists(_LOG_FILE):
        logger.warning("[MockSplunk] Log file not found: %s  (run scripts/generate_logs.py)", _LOG_FILE)
        return
    count = 0
    with open(_LOG_FILE, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                svc = entry.get("service", "unknown")
                _index.setdefault(svc, []).append(entry)
                count += 1
            except json.JSONDecodeError:
                pass
    logger.info("[MockSplunk] Loaded %d log entries across %d services", count, len(_index))


import threading
threading.Thread(target=_load, daemon=True).start()  # non-blocking background load

# ── Scenario-specific anchor logs (always appended for demo) ──
_SCENARIO: Dict[str, List[Dict]] = {
    "payment-service": [
        {"timestamp": "2025-05-27T14:02:11Z", "level": "ERROR", "service": "payment-service", "message": "Connection to postgres timed out after 30000ms", "code": "CONN_TIMEOUT_5023", "thread": "pool-1-thread-4"},
        {"timestamp": "2025-05-27T14:03:15Z", "level": "ERROR", "service": "payment-service", "message": "HikariPool-1 - Connection is not available, request timed out after 30000ms", "code": "CONN_TIMEOUT_5023", "thread": "pool-1-thread-2"},
        {"timestamp": "2025-05-27T14:04:22Z", "level": "FATAL", "service": "payment-service", "message": "Unable to acquire JDBC connection from pool", "code": "DB_POOL_EXHAUSTED", "thread": "http-nio-8080-exec-7"},
        {"timestamp": "2025-05-27T14:05:01Z", "level": "WARN",  "service": "payment-service", "message": "Active connections: 50/50 (pool exhausted)", "code": "POOL_FULL"},
        {"timestamp": "2025-05-27T14:05:45Z", "level": "ERROR", "service": "payment-service", "message": "POST /api/checkout failed: 503 Service Unavailable", "code": "HTTP_503"},
        {"timestamp": "2025-05-27T14:07:00Z", "level": "ERROR", "service": "payment-service", "message": "Error rate: 23% (threshold: 5%)", "code": "HIGH_ERROR_RATE"},
    ],
    "auth-service": [
        {"timestamp": "2025-05-27T10:12:05Z", "level": "ERROR", "service": "auth-service", "message": "JWT validation failed: token signature mismatch", "code": "JWT_SIG_INVALID"},
        {"timestamp": "2025-05-27T10:12:45Z", "level": "ERROR", "service": "auth-service", "message": "Redis cache miss rate: 92% (normal: <10%)", "code": "CACHE_MISS_HIGH"},
        {"timestamp": "2025-05-27T10:13:00Z", "level": "WARN",  "service": "auth-service", "message": "Auth latency p99: 4800ms (SLA: 500ms)", "code": "LATENCY_BREACH"},
        {"timestamp": "2025-05-27T10:13:30Z", "level": "ERROR", "service": "auth-service", "message": "Failed login attempts spike: 8432 in last 5 min", "code": "AUTH_SPIKE"},
    ],
    "recommendation-engine": [
        {"timestamp": "2025-05-27T08:45:00Z", "level": "WARN",  "service": "recommendation-engine", "message": "JVM heap usage: 94% (GC pressure high)", "code": "HEAP_HIGH"},
        {"timestamp": "2025-05-27T08:45:30Z", "level": "ERROR", "service": "recommendation-engine", "message": "OutOfMemoryError: Java heap space", "code": "OOM_ERROR"},
        {"timestamp": "2025-05-27T08:46:00Z", "level": "WARN",  "service": "recommendation-engine", "message": "Full GC pause: 8200ms", "code": "FULL_GC_PAUSE"},
        {"timestamp": "2025-05-27T08:46:45Z", "level": "ERROR", "service": "recommendation-engine", "message": "Model inference timeout after 60000ms", "code": "INFERENCE_TIMEOUT"},
    ],
    "checkout-service": [
        {"timestamp": "2025-05-27T11:00:01Z", "level": "INFO",  "service": "checkout-service", "message": "Deploy v3.1.0 completed", "code": "DEPLOY_EVENT"},
        {"timestamp": "2025-05-27T11:01:00Z", "level": "ERROR", "service": "checkout-service", "message": "NullPointerException at CheckoutController.java:142", "code": "NPE_CHECKOUT"},
        {"timestamp": "2025-05-27T11:01:30Z", "level": "ERROR", "service": "checkout-service", "message": "Error rate jumped from 0.2% to 18% post-deploy", "code": "REGRESSION_DETECTED"},
        {"timestamp": "2025-05-27T11:02:00Z", "level": "WARN",  "service": "checkout-service", "message": "Rollback candidate detected: v3.1.0 introduced breaking change", "code": "ROLLBACK_CANDIDATE"},
    ],
    "notification-service": [
        {"timestamp": "2025-05-27T15:30:00Z", "level": "ERROR", "service": "notification-service", "message": "Downstream dependency email-provider returned 503", "code": "DEPENDENCY_503"},
        {"timestamp": "2025-05-27T15:30:15Z", "level": "ERROR", "service": "notification-service", "message": "SMS gateway timeout after 10000ms", "code": "SMS_TIMEOUT"},
        {"timestamp": "2025-05-27T15:30:45Z", "level": "WARN",  "service": "notification-service", "message": "Message queue depth: 42180 (normal: <500)", "code": "QUEUE_BACKLOG"},
        {"timestamp": "2025-05-27T15:31:00Z", "level": "ERROR", "service": "notification-service", "message": "Notification delivery rate: 4% (SLA: 99%)", "code": "DELIVERY_FAILURE"},
    ],
}


@app.get("/health")
async def health():
    total = sum(len(v) for v in _index.values())
    return {
        "status": "ok",
        "service": "mock-splunk",
        "indexed_logs": total,
        "services": list(_index.keys()),
    }


@app.get("/api/logs/search")
async def search_logs(
    service: str = Query(...),
    timestamp: Optional[str] = Query(None),
    window_minutes: int = Query(30),
    limit: int = Query(200),
):
    """Return log entries for the given service from the log file + scenario anchors."""
    file_logs = _index.get(service, [])

    # Split file logs by severity
    errors = [l for l in file_logs if l.get("level") in ("ERROR", "FATAL")]
    warns  = [l for l in file_logs if l.get("level") == "WARN"]
    infos  = [l for l in file_logs if l.get("level") in ("INFO", "DEBUG")]

    # Blend: scenario anchors + top errors + sample of warns/infos
    scenario = _SCENARIO.get(service, [])
    combined = scenario + errors[:60] + warns[:30] + infos[:20]

    # Sort by timestamp desc
    combined.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return {
        "service": service,
        "window_minutes": window_minutes,
        "total_events": len(combined),
        "file_log_total": len(file_logs),
        "logs": combined[:limit],
    }


@app.get("/api/logs/stats")
async def log_stats():
    return {
        "total_indexed": sum(len(v) for v in _index.values()),
        "by_service": {svc: len(logs) for svc, logs in _index.items()},
    }


@app.get("/api/logs/trends")
async def get_log_trends(
    service: str = Query(...),
    window_minutes: int = Query(30),
):
    """Return error-rate trend data for predictive anomaly detection."""
    import random

    BASE_RATES = {
        "payment-service":       1.2,
        "auth-service":          0.8,
        "recommendation-engine": 2.1,
        "checkout-service":      0.5,
        "notification-service":  3.0,
    }
    TOP_ERRORS = {
        "payment-service":       ["CONN_TIMEOUT_5023", "HIGH_ERROR_RATE", "DB_POOL_FULL"],
        "auth-service":          ["CACHE_MISS_HIGH", "JWT_SIG_INVALID", "TOKEN_TIMEOUT"],
        "recommendation-engine": ["OOM_ERROR", "HEAP_HIGH", "INFERENCE_TIMEOUT"],
        "checkout-service":      ["NPE_CHECKOUT", "REGRESSION_DETECTED", "HTTP_500"],
        "notification-service":  ["DEPENDENCY_503", "SMS_TIMEOUT", "QUEUE_BACKLOG"],
    }

    base   = BASE_RATES.get(service, 1.5)
    # Introduce a realistic uptick to make some predictions fire
    spike  = random.choice([0, 0, 0, random.uniform(2.0, 6.0)])
    current = max(0.1, base + spike + random.uniform(-0.3, 0.5))
    roc     = round(random.uniform(-0.05, 0.45), 3)
    anomaly = min(0.95, max(0.0, (current - base) / max(base, 1) * 0.5 + random.uniform(0, 0.25)))

    if anomaly > 0.55 or roc > 0.25:
        trend_label = "increasing"
        eta = max(5, int(25 - anomaly * 20))
    elif anomaly > 0.3:
        trend_label = "stable-elevated"
        eta = 45
    else:
        trend_label = "stable"
        eta = 120

    data_points = [round(base + i * roc + random.uniform(-0.2, 0.2), 2) for i in range(10)]

    return {
        "service": service,
        "window_minutes": window_minutes,
        "current_error_rate_pct": round(current, 2),
        "baseline_error_rate_pct": base,
        "trend": trend_label,
        "rate_of_change_per_min": roc,
        "anomaly_score": round(anomaly, 3),
        "predicted_threshold_breach_minutes": eta,
        "top_error_codes": TOP_ERRORS.get(service, ["UNKNOWN"])[:3],
        "data_points": data_points,
    }
