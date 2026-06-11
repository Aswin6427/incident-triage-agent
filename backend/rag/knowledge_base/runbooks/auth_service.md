# Runbook: Auth Service

## Service Overview
The Auth Service handles user authentication, JWT token issuance and validation,
and session management backed by Redis cache.

## Alert: HIGH_ERROR_RATE — Auth Failures

### Symptoms
- Error rate > 10% on `/api/login` or `/api/validate-token`
- JWT_SIG_INVALID or CACHE_MISS_HIGH error codes
- Redis cache miss rate > 50%
- Auth latency > 2000ms p99

### Known Failure Modes
1. **Redis Cache Failure** — Redis OOM causing key eviction; all requests hit DB
2. **JWT Secret Rotation** — New secret in vault but old tokens still in circulation
3. **Token Replay Attack** — Mass invalid login attempts overwhelming service
4. **DB Overload** — Auth DB slow due to cache misses routing all requests to DB

### Diagnostic Steps
1. Check Redis memory usage: `redis-cli INFO memory | grep used_memory_human`
2. Check Redis eviction stats: `redis-cli INFO stats | grep evicted_keys`
3. Check JWT secret version in Vault vs application config
4. Review auth error logs for error code distribution
5. Check DB connection pool utilisation for auth database

### Remediation Steps — JWT Issues
1. Verify current JWT secret in Vault: `vault kv get secret/auth-service/jwt`
2. Check application env var `JWT_SECRET_VERSION` matches Vault version
3. If mismatch: deploy config update with correct secret (do NOT restart without updating config)
4. Enable dual-key validation window during rotation (set `JWT_ROTATION_GRACE_MINUTES=30`)

### Remediation Steps — Redis Cache Failure
1. Check Redis memory: if > 95%, increase `maxmemory` config
2. Set eviction policy: `redis-cli CONFIG SET maxmemory-policy allkeys-lru`
3. If Redis cluster is degraded: `redis-cli CLUSTER INFO` → restart unhealthy nodes
4. Monitor cache hit rate recovery after restart

### Remediation Steps — Login Spike / DDoS
1. Enable rate limiting at API gateway: `kubectl apply -f config/rate-limit-strict.yaml`
2. Add source IP to blocklist if attack from specific IPs
3. Scale auth service replicas: `kubectl scale deployment/auth-service --replicas=10`

### Rollback Procedure
```bash
kubectl rollout undo deployment/auth-service -n production
```

### Escalation
- **Security Team**: If pattern suggests credential stuffing attack
- **Platform Team**: If Redis cluster needs node replacement
