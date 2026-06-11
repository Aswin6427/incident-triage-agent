"""
push_alert.py — Simulate an alert being pushed to the triage agent.

Usage:
    python scripts/push_alert.py --scenario db_timeout
    python scripts/push_alert.py --scenario high_error_rate
    python scripts/push_alert.py --scenario memory_leak
    python scripts/push_alert.py --scenario deploy_regression
    python scripts/push_alert.py --scenario dependency_failure
    python scripts/push_alert.py --list
"""
import argparse
import json
import sys
import uuid
from datetime import datetime, timezone

import httpx

BACKEND_URL = "http://localhost:8000"

# ── Pre-built alert scenarios ─────────────────────────────────
SCENARIOS = {
    "db_timeout": {
        "incident_id": f"INC-{uuid.uuid4().hex[:6].upper()}",
        "service": "payment-service",
        "alert_type": "DB_CONNECTION_TIMEOUT",
        "severity": "P1",
        "region": "us-east-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_code": "CONN_TIMEOUT_5023",
        "affected_endpoints": ["/api/checkout", "/api/payment", "/api/refund"],
        "metrics": {
            "error_rate": "23%",
            "latency_p99": "8200ms",
            "throughput_drop": "67%",
        },
        "description": "Database connection pool exhausted. 847 CONN_TIMEOUT errors in last 5 minutes.",
        "source": "datadog",
    },
    "high_error_rate": {
        "incident_id": f"INC-{uuid.uuid4().hex[:6].upper()}",
        "service": "auth-service",
        "alert_type": "HIGH_ERROR_RATE",
        "severity": "P1",
        "region": "eu-west-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_code": "CACHE_MISS_HIGH",
        "affected_endpoints": ["/api/login", "/api/validate-token", "/api/refresh"],
        "metrics": {
            "error_rate": "31%",
            "latency_p99": "4800ms",
            "throughput_drop": "45%",
        },
        "description": "Auth service error rate spiked to 31%. Redis cache miss rate at 92%.",
        "source": "pagerduty",
    },
    "memory_leak": {
        "incident_id": f"INC-{uuid.uuid4().hex[:6].upper()}",
        "service": "recommendation-engine",
        "alert_type": "MEMORY_LEAK",
        "severity": "P1",
        "region": "us-west-2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_code": "OOM_ERROR",
        "affected_endpoints": ["/api/recommendations", "/api/personalised-feed"],
        "metrics": {
            "memory_usage": "94%",
            "latency_p99": "timeout",
            "cpu_usage": "88%",
        },
        "description": "JVM heap at 94%, full GC pause 8200ms. OutOfMemoryError on worker threads.",
        "source": "grafana",
    },
    "deploy_regression": {
        "incident_id": f"INC-{uuid.uuid4().hex[:6].upper()}",
        "service": "checkout-service",
        "alert_type": "DEPLOY_REGRESSION",
        "severity": "P1",
        "region": "us-east-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_code": "NPE_CHECKOUT",
        "affected_endpoints": ["/api/cart/checkout", "/api/orders/create"],
        "metrics": {
            "error_rate": "18%",
            "latency_p99": "350ms",
            "throughput_drop": "21%",
        },
        "description": "Error rate jumped from 0.2% to 18% immediately after deploy of v3.1.0.",
        "source": "datadog",
    },
    "dependency_failure": {
        "incident_id": f"INC-{uuid.uuid4().hex[:6].upper()}",
        "service": "notification-service",
        "alert_type": "DEPENDENCY_FAILURE",
        "severity": "P2",
        "region": "us-east-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_code": "DEPENDENCY_503",
        "affected_endpoints": ["/api/notify/email", "/api/notify/sms"],
        "metrics": {
            "error_rate": "96%",
            "latency_p99": "10000ms",
        },
        "description": "Email provider returning 503. SMS gateway timeout. Queue depth 42,180 messages.",
        "source": "pagerduty",
    },
}


def list_scenarios():
    print("\nAvailable alert scenarios:\n")
    for name, scenario in SCENARIOS.items():
        print(f"  --scenario {name:<20} {scenario['service']} | {scenario['alert_type']} | {scenario['severity']}")
    print()


def push_alert(scenario_name: str):
    if scenario_name not in SCENARIOS:
        print(f"[ERROR] Unknown scenario: '{scenario_name}'")
        list_scenarios()
        sys.exit(1)

    payload = SCENARIOS[scenario_name]
    # Ensure fresh incident ID on each push
    payload["incident_id"] = f"INC-{uuid.uuid4().hex[:6].upper()}"

    print(f"\n[ALERT] Pushing scenario: {scenario_name}")
    print(f"   Service:    {payload['service']}")
    print(f"   Alert Type: {payload['alert_type']}")
    print(f"   Severity:   {payload['severity']}")
    print(f"   Incident:   {payload['incident_id']}")
    print(f"\n   POST {BACKEND_URL}/alert\n")

    try:
        response = httpx.post(f"{BACKEND_URL}/alert", json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        print(f"[OK] Alert accepted!")
        print(f"   Incident ID:  {result['incident_id']}")
        print(f"   Track URL:    {BACKEND_URL}{result['track_url']}")
        print(f"\n   Open the React UI or poll: GET {BACKEND_URL}{result['track_url']}\n")
    except httpx.ConnectError:
        print(f"[ERROR] Could not connect to backend at {BACKEND_URL}")
        print("   Make sure the backend is running: uvicorn backend.main:app --port 8000")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"[ERROR] Backend returned {e.response.status_code}: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push a test alert to the incident triage agent")
    parser.add_argument("--scenario", type=str, help="Alert scenario to push")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--url", type=str, default=BACKEND_URL, help="Backend URL")
    args = parser.parse_args()

    if args.url:
        BACKEND_URL = args.url

    if args.list or not args.scenario:
        list_scenarios()
    else:
        push_alert(args.scenario)
