"""MCP Tools: ServiceNow — search incidents, get details, create tickets."""
import logging
from typing import Any, Dict, Optional

import httpx
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def search_servicenow_incidents(
    service: str,
    alert_type: str = "",
    error_code: str = "",
    limit: int = 10,
) -> Dict[str, Any]:
    """Search ServiceNow for past/open incidents matching the given service and alert type."""
    url = f"{settings.mock_servicenow_url}/api/incidents/search"
    params: Dict[str, Any] = {"service": service, "limit": limit}
    if alert_type:
        params["alert_type"] = alert_type
    if error_code:
        params["error_code"] = error_code

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        logger.info(
            "[servicenow_tool] search returned %d incidents (%d open) for service=%s",
            data.get("total", 0),
            data.get("open_count", 0),
            service,
        )
        return data


async def get_incident_details(ticket_id: str) -> Dict[str, Any]:
    """Fetch full details for a specific incident ticket from mock ServiceNow."""
    url = f"{settings.mock_servicenow_url}/api/incidents/{ticket_id}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def create_incident_ticket(
    title: str,
    description: str,
    severity: str,
    service: str,
) -> Dict[str, Any]:
    """Create a new incident ticket in mock ServiceNow."""
    url = f"{settings.mock_servicenow_url}/api/incidents"
    payload = {"title": title, "description": description, "severity": severity, "service": service}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        logger.info("[servicenow_tool] Created ticket: %s", data.get("ticket_id"))
        return data
