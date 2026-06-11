"""
Generate 1 lakh (100,000) realistic application log entries.
Output: backend/data/logs/application.log  (JSON Lines format)
Usage:  python scripts/generate_logs.py
"""
import json
import os
import random
from datetime import datetime, timedelta, timezone

SERVICES = [
    "payment-service",
    "auth-service",
    "recommendation-engine",
    "checkout-service",
    "notification-service",
    "api-gateway",
    "user-service",
]

REGIONS = ["us-east-1", "eu-west-1", "us-west-2"]

# Weighted level distribution
_LEVEL_POOL = (
    ["DEBUG"] * 8
    + ["INFO"] * 52
    + ["WARN"] * 22
    + ["ERROR"] * 16
    + ["FATAL"] * 2
)

THREAD_POOL = [
    "pool-1-thread-{n}",
    "http-nio-8080-exec-{n}",
    "worker-{n}",
    "async-task-{n}",
    "scheduler-{n}",
    "db-pool-thread-{n}",
]

# (message_template, error_code_or_None)
MESSAGES: dict = {
    "payment-service": {
        "DEBUG": [
            ("Processing payment request id=req-{rid}", None),
            ("Acquiring DB connection from pool (active={n}/50)", None),
            ("Payment validation started for amount=${amt}", None),
            ("Running fraud check for order ord-{oid}", None),
            ("DB pool stats: active={n}, idle={m}, waiting=0", None),
        ],
        "INFO": [
            ("Payment processed successfully for order ord-{oid} in {ms}ms", None),
            ("DB connection acquired in {ms}ms (pool: {n}/50 active)", None),
            ("Checkout completed for order ord-{oid}", None),
            ("Refund processed for order ord-{oid}", None),
            ("Deploy {ver} health check passed", "DEPLOY_OK"),
            ("POST /api/checkout 200 OK {ms}ms", None),
            ("POST /api/payment 200 OK {ms}ms", None),
            ("GET /api/refund/{oid} 200 OK {ms}ms", None),
        ],
        "WARN": [
            ("DB connection pool at {pct}% capacity ({n}/50 active)", "POOL_WARN"),
            ("Payment retry attempt {rn}/3 for order ord-{oid}", "PAYMENT_RETRY"),
            ("Slow query detected: {ms}ms (threshold: 1000ms)", "SLOW_QUERY"),
            ("High error rate: {pct}% (threshold: 5%)", "ERROR_RATE_WARN"),
            ("Connection pool wait time exceeded: {ms}ms", "POOL_WAIT"),
        ],
        "ERROR": [
            ("Connection to postgres timed out after 30000ms", "CONN_TIMEOUT_5023"),
            ("HikariPool-1 - Connection is not available, request timed out after 30000ms", "CONN_TIMEOUT_5023"),
            ("POST /api/checkout failed: 503 Service Unavailable", "HTTP_503"),
            ("Payment validation failed: card declined for order ord-{oid}", "PAYMENT_DECLINED"),
            ("Transaction rollback: deadlock detected on order ord-{oid}", "DB_DEADLOCK"),
            ("Error rate: {pct}% (threshold: 5%)", "HIGH_ERROR_RATE"),
            ("DB connection refused: max pool size exceeded", "DB_POOL_FULL"),
        ],
        "FATAL": [
            ("Unable to acquire JDBC connection from pool - DB POOL EXHAUSTED", "DB_POOL_EXHAUSTED"),
            ("Service health check FAILED: database unreachable", "HEALTH_FAIL"),
        ],
    },
    "auth-service": {
        "DEBUG": [
            ("JWT token validation started for session sess-{sid}", None),
            ("Redis cache lookup for session sess-{sid}", None),
            ("Auth request received from {ip}", None),
            ("Token expiry check: {sec}s remaining", None),
        ],
        "INFO": [
            ("User u{uid} authenticated successfully from {ip}", "AUTH_OK"),
            ("Token refreshed for session sess-{sid}", "TOKEN_REFRESH"),
            ("Redis cache HIT for session sess-{sid} ({ms}ms)", "CACHE_HIT"),
            ("POST /api/login 200 OK {ms}ms", None),
            ("GET /api/validate-token 200 OK {ms}ms", None),
            ("Redis pool: {n}/100 connections active", None),
        ],
        "WARN": [
            ("Redis cache miss rate: {pct}% (normal: <10%)", "CACHE_MISS_HIGH"),
            ("Auth latency p99: {ms}ms (SLA: 500ms)", "LATENCY_BREACH"),
            ("Multiple failed login attempts from {ip}: {n} in 5 min", "LOGIN_ATTEMPTS"),
            ("Redis eviction count high: {n}/min", "REDIS_EVICT"),
        ],
        "ERROR": [
            ("JWT validation failed: token signature mismatch", "JWT_SIG_INVALID"),
            ("Redis connection failed: connection refused", "REDIS_CONN_FAIL"),
            ("Failed login attempts spike: {n} in last 5 min", "AUTH_SPIKE"),
            ("Token validation timeout after 5000ms", "TOKEN_TIMEOUT"),
            ("Redis cache miss forcing DB fallback for {n} requests", "CACHE_MISS_HIGH"),
        ],
        "FATAL": [
            ("Auth service unable to reach Redis: connection pool exhausted", "REDIS_POOL_EXHAUSTED"),
            ("Critical: all session validations failing - Redis unreachable", "REDIS_DOWN"),
        ],
    },
    "recommendation-engine": {
        "DEBUG": [
            ("Model inference started for user u{uid}", None),
            ("Feature cache lookup for user u{uid}", None),
            ("Loading recommendation batch {n} ({size}MB)", None),
            ("GC stats: heap={pct}% pause={ms}ms", None),
        ],
        "INFO": [
            ("Recommendations generated for user u{uid} in {ms}ms", "REC_OK"),
            ("Model {ver} loaded successfully", "MODEL_LOAD"),
            ("Feature cache warmed for {n} users", "CACHE_WARM"),
            ("GET /api/recommendations 200 OK {ms}ms", None),
            ("Batch inference: {n} users in {ms}ms", None),
        ],
        "WARN": [
            ("JVM heap usage: {pct}% (GC pressure high)", "HEAP_HIGH"),
            ("Full GC pause: {ms}ms", "FULL_GC_PAUSE"),
            ("Model inference slow: {ms}ms (SLA: 500ms)", "INFERENCE_SLOW"),
            ("FeatureCache growing: {size}GB (limit: 4GB)", "CACHE_GROW"),
        ],
        "ERROR": [
            ("OutOfMemoryError: Java heap space", "OOM_ERROR"),
            ("Model inference timeout after 60000ms", "INFERENCE_TIMEOUT"),
            ("Feature cache write failed: out of memory", "CACHE_OOM"),
            ("Worker thread killed: OOM in batch processor", "WORKER_OOM"),
        ],
        "FATAL": [
            ("JVM process terminated: heap exhausted - FeatureCache {size}GB uncollected", "JVM_CRASH"),
            ("OutOfMemoryError: unable to create new native thread", "OOM_THREAD"),
        ],
    },
    "checkout-service": {
        "DEBUG": [
            ("Cart validation started for session sess-{sid}", None),
            ("Promo code lookup for code=PROMO{pcode}", None),
            ("Order creation started for user u{uid}", None),
        ],
        "INFO": [
            ("Order ord-{oid} created successfully in {ms}ms", "ORDER_OK"),
            ("Deploy {ver} completed", "DEPLOY_OK"),
            ("Cart checkout completed in {ms}ms", "CHECKOUT_OK"),
            ("POST /api/cart/checkout 200 OK {ms}ms", None),
        ],
        "WARN": [
            ("Slow cart validation: {ms}ms (threshold: 200ms)", "CART_SLOW"),
            ("Error rate jumped from 0.2% to {pct}% post-deploy", "REGRESSION_DETECTED"),
            ("Rollback candidate: {ver} introduced breaking change", "ROLLBACK_CANDIDATE"),
        ],
        "ERROR": [
            ("NullPointerException at CheckoutController.java:142", "NPE_CHECKOUT"),
            ("Cart validation failed: promo code null reference at line 87", "PROMO_NPE"),
            ("Order creation failed: downstream payment service timeout", "ORDER_FAIL"),
            ("POST /api/cart/checkout failed: 500 Internal Server Error", "HTTP_500"),
        ],
        "FATAL": [
            ("CheckoutService crashed: unhandled NPE in critical path", "CHECKOUT_CRASH"),
        ],
    },
    "notification-service": {
        "DEBUG": [
            ("Email notification queued for user u{uid}", None),
            ("SMS notification queued", None),
            ("Processing notification batch {n}", None),
        ],
        "INFO": [
            ("Email sent in {ms}ms", "EMAIL_OK"),
            ("SMS delivered in {ms}ms", "SMS_OK"),
            ("Batch of {n} notifications processed", "BATCH_OK"),
            ("POST /api/notify/email 200 OK {ms}ms", None),
        ],
        "WARN": [
            ("Email provider latency: {ms}ms (SLA: 2000ms)", "EMAIL_SLOW"),
            ("SMS gateway retry attempt {rn}/3", "SMS_RETRY"),
            ("Message queue depth: {n} (normal: <500)", "QUEUE_BACKLOG"),
            ("Notification delivery rate: {pct}% (SLA: 99%)", "DELIVERY_LOW"),
        ],
        "ERROR": [
            ("Downstream dependency email-provider returned 503", "DEPENDENCY_503"),
            ("SMS gateway timeout after 10000ms", "SMS_TIMEOUT"),
            ("Email provider connection refused", "EMAIL_CONN_FAIL"),
            ("Notification delivery failed: {n} messages dropped", "DELIVERY_FAILURE"),
        ],
        "FATAL": [
            ("Notification service: all downstream providers unreachable", "NO_PROVIDER"),
        ],
    },
    "api-gateway": {
        "DEBUG": [
            ("Route matching for /api/{path}", None),
            ("Rate limit check for client client-{cid}: {n}/1000", None),
        ],
        "INFO": [
            ("Request req-{rid} routed to payment-service in {ms}ms", None),
            ("SSL certificate valid: {days} days remaining", None),
            ("Load balancer health check: all upstreams healthy", None),
            ("GET /api/{path} 200 OK {ms}ms", None),
        ],
        "WARN": [
            ("Rate limit approaching for client client-{cid}: {n}/1000 req/min", "RATE_WARN"),
            ("Upstream payment-service latency: {ms}ms", "UPSTREAM_SLOW"),
            ("Circuit breaker half-open for auth-service", "CIRCUIT_HALF"),
        ],
        "ERROR": [
            ("Circuit breaker OPEN for checkout-service: failure rate {pct}%", "CIRCUIT_OPEN"),
            ("Request timeout: payment-service did not respond in 30000ms", "GATEWAY_TIMEOUT"),
            ("Invalid auth token in request req-{rid}", "AUTH_INVALID"),
        ],
        "FATAL": [
            ("API gateway overloaded: connection pool exhausted", "GW_OVERLOAD"),
        ],
    },
    "user-service": {
        "DEBUG": [
            ("User profile lookup for uid=u{uid}", None),
            ("Permission check for resource orders by uid=u{uid}", None),
            ("Session validation for sid=sess-{sid}", None),
        ],
        "INFO": [
            ("User u{uid} profile updated in {ms}ms", "PROFILE_OK"),
            ("New user registration", "USER_REG"),
            ("Password changed for user u{uid}", "PWD_CHANGE"),
            ("GET /api/users/{uid} 200 OK {ms}ms", None),
        ],
        "WARN": [
            ("Duplicate registration attempt", "DUPE_REG"),
            ("User u{uid} account locked after {n} failed attempts", "ACCT_LOCK"),
        ],
        "ERROR": [
            ("User u{uid} not found in database", "USER_NOT_FOUND"),
            ("Password validation failed for user u{uid}", "PWD_INVALID"),
            ("DB constraint violation: duplicate email", "DB_CONSTRAINT"),
        ],
        "FATAL": [
            ("User service DB connection lost: max retries exceeded", "DB_CONN_LOST"),
        ],
    },
}


