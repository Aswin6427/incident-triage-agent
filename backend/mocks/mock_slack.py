"""
Mock Slack Webhook — receives and stores incident reports.

Run on port 8004:
    uvicorn backend.mocks.mock_slack:app --port 8004 --reload
"""
import json
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI(title="Mock Slack", version="1.0.0")

# In-memory message store
_messages: List[Dict[str, Any]] = []


class SlackPostRequest(BaseModel):
    channel: str
    text: str
    incident_id: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-slack"}


@app.post("/api/slack/post")
async def post_message(req: SlackPostRequest):
    """Receive and store a Slack-formatted report."""
    msg = {
        "id": len(_messages) + 1,
        "channel": req.channel,
        "text": req.text,
        "incident_id": req.incident_id,
        "received_at": datetime.utcnow().isoformat() + "Z",
    }
    _messages.append(msg)

    # Pretty-print to console for demo visibility (safe encoding)
    sep = "=" * 60
    try:
        print(f"\n{sep}")
        print(f"[SLACK] --> {req.channel}  (incident: {req.incident_id})")
        print("-" * 60)
        print(req.text)
        print(f"{sep}\n")
    except UnicodeEncodeError:
        print(f"[SLACK] Message received for {req.channel}")

    return {"ok": True, "message_id": msg["id"]}


@app.get("/api/slack/messages")
async def get_messages(channel: Optional[str] = None):
    """List all received messages (for inspection)."""
    msgs = _messages
    if channel:
        msgs = [m for m in msgs if m["channel"] == channel]
    return {"messages": msgs, "total": len(msgs)}


@app.get("/api/slack/messages/{message_id}")
async def get_message(message_id: int):
    """Get a specific message by ID."""
    for msg in _messages:
        if msg["id"] == message_id:
            return msg
    return {"error": "Message not found"}, 404
