# Runbook: Notification Service

## Service Overview
The Notification Service is responsible for delivering user notifications via
Email (Sendgrid), SMS (Twilio), and Push (Firebase). It processes messages
from an internal queue (RabbitMQ/Kafka).

## Alert: DEPENDENCY_FAILURE

### Symptoms
- Delivery success rate < 50%
- Error codes DEPENDENCY_503, SMS_TIMEOUT, or DELIVERY_FAILURE
- Message queue depth growing rapidly (> 5000 messages)
- Downstream provider returning 503 or timing out

### Known Failure Modes
1. **Email Provider Outage** — Sendgrid/SES regional incident
2. **SMS Gateway Timeout** — Twilio latency spike or rate limit hit
3. **Queue Backlog** — Slow processing causing message accumulation
4. **Firebase FCM Issues** — Push notification delivery failures

### Diagnostic Steps
1. Check provider status pages:
   - Sendgrid: https://status.sendgrid.com
   - Twilio: https://status.twilio.com
   - Firebase: https://status.firebase.google.com
2. Check queue depth: `rabbitmqctl list_queues name messages consumers`
3. Review error log for specific provider error codes
4. Check delivery retry metrics in service dashboard

### Remediation Steps — Provider Outage
1. **Activate fallback channel**: if email is down, switch to SMS-only mode
   ```bash
   kubectl set env deployment/notification-service EMAIL_ENABLED=false
   ```
2. **Pause non-critical notifications**: set `PRIORITY_FILTER=critical` to drop low-priority messages
3. **Increase retry interval**: avoid hammering degraded provider
   ```bash
   kubectl set env deployment/notification-service RETRY_INTERVAL_SECONDS=60
   ```
4. **Monitor queue depth**: ensure it is not growing unboundedly

### Remediation Steps — Queue Backlog
1. Scale up notification workers: `kubectl scale deployment/notification-service --replicas=10`
2. If queue > 100,000 messages: consider archiving non-critical messages
3. Increase consumer prefetch count for faster drain

### Rollback / Fallback Mode
```bash
# Enable SMS-only fallback mode
kubectl apply -f config/notification-sms-fallback.yaml

# Restore normal mode after provider recovers
kubectl apply -f config/notification-normal.yaml
```

### Escalation
- **Vendor Support**: Open priority ticket with provider if outage > 30 minutes
- **Platform Team**: If queue infrastructure is affected
- **Product Team**: Alert on notification SLA breach for critical user-facing flows
