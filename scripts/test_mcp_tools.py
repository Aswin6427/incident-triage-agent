"""
Test all 9 MCP tools by spawning the MCP server as a subprocess
and calling each tool through the official MCP Python client.
"""
import asyncio
import json
import os
import sys

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_CMD = sys.executable
SERVER_ARGS = ["-m", "backend.mcp.server"]
ENV = {**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(__file__))}

SEP  = "=" * 70
THIN = "-" * 70

# ── Test cases for every tool ─────────────────────────────────
TESTS = [
    {
        "tool": "search_logs",
        "args": {"service": "payment-service", "timestamp": "2026-06-08T10:00:00Z", "window_minutes": 30},
        "check": lambda r: isinstance(r, list) and len(r) > 0,
        "show":  lambda r: f"{len(r)} log entries returned | top entry level={r[0].get('level')} msg={r[0].get('message','')[:60]}",
    },
    {
        "tool": "get_log_trends",
        "args": {"service": "payment-service", "window_minutes": 30},
        "check": lambda r: "anomaly_score" in r and "trend" in r,
        "show":  lambda r: f"anomaly={r['anomaly_score']}  trend={r['trend']}  current={r['current_error_rate_pct']}%  baseline={r['baseline_error_rate_pct']}%  ETA={r['predicted_threshold_breach_minutes']}min",
    },
    {
        "tool": "search_past_incidents",
        "args": {"service": "payment-service", "alert_type": "DB_CONNECTION_TIMEOUT", "error_code": "CONN_TIMEOUT_5023"},
        "check": lambda r: isinstance(r, list) and len(r) > 0,
        "show":  lambda r: f"{len(r)} incidents | open/in-progress={sum(1 for i in r if i.get('status') in ('Open','In Progress'))} | top={r[0].get('ticket_id')} [{r[0].get('status')}]",
    },
    {
        "tool": "search_servicenow_incidents",
        "args": {"service": "payment-service", "alert_type": "DB_CONNECTION_TIMEOUT"},
        "check": lambda r: "incidents" in r,
        "show":  lambda r: f"{r['total']} incidents | open={r['open_count']} | top={r['incidents'][0]['ticket_id']} [{r['incidents'][0]['status']}]",
    },
    {
        "tool": "get_incident_details",
        "args": {"ticket_id": "SN-PAY003"},   # ServiceNow ID — tool routes to ServiceNow only
        "check": lambda r: "ticket_id" in r,
        "show":  lambda r: f"ticket={r['ticket_id']} status={r['status']} service={r['service']} severity={r['severity']}",
    },
    {
        "tool": "create_incident_ticket",
        "args": {
            "title":       "P1 - payment-service DB pool exhausted after deploy v2.3.2",
            "description": "Connection pool exhausted. 847 CONN_TIMEOUT errors in 5 min. Suspected leak in PaymentRepository.",
            "severity":    "P1",
            "service":     "payment-service",
        },
        "check": lambda r: "ticket_id" in r and r.get("status") == "Open",
        "show":  lambda r: f"created ticket={r['ticket_id']} status={r['status']} team={r['assigned_team']}",
    },
    {
        "tool": "post_slack_report",
        "args": {
            "report": {
                "incident_id":   "INC-TEST01",
                "alert_summary": "[P1] DB_CONNECTION_TIMEOUT on payment-service in us-east-1",
                "oncall_engineer": {"name": "Alice Chen", "slack": "@alice.chen"},
                "root_cause_hypotheses": [
                    {"rank": 1, "hypothesis": "Connection leak in v2.3.1 PaymentRepository", "confidence": "High"}
                ],
            }
        },
        "check": lambda r: r.get("status") == "posted",
        "show":  lambda r: f"status={r['status']}  preview={r['slack_message'][:80]}",
    },
    {
        "tool": "get_oncall_engineer",
        "args": {"service": "payment-service"},
        "check": lambda r: "engineer" in r and "name" in r["engineer"],
        "show":  lambda r: f"team={r['team']}  shift={r['shift']}  engineer={r['engineer']['name']}  email={r['engineer']['email']}",
    },
    {
        "tool": "page_oncall_engineer",
        "args": {
            "service":     "payment-service",
            "incident_id": "INC-TEST01",
            "severity":    "P1",
            "message":     "P1 INCIDENT on payment-service: DB_CONNECTION_TIMEOUT. Pool exhausted. Immediate rollback required.",
        },
        "check": lambda r: "page_id" in r and r.get("status") == "delivered",
        "show":  lambda r: f"page_id={r['page_id']}  paged={r['engineer_paged']['name']}  channel={r['channel']}  status={r['status']}",
    },
]


async def run_tests():
    params = StdioServerParameters(command=SERVER_CMD, args=SERVER_ARGS, env=ENV)

    print(f"\n{SEP}")
    print("  MCP TOOL TEST SUITE  --  incident-triage-agent")
    print(f"  Server: python -m backend.mcp.server  (stdio mode)")
    print(SEP)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools first
            tools_resp = await session.list_tools()
            tools = tools_resp.tools
            print(f"\n  Connected. {len(tools)} tools discovered:\n")
            for t in tools:
                print(f"    [ok] {t.name}")

            print(f"\n{SEP}")
            print("  RUNNING TESTS")
            print(SEP)

            passed = 0
            failed = 0

            for test in TESTS:
                tool_name = test["tool"]
                args      = test["args"]
                print(f"\n  [{tool_name}]")
                print(f"  Input: {json.dumps(args)[:120]}")

                try:
                    result = await session.call_tool(tool_name, args)
                    raw    = result.content[0].text if result.content else ""
                    parsed = json.loads(raw)

                    ok = test["check"](parsed)
                    summary = test["show"](parsed)

                    if ok:
                        print(f"  PASS  {summary}")
                        passed += 1
                    else:
                        print(f"  FAIL  check failed — raw: {raw[:120]}")
                        failed += 1

                except Exception as exc:
                    print(f"  ERROR  {exc}")
                    failed += 1

            print(f"\n{SEP}")
            print(f"  RESULTS:  {passed} passed  /  {failed} failed  /  {len(TESTS)} total")
            print(SEP)


if __name__ == "__main__":
    asyncio.run(run_tests())
