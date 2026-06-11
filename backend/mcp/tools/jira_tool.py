"""MCP Tool: search_past_incidents → Mock Jira API."""
import logging
from typing import Any, Dict, List, Optional

import httpx
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def search_past_incidents(
    service: str,
    alert_type: Optional[str] = None,
    error_code: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search mock Jira for past incidents matching service/alert_type/error_code.

    Returns a list of incident dicts.
    """
    url = f"{settings.mock_jira_url}/api/incidents/search"
    params: Dict[str, Any] = {"service": service, "limit": limit}
    if alert_type:
        params["alert_type"] = alert_type
    if error_code:
        params["error_code"] = error_code

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"[jira_tool] Got {len(data.get('incidents', []))} past incidents")
        return data.get("incidents", [])
