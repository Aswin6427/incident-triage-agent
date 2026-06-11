# Runbook: Payment Service

## Service Overview
The Payment Service handles all checkout, transaction processing, and refund operations.
It connects to a PostgreSQL database using HikariCP connection pooling.

## Alert: DB_CONNECTION_TIMEOUT / CONN_TIMEOUT_5023

### Symptoms
- Repeated `Connection is not available, request timed out` errors in logs
- Error code `CONN_TIMEOUT_5023` or `DB_POOL_EXHAUSTED`
- Checkout and payment endpoints returning 503
- Active connections at 100% of pool maximum

### Known Failure Modes
1. **Connection Pool Exhaustion** — Pool size too small for traffic spike or connection leak after deploy
2. **Database Overload** — Slow queries holding connections longer than normal
3. **Connection Leak** — Code path not closing connections (often introduced in new deploys)
4. **Network Partition** — Intermittent connectivity between app and DB

### Diagnostic Steps
1. Check HikariCP metrics: `GET /actuator/metrics/hikaricp.connections.active`
2. Query DB for active connections: `SELECT count(*) FROM pg_stat_activity WHERE datname='payments';`
3. Check for long-running queries: `SELECT pid, now()-query_start AS duration, query FROM pg_stat_activity WHERE state='active' ORDER BY duration DESC LIMIT 10;`
4. Review recent deployments in CI/CD dashboard for timing correlation
5. Check application logs for connection lifecycle errors (open without close)

### Remediation Steps
1. **Immediate**: Restart the payment-service pods to flush hanging connections
2. **Short-term**: Increase HikariCP pool size — set `spring.datasource.hikari.maximum-pool-size=50`
3. **DB relief**: Kill long-running queries if they are blocking pool acquisition
4. **If deploy-related**: Roll back to previous stable version using `kubectl rollout undo deployment/payment-service`
5. **Monitoring**: Set alert threshold on pool utilisation > 80%

### Rollback Procedure
```bash
kubectl rollout undo deployment/payment-service -n production
kubectl rollout status deployment/payment-service -n production
```

### Escalation
- **DB Team**: If queries show DB performance degradation
- **Platform Team**: If issue persists after pod restart and rollback
- SLA: Resolve P1 within 15 minutes; escalate after 10 minutes of no progress

---

## Alert: LATENCY_SPIKE / SLOW_QUERY

### Symptoms
- p99 latency > 3000ms (normal: < 200ms)
- Slow query log entries in PostgreSQL
- Missing index warnings

### Diagnostic Steps
1. Check PostgreSQL slow query log for queries > 1000ms
2. Run `EXPLAIN ANALYZE` on suspected queries
3. Check for recently added/dropped indexes (`pg_indexes`)
4. Verify DB schema migrations applied correctly

### Remediation Steps
1. Identify slow queries from `pg_stat_statements`
2. Add missing indexes: `CREATE INDEX CONCURRENTLY idx_name ON table(column);`
3. Update table statistics: `ANALYZE transactions;`
4. Consider query rewrite if index cannot help
