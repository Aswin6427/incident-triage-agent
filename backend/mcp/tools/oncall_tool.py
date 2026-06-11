"""MCP Tools: On-Call schedule lookup and paging via Mock On-Call API."""
import logging
from typing import Any, Dict, Optional

import httpx
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_oncall_engineer(service: str, team: Optional[str] = None) -> Dict[str, Any]:
    """Return the current on-call engineer for the given service or team."""
    url = f"{settings.mock_oncall_url}/api/oncall/by-service/{service}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        logger.info(
            "[oncall_tool] On-call for %s: %s (%s shift)",
            service,
            data.get("engineer", {}).get("name", "unknown"),
            data.get("shift", "?"),
        )
        return data


async def page_oncall_engineer(
    service: str,
    incident_id: str,
    severity: str,
    message: str,
    team: Optional[str] = None,
) -> Dict[str, Any]:
    """Page the on-call engineer for the given service."""
    url = f"{settings.mock_oncall_url}/api/oncall/page"
    payload = {
        "team": team or service,
        "service": service,
        "incident_id": incident_id,
        "severity": severity,
        "message": message,
        "paged_by": "triage-agent",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        logger.info("[oncall_tool] Paged %s for %s", data.get("engineer_paged", {}).get("name"), incident_id)
        return data
