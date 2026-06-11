"""
PredictiveMonitorAgent -- checks error-rate trends across all services
and fires proactive PREDICTED_INCIDENT alerts before thresholds are breached.
"""
import logging
from typing import Any, Dict, List

from backend.mcp.gateway import MCPGateway

logger = logging.getLogger(__name__)

MONITORED_SERVICES = [
    "payment-service",
    "auth-service",
    "recommendation-engine",
    "checkout-service",
    "notification-service",
]

# Alert type inferred from top error codes
ERROR_CODE_TO_ALERT = {
    "CONN_TIMEOUT_5023": "DB_CONNECTION_TIMEOUT",
    "DB_POOL_EXHAUSTED":  "DB_CONNECTION_TIMEOUT",
    "CACHE_MISS_HIGH":    "HIGH_ERROR_RATE",
    "OOM_ERROR":          "MEMORY_LEAK",
    "HEAP_HIGH":          "MEMORY_LEAK",
    "NPE_CHECKOUT":       "DEPLOY_REGRESSION",
    "DEPENDENCY_503":     "DEPENDENCY_FAILURE",
    "SMS_TIMEOUT":        "DEPENDENCY_FAILURE",
}

ANOMALY_THRESHOLD = 0.55      # fire if anomaly_score exceeds this
ERROR_RATE_MULTIPLIER = 2.5   # fire if current > baseline * this
RATE_OF_CHANGE_THRESHOLD = 0.25  # fire if increasing faster than this %/min


class PredictiveMonitorAgent:
    """Polls Splunk trends and returns predicted incidents for at-risk services."""

    def __init__(self, mcp_gateway: MCPGateway):
        self.mcp = mcp_gateway

    async def run(self) -> List[Dict[str, Any]]:
        """Check all services. Returns a list of predicted alert dicts."""
        predictions: List[Dict[str, Any]] = []

        for service in MONITORED_SERVICES:
            try:
                trend = await self.mcp.call_tool("get_log_trends", {"service": service})
                if self._should_predict(trend):
                    predictions.append(self._build_prediction(service, trend))
            except Exception as exc:
                logger.warning("[PredictiveMonitor] Failed to get trend for %s: %s", service, exc)

        if predictions:
            logger.info("[PredictiveMonitor] %d service(s) at risk: %s",
                        len(predictions), [p["service"] for p in predictions])
        else:
            logger.info("[PredictiveMonitor] All services within normal thresholds")

        return predictions

    def _should_predict(self, trend: Dict[str, Any]) -> bool:
        anomaly     = trend.get("anomaly_score", 0)
        current     = trend.get("current_error_rate_pct", 0)
        baseline    = trend.get("baseline_error_rate_pct", 1)
        roc         = trend.get("rate_of_change_per_min", 0)
        trend_label = trend.get("trend", "stable")

        return (
            anomaly > ANOMALY_THRESHOLD
            or current > baseline * ERROR_RATE_MULTIPLIER
            or (trend_label == "increasing" and roc > RATE_OF_CHANGE_THRESHOLD)
        )

    def _build_prediction(self, service: str, trend: Dict[str, Any]) -> Dict[str, Any]:
        top_codes  = trend.get("top_error_codes", [])
        alert_type = next(
            (ERROR_CODE_TO_ALERT[c] for c in top_codes if c in ERROR_CODE_TO_ALERT),
            "HIGH_ERROR_RATE",
        )

        anomaly = trend.get("anomaly_score", 0)
        if anomaly > 0.8:
            confidence = "High"
            severity   = "P2"
        elif anomaly > 0.6:
            confidence = "Medium"
            severity   = "P3"
        else:
            confidence = "Low"
            severity   = "P3"

        eta = trend.get("predicted_threshold_breach_minutes", 20)

        return {
            "service":         service,
            "alert_type":      alert_type,
            "predicted":       True,
            "confidence":      confidence,
            "severity":        severity,
            "eta_minutes":     eta,
            "anomaly_score":   round(trend.get("anomaly_score", 0), 3),
            "current_error_rate_pct": trend.get("current_error_rate_pct", 0),
            "baseline_error_rate_pct": trend.get("baseline_error_rate_pct", 1),
            "trend":           trend.get("trend", "stable"),
            "top_error_codes": top_codes,
            "description":     (
                f"Error rate trending {trend.get('trend')} on {service}. "
                f"Current: {trend.get('current_error_rate_pct', 0):.1f}% "
                f"(baseline: {trend.get('baseline_error_rate_pct', 1):.1f}%). "
                f"Predicted to breach threshold in ~{eta} min."
            ),
            "data_points":     trend.get("data_points", []),
        }
