"""MCP Tool: post_slack_report → Mock Slack Webhook."""
import json
import logging
from typing import Any, Dict

import httpx
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _format_slack_message(report: Dict[str, Any]) -> str:
    """Format the triage report as a Slack-friendly message."""
    hypotheses = report.get("root_cause_hypotheses", [])
    checklist = report.get("remediation_checklist", [])
    escalation = report.get("escalation_recommendation") or {}

    lines = [
        f"🚨 *INCIDENT TRIAGE REPORT* — `{report.get('incident_id', 'N/A')}`",
        f"⏱ Completed in {report.get('elapsed_seconds', '?')}s",
        "",
        f"*Alert:* {report.get('alert_summary', 'N/A')}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "*🔍 Root Cause Hypotheses*",
    ]

    for h in hypotheses[:3]:
        emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(h.get("confidence", ""), "⚪")
        lines.append(f"{emoji} *#{h.get('rank')}* {h.get('hypothesis')} ({h.get('confidence')} confidence)")
        for ev in (h.get("evidence") or [])[:2]:
            lines.append(f"   › {ev}")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "*🛠 Remediation Checklist (Top 5)*",
    ]

    for step in checklist[:5]:
        lines.append(f"{step.get('priority', '?')}. {step.get('action')} — _{step.get('owner', 'Engineer')}_ ({step.get('estimated_time', '?')})")

    if escalation.get("required"):
        lines += [
            "",
            f"⚠️ *ESCALATION REQUIRED* [{escalation.get('priority')}] → {escalation.get('team')}",
            f"Reason: {escalation.get('reason', '')}",
        ]

    return "\n".join(lines)


async def post_slack_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Post formatted triage report to mock Slack webhook."""
    slack_message = _format_slack_message(report)
    url = f"{settings.mock_slack_url}/api/slack/post"
    payload = {
        "channel": "#incidents",
        "text": slack_message,
        "incident_id": report.get("incident_id"),
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        logger.info(f"[slack_tool] Report posted for incident {report.get('incident_id')}")
        return {"status": "posted", "slack_message": slack_message}