def _fmt(template: str, v: dict) -> str:
    try:
        return template.format(**v)
    except (KeyError, ValueError):
        return template


def _make_vals() -> dict:
    return {
        "rid": random.randint(100_000, 999_999),
        "sid": random.randint(10_000, 99_999),
        "uid": random.randint(1_000, 9_999),
        "oid": random.randint(100_000, 999_999),
        "ip": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "ms": random.choice([5, 12, 23, 45, 89, 150, 250, 400, 800, 1200, 2500, 4800, 8200, 30000]),
        "n": random.randint(1, 200),
        "m": random.randint(1, 49),
        "rn": random.randint(1, 3),
        "pct": round(random.uniform(1.0, 95.0), 1),
        "amt": round(random.uniform(10.0, 999.99), 2),
        "size": round(random.uniform(0.1, 3.5), 1),
        "ver": f"v{random.randint(2,4)}.{random.randint(0,9)}.{random.randint(0,9)}",
        "sec": random.randint(60, 3600),
        "days": random.randint(10, 365),
        "cid": random.randint(100, 999),
        "path": random.choice(["checkout", "payment", "users", "auth", "orders"]),
        "pcode": random.randint(100, 999),
    }


def generate_logs(count: int = 100_000, output_path: str = None) -> str:
    if output_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        output_path = os.path.join(project_root, "backend", "data", "logs", "application.log")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    now = datetime.now(timezone.utc)
    print(f"Generating {count:,} log entries -> {output_path}")

    with open(output_path, "w", encoding="utf-8") as fh:
        for i in range(count):
            service = random.choice(SERVICES)
            level = random.choice(_LEVEL_POOL)

            offset = timedelta(seconds=random.randint(0, 7 * 24 * 3600))
            ts = now - offset
            timestamp = ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z"

            msgs = MESSAGES.get(service, {}).get(level, [("log entry", None)])
            template, code = random.choice(msgs)
            vals = _make_vals()
            message = _fmt(template, vals)

            thread_tmpl = random.choice(THREAD_POOL)
            thread = _fmt(thread_tmpl, vals)

            entry: dict = {
                "timestamp": timestamp,
                "level": level,
                "service": service,
                "region": random.choice(REGIONS),
                "message": message,
                "thread": thread,
                "trace_id": f"trace-{random.randint(0, 0xFFFFFFFF):08x}",
            }
            if code:
                entry["code"] = code

            fh.write(json.dumps(entry) + "\n")

            if (i + 1) % 10_000 == 0:
                print(f"  {i + 1:,} / {count:,} written...")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done: {count:,} logs, {size_mb:.1f} MB -> {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate application logs")
    parser.add_argument("--count", type=int, default=100_000, help="Number of log entries")
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    args = parser.parse_args()
    generate_logs(args.count, args.output)
