"""Tests for mock external API services."""
import pytest
from httpx import AsyncClient, ASGITransport

from backend.mocks.mock_jira import app as jira_app
from backend.mocks.mock_splunk import app as splunk_app
from backend.mocks.mock_servicenow import app as servicenow_app
from backend.mocks.mock_slack import app as slack_app


@pytest.mark.asyncio
async def test_mock_jira_health():
    async with AsyncClient(transport=ASGITransport(app=jira_app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_mock_jira_search_payment_service():
    async with AsyncClient(transport=ASGITransport(app=jira_app), base_url="http://test") as client:
        response = await client.get("/api/incidents/search", params={"service": "payment-service"})
    assert response.status_code == 200
    data = response.json()
    assert "incidents" in data
    assert len(data["incidents"]) > 0
    assert data["incidents"][0]["service"] == "payment-service"


@pytest.mark.asyncio
async def test_mock_jira_search_with_alert_type():
    async with AsyncClient(transport=ASGITransport(app=jira_app), base_url="http://test") as client:
        response = await client.get(
            "/api/incidents/search",
            params={"service": "payment-service", "alert_type": "DB_CONNECTION_TIMEOUT"},
        )
    data = response.json()
    assert len(data["incidents"]) > 0
    assert data["incidents"][0]["alert_type"] == "DB_CONNECTION_TIMEOUT"


@pytest.mark.asyncio
async def test_mock_splunk_health():
    async with AsyncClient(transport=ASGITransport(app=splunk_app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_mock_splunk_search_logs():
    async with AsyncClient(transport=ASGITransport(app=splunk_app), base_url="http://test") as client:
        response = await client.get(
            "/api/logs/search",
            params={"service": "payment-service", "timestamp": "2025-05-27T14:32:00Z"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert len(data["logs"]) > 0


@pytest.mark.asyncio
async def test_mock_servicenow_create_and_get():
    async with AsyncClient(transport=ASGITransport(app=servicenow_app), base_url="http://test") as client:
        # Create
        create_resp = await client.post(
            "/api/incidents",
            json={
                "title": "Test incident",
                "description": "Testing ServiceNow mock",
                "severity": "P2",
                "service": "test-service",
            },
        )
        assert create_resp.status_code == 201
        ticket = create_resp.json()
        assert "ticket_id" in ticket

        # Retrieve
        get_resp = await client.get(f"/api/incidents/{ticket['ticket_id']}")
        assert get_resp.status_code == 200
        assert get_resp.json()["ticket_id"] == ticket["ticket_id"]


@pytest.mark.asyncio
async def test_mock_slack_post():
    async with AsyncClient(transport=ASGITransport(app=slack_app), base_url="http://test") as client:
        response = await client.post(
            "/api/slack/post",
            json={
                "channel": "#incidents",
                "text": "Test triage report",
                "incident_id": "INC-TEST-001",
            },
        )
    assert response.status_code == 200
    assert response.json()["ok"] is True
