"""MCP Tools: search_logs, get_log_trends -> Mock Splunk/ELK API."""
import logging
from typing import Any, Dict, List

import httpx
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def search_logs(
    service: str,
    timestamp: str,
    window_minutes: int = 30,
) -> List[Dict[str, Any]]:
    """Query the mock Splunk/ELK endpoint for log entries."""
    url = f"{settings.mock_splunk_url}/api/logs/search"
    params = {"service": service, "timestamp": timestamp, "window_minutes": window_minutes}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        logger.debug("[splunk_tool] Got %d log entries", len(data.get("logs", [])))
        return data.get("logs", [])


async def get_log_trends(
    service: str,
    window_minutes: int = 30,
) -> Dict[str, Any]:
    """Return error-rate trend and anomaly score for predictive monitoring."""
    url = f"{settings.mock_splunk_url}/api/logs/trends"
    params = {"service": service, "window_minutes": window_minutes}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
