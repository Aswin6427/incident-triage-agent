# Runbook: Recommendation Engine

## Service Overview
The Recommendation Engine is a JVM-based service that serves personalised product
recommendations using ML models loaded into memory. It is memory-intensive by design.

## Alert: MEMORY_LEAK / OOM_ERROR

### Symptoms
- JVM heap usage > 90%
- Full GC pause duration > 5000ms
- OutOfMemoryError in logs
- Model inference timeouts
- Error code OOM_ERROR or MEMORY_LEAK_DETECTED

### Known Failure Modes
1. **Model Cache Leak** — New ML model version retaining objects in FeatureCache
2. **Eager Loading** — Model loaded all features at startup instead of lazily
3. **Insufficient Heap** — Traffic increase exceeded original heap sizing
4. **Native Memory Leak** — Off-heap memory in model serialisation layer

### Diagnostic Steps
1. Check heap usage: `kubectl exec -it <pod> -- jcmd 1 VM.native_memory`
2. Check GC logs: `kubectl logs <pod> | grep "GC pause"`
3. Identify large objects: `kubectl exec -it <pod> -- jcmd 1 GC.heap_info`
4. Check model version recently deployed: compare with `git log --oneline model/`
5. Monitor GC overhead with: `kubectl exec -it <pod> -- jstat -gcutil <pid> 5000`

### Remediation Steps — Immediate
1. **Increase heap** (temporary): Set JVM flag `-Xmx8g` via env var `JAVA_OPTS`
2. **Rolling restart** to clear leaked memory (buys time): `kubectl rollout restart deployment/recommendation-engine`
3. **Scale out**: Add more replicas to distribute load while memory issue is diagnosed

### Remediation Steps — Root Cause
1. If issue started after model deploy: **rollback model version**
   ```bash
   kubectl set image deployment/recommendation-engine app=rec-engine:previous-version
   ```
2. Enable lazy loading: set `MODEL_LOADING_STRATEGY=lazy` in configmap
3. Set cache eviction: configure `FEATURE_CACHE_MAX_SIZE=500MB` and eviction TTL

### JVM Tuning Recommendations
```
-Xms4g -Xmx8g
-XX:+UseG1GC
-XX:G1HeapRegionSize=16m
-XX:MaxGCPauseMillis=500
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/dumps/
```

### Escalation
- **ML Platform Team**: For model-related memory issues
- **Platform Team**: For infrastructure-level scaling
