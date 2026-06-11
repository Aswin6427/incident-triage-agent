# Runbook: Checkout Service

## Service Overview
The Checkout Service manages shopping cart operations, order creation, discount
application, and payment orchestration. It is a critical path service.

## Alert: DEPLOY_REGRESSION

### Symptoms
- Error rate spike immediately following a deployment
- NullPointerException or IllegalStateException in logs
- Error rate increase from baseline to > 5% post-deploy
- Error code REGRESSION_DETECTED or NPE_CHECKOUT

### Known Failure Modes
1. **Null Reference in New Code** — Unguarded null check in new feature code
2. **Config/Feature Flag Missing** — New code expects a config key not yet deployed
3. **DB Schema Mismatch** — Code references column/table not yet added/migrated
4. **Incompatible API Contract** — Breaking change in downstream service API

### Diagnostic Steps
1. Confirm exact deploy time and compare with error rate graph
2. Check diff of deployed version: `git diff v<previous>..v<current>`
3. Look for NPE stack traces in logs — note class name and line number
4. Check feature flags service for any missing flags the new version expects
5. Verify DB migrations ran successfully: `flyway info | grep pending`

### Remediation Steps — Immediate Rollback
```bash
# Check current version
kubectl get deployment checkout-service -o jsonpath='{.spec.template.spec.containers[0].image}'

# Immediate rollback
kubectl rollout undo deployment/checkout-service -n production

# Verify rollback
kubectl rollout status deployment/checkout-service -n production

# Confirm error rate drops
# Watch Datadog dashboard for 2 minutes post-rollback
```

### Post-Rollback Actions
1. Open P1 incident ticket documenting regression
2. Notify engineering team in #deployments Slack channel
3. Prevent re-deploy until root cause fixed and tested
4. Add regression test case covering the broken scenario

### Alert: CPU_SPIKE / Infinite Loop

### Symptoms
- CPU usage > 90% on all pods
- Response times increasing indefinitely
- No OutOfMemoryError (CPU-bound, not memory)

### Diagnostic Steps
1. Get thread dump: `kubectl exec -it <pod> -- kill -3 <pid>`
2. Look for threads in RUNNABLE state in infinite loops
3. Check DiscountEngine logs for cyclical rule application

### Remediation Steps
1. Emergency pod restart: `kubectl rollout restart deployment/checkout-service`
2. Deploy circuit breaker config: limit max discount iterations
3. Review discount rule configuration for circular references
