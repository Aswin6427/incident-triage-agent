"""
Generate a PDF document explaining the Incident Triage Agent architecture and flow.
Usage: python scripts/generate_flow_doc.py
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import Preformatted
import os

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Incident_Triage_Agent_Flow_v2.pdf")

# ── Colour palette ────────────────────────────────────────────
DARK_BG   = colors.HexColor("#1E293B")
ACCENT    = colors.HexColor("#3B82F6")
ACCENT2   = colors.HexColor("#8B5CF6")
GREEN     = colors.HexColor("#22C55E")
ORANGE    = colors.HexColor("#F59E0B")
RED       = colors.HexColor("#EF4444")
LIGHT_BG  = colors.HexColor("#F1F5F9")
MID_GREY  = colors.HexColor("#64748B")
CODE_BG   = colors.HexColor("#0F172A")
WHITE     = colors.white
TEXT      = colors.HexColor("#1E293B")


def build_styles():
    base = getSampleStyleSheet()

    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title",
        fontSize=28, leading=34, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=8,
    )
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub",
        fontSize=13, leading=18, textColor=colors.HexColor("#94A3B8"),
        fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4,
    )
    styles["h1"] = ParagraphStyle(
        "h1",
        fontSize=16, leading=20, textColor=WHITE,
        fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=6,
        backColor=DARK_BG, borderPad=6,
        leftIndent=-0.3*cm, rightIndent=-0.3*cm,
    )
    styles["h2"] = ParagraphStyle(
        "h2",
        fontSize=13, leading=17, textColor=ACCENT,
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=4,
    )
    styles["h3"] = ParagraphStyle(
        "h3",
        fontSize=11, leading=15, textColor=ACCENT2,
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=3,
    )
    styles["body"] = ParagraphStyle(
        "body",
        fontSize=10, leading=15, textColor=TEXT,
        fontName="Helvetica", spaceAfter=4,
    )
    styles["body_small"] = ParagraphStyle(
        "body_small",
        fontSize=9, leading=13, textColor=MID_GREY,
        fontName="Helvetica", spaceAfter=3,
    )
    styles["bullet"] = ParagraphStyle(
        "bullet",
        fontSize=10, leading=15, textColor=TEXT,
        fontName="Helvetica", leftIndent=16, spaceAfter=3,
        bulletIndent=6,
    )
    styles["code"] = ParagraphStyle(
        "code",
        fontSize=8.5, leading=13, textColor=colors.HexColor("#E2E8F0"),
        fontName="Courier", backColor=CODE_BG,
        leftIndent=10, rightIndent=10, spaceBefore=6, spaceAfter=6,
        borderPad=8,
    )
    styles["label_green"] = ParagraphStyle(
        "label_green",
        fontSize=9, textColor=GREEN, fontName="Helvetica-Bold",
    )
    styles["label_orange"] = ParagraphStyle(
        "label_orange",
        fontSize=9, textColor=ORANGE, fontName="Helvetica-Bold",
    )
    styles["label_red"] = ParagraphStyle(
        "label_red",
        fontSize=9, textColor=RED, fontName="Helvetica-Bold",
    )
    styles["note"] = ParagraphStyle(
        "note",
        fontSize=9, leading=13, textColor=colors.HexColor("#475569"),
        fontName="Helvetica-Oblique", leftIndent=12, spaceAfter=4,
    )
    return styles


def hr(color=ACCENT, thickness=1):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=6, spaceBefore=2)


def code_block(text, styles):
    return Paragraph(text.replace("\n", "<br/>").replace(" ", "&nbsp;"), styles["code"])


def build_doc():
    S = build_styles()
    story = []
    W, H = A4

    # ══════════════════════════════════════════════════════════
    # COVER
    # ══════════════════════════════════════════════════════════
    cover_table = Table(
        [[Paragraph("Incident Triage Agent", S["cover_title"])],
         [Paragraph("Architecture, Working Flow, Prediction Engine &amp; Token Optimization", S["cover_sub"])],
         [Spacer(1, 0.3*cm)],
         [Paragraph("A detailed technical walkthrough", S["cover_sub"])],
         ],
        colWidths=[W - 4*cm],
    )
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 20),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
        ("LEFTPADDING",   (0, 0), (-1, -1), 30),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 30),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [DARK_BG]),
    ]))
    story.append(Spacer(1, 1*cm))
    story.append(cover_table)
    story.append(Spacer(1, 0.6*cm))

    # ══════════════════════════════════════════════════════════
    # SECTION 1 — OVERVIEW
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("1.  Project Overview", S["h1"]))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "The Incident Triage Agent is an AI-powered system that automatically diagnoses production "
        "alerts, identifies root causes, and pages the correct on-call engineer — all without human "
        "intervention. It also <b>predicts incidents before they occur</b> by continuously monitoring "
        "error-rate trends across all services.",
        S["body"],
    ))
    story.append(Paragraph(
        "The stack: <b>React + TypeScript</b> frontend, <b>FastAPI</b> backend, "
        "<b>LangGraph</b> state machine, <b>Azure OpenAI GPT</b> for reasoning, "
        "<b>FAISS</b> vector store for runbook retrieval, and five mock microservices "
        "(Jira, Splunk, ServiceNow, Slack, On-Call).",
        S["body"],
    ))

    # ══════════════════════════════════════════════════════════
    # SECTION 2 — SYSTEM ARCHITECTURE
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("2.  System Architecture", S["h1"]))

    arch_data = [
        ["Component", "Port", "Role"],
        ["React UI",            "5173", "Live dashboard — alert feed, agent flow panel, triage report"],
        ["FastAPI Backend",     "8000", "REST API + WebSocket hub + LangGraph pipeline orchestrator"],
        ["Mock Jira",           "8001", "Historical incident tickets (past + currently open)"],
        ["Mock Splunk/ELK",     "8002", "Application logs + error-rate trend data for predictions"],
        ["Mock ServiceNow",     "8003", "ITSM tickets — search, get, create"],
        ["Mock Slack",          "8004", "Receives and stores formatted incident reports"],
        ["Mock On-Call",        "8005", "Shift-based engineer routing + page events"],
    ]
    arch_table = Table(arch_data, colWidths=[4*cm, 1.8*cm, 10.4*cm])
    arch_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  DARK_BG),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_BG, WHITE]),
        ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 7),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("Communication topology:", S["h3"]))
    story.append(code_block(
        "React UI (5173)\n"
        "    │  WebSocket (ws://)  +  REST fetch (via Vite proxy)\n"
        "    ▼\n"
        "FastAPI Backend (8000)\n"
        "    │  MCP Gateway  (tool calls — never direct HTTP from agents)\n"
        "    ├──► Jira (8001)       search_past_incidents\n"
        "    ├──► Splunk (8002)     search_logs  /  get_log_trends\n"
        "    ├──► ServiceNow (8003) search_servicenow_incidents / create_incident_ticket\n"
        "    ├──► Slack (8004)      post_slack_report\n"
        "    └──► On-Call (8005)    get_oncall_engineer / page_oncall_engineer",
        S,
    ))

    # ══════════════════════════════════════════════════════════
    # SECTION 3 — REACTIVE TRIAGE FLOW
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("3.  Reactive Triage Flow  (Alert → Resolution)", S["h1"]))

    # Step 3.1
    story.append(Paragraph("Step 1 — Alert Ingestion", S["h2"]))
    story.append(Paragraph(
        "An external monitoring system (or the test script) sends a JSON payload to "
        "<b>POST /alert</b>. The payload contains the service name, alert type, severity, "
        "affected endpoints, and current metrics.",
        S["body"],
    ))
    story.append(code_block(
        "python scripts/push_alert.py --scenario db_timeout\n"
        "  │\n"
        "  └─► POST http://localhost:8000/alert\n"
        "        {\n"
        "          \"service\":   \"payment-service\",\n"
        "          \"alert_type\": \"DB_CONNECTION_TIMEOUT\",\n"
        "          \"severity\":  \"P1\",\n"
        "          \"metrics\":   {\"error_rate\": \"23%\", \"latency_p99\": \"8200ms\"}\n"
        "        }",
        S,
    ))
    story.append(Paragraph(
        "The backend immediately:",
        S["body"],
    ))
    for b in [
        "Creates an incident record in memory with status <b>ingested</b>.",
        "Broadcasts a <b>new_alert</b> WebSocket event — the UI card appears instantly.",
        "Returns HTTP 202 Accepted (non-blocking).",
        "Spawns the triage pipeline as a background asyncio task.",
    ]:
        story.append(Paragraph(f"• {b}", S["bullet"]))
    story.append(Spacer(1, 0.2*cm))

    # Step 3.2
    story.append(Paragraph("Step 2 — LangGraph State Machine", S["h2"]))
    story.append(Paragraph(
        "The triage pipeline is a <b>directed acyclic graph</b> built with LangGraph. "
        "Each node is an async function that reads from and writes to a shared "
        "<b>IncidentState</b> dictionary. The graph compiles to a runnable that "
        "streams intermediate state updates — every node completion fires a WebSocket "
        "broadcast so the UI agent-flow panel updates in real time.",
        S["body"],
    ))
    story.append(code_block(
        "START\n"
        "  │\n"
        "  ▼\n"
        "ingest_node          ← resets flags, records start time\n"
        "  │\n"
        "  ├────────────────────────┬────────────────────────┐\n"
        "  ▼                        ▼                        ▼\n"
        "log_analyzer_node    past_ticket_node         runbook_node\n"
        "(Splunk logs)        (Jira + ServiceNow)      (FAISS / RAG)\n"
        "  │                        │                        │\n"
        "  └────────────────────────┴────────────────────────┘\n"
        "                           │   fan-in (all 3 must finish)\n"
        "                           ▼\n"
        "                    root_cause_node     ← Azure OpenAI GPT\n"
        "                           │\n"
        "                           ▼\n"
        "                     report_node        ← on-call lookup, page, Slack post\n"
        "                           │\n"
        "                          END",
        S,
    ))

    # Step 3.3
    story.append(Paragraph("Step 3 — Parallel Evidence Gathering", S["h2"]))
    story.append(Paragraph(
        "Three agents run <b>simultaneously</b> after ingest_node completes:",
        S["body"],
    ))

    parallel_data = [
        ["Agent", "Tool Called", "Data Fetched"],
        ["LogAnalyzerAgent",
         "search_logs\n→ Splunk (8002)",
         "Error + FATAL logs for the service in the last 30 min.\nIncludes scenario-specific anchor logs injected by the mock."],
        ["PastTicketAgent",
         "search_past_incidents → Jira (8001)\nsearch_servicenow_incidents → ServiceNow (8003)",
         "Historical resolved incidents matching the service + alert type.\nAlso returns currently OPEN / IN-PROGRESS tickets."],
        ["RunbookAgent",
         "RAGRetriever.search()\n→ local FAISS index",
         "Top-5 semantically similar runbook chunks.\nEmbedded at startup using Azure OpenAI Embeddings API."],
    ]
    pt = Table(parallel_data, colWidths=[3.5*cm, 4.5*cm, 8.2*cm])
    pt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BG, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(pt)
    story.append(Spacer(1, 0.2*cm))

    # Step 3.4
    story.append(Paragraph("Step 4 — Root Cause Synthesis  (Azure OpenAI GPT)", S["h2"]))
    story.append(Paragraph(
        "Once all three parallel agents finish, <b>root_cause_node</b> calls Azure OpenAI "
        "with a structured prompt that bundles all gathered evidence:",
        S["body"],
    ))
    story.append(code_block(
        "=== ALERT DETAILS ===         ← original alert payload\n"
        "=== LOG ANALYSIS FINDINGS === ← Splunk error patterns\n"
        "=== SIMILAR PAST INCIDENTS === ← resolved Jira + ServiceNow tickets\n"
        "=== CURRENTLY OPEN TICKETS === ← active in-progress tickets (!)\n"
        "=== RUNBOOK GUIDANCE ===       ← RAG-retrieved runbook text",
        S,
    ))
    story.append(Paragraph("The LLM (temperature=0) responds with strict JSON:", S["body"]))
    for b in [
        "<b>hypotheses</b> — Top 3 root cause hypotheses ranked by confidence (High/Medium/Low), each with evidence quotes and remediation steps.",
        "<b>remediation_checklist</b> — 10 prioritised actions with owner and time estimate per step.",
        "<b>escalation</b> — Boolean required flag, priority level, team to escalate to, and reason.",
    ]:
        story.append(Paragraph(f"• {b}", S["bullet"]))
    story.append(Paragraph(
        "Open tickets are critical inputs here — if Jira/ServiceNow already has an active "
        "investigation for the same service and error code, the LLM references those ticket "
        "IDs in its evidence and remediation steps.",
        S["note"],
    ))

    # Step 3.5
    story.append(Paragraph("Step 5 — Report Generation, On-Call Paging &amp; Slack", S["h2"]))
    story.append(Paragraph(
        "<b>report_node</b> assembles the final report and performs three actions:",
        S["body"],
    ))

    report_data = [
        ["Action", "How", "Condition"],
        ["On-call lookup",
         "GET /api/oncall/current?service=<name>\nMock On-Call (8005)",
         "Always — resolves the team and current shift engineer (morning/afternoon/night UTC rotation)"],
        ["Auto-page engineer",
         "POST /api/oncall/page\nMock On-Call (8005)",
         "Only if: escalation.required=true AND severity=P1"],
        ["Post to Slack",
         "POST /api/slack/post\nMock Slack (8004)",
         "Always — full structured report sent to the incident channel"],
    ]
    rt = Table(report_data, colWidths=[3.5*cm, 5.5*cm, 7.2*cm])
    rt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BG, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(rt)
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "Every state change throughout steps 1–5 is broadcast over WebSocket so the React "
        "UI updates live: the agent-flow panel shows each node going from pending → running "
        "→ completed, and the progress bar advances in real time.",
        S["note"],
    ))

    # Step 3.6
    story.append(Paragraph("Step 6 — Post-Mortem  (human-triggered)", S["h2"]))
    story.append(Paragraph(
        "After the incident reaches <b>done</b> status, an engineer clicks Resolve in the UI, "
        "which calls <b>POST /incidents/{id}/resolve</b> with a resolution summary, confirmed "
        "root cause, and who resolved it. <b>PostMortemAgent</b> runs another Azure OpenAI call "
        "to generate a full post-mortem document, stored at <b>GET /post-mortems/{id}</b>.",
        S["body"],
    ))

    # ══════════════════════════════════════════════════════════
    # SECTION 4 — PREDICTIVE MONITORING
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("4.  Predictive Monitoring  (Before the alert fires)", S["h1"]))
    story.append(Paragraph(
        "The predictive path runs completely independently of the reactive triage pipeline. "
        "It is a background asyncio loop that starts at application startup and polls "
        "Splunk trend data for all monitored services on a configurable interval.",
        S["body"],
    ))

    story.append(Paragraph("4.1  How it starts", S["h2"]))
    story.append(code_block(
        "# backend/main.py — FastAPI lifespan startup\n"
        "asyncio.create_task(run_predictive_monitor())\n"
        "\n"
        "async def run_predictive_monitor():\n"
        "    await asyncio.sleep(15)   # wait for mocks to start\n"
        "    while True:\n"
        "        agent = PredictiveMonitorAgent(mcp_gateway=MCPGateway())\n"
        "        predictions = await agent.run()   # check all 5 services\n"
        "        for pred in predictions:\n"
        "            await manager.broadcast({\"event\": \"prediction\", ...})\n"
        "        await asyncio.sleep(interval)     # configured in .env",
        S,
    ))

    story.append(Paragraph("4.2  Per-service trend check", S["h2"]))
    story.append(Paragraph(
        "For each of the 5 monitored services, the agent calls "
        "<b>get_log_trends</b> via the MCP Gateway, which hits "
        "<b>GET /api/logs/trends?service=&lt;name&gt;</b> on Mock Splunk (8002). "
        "The response contains:",
        S["body"],
    ))

    trend_data = [
        ["Field", "Meaning"],
        ["current_error_rate_pct",          "Live error rate (%) right now"],
        ["baseline_error_rate_pct",         "Normal/expected error rate for this service"],
        ["trend",                           "\"increasing\" | \"stable-elevated\" | \"stable\""],
        ["rate_of_change_per_min",          "How fast the error rate is growing (% per minute)"],
        ["anomaly_score",                   "0.0–1.0 composite anomaly score"],
        ["predicted_threshold_breach_minutes", "ETA until SLA threshold is breached"],
        ["top_error_codes",                 "e.g. [\"CONN_TIMEOUT_5023\", \"DB_POOL_EXHAUSTED\"]"],
    ]
    td = Table(trend_data, colWidths=[6.5*cm, 9.7*cm])
    td.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BG, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(td)
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("4.3  Prediction decision logic", S["h2"]))
    story.append(Paragraph(
        "The agent fires a prediction if <b>ANY ONE</b> of three conditions is true:",
        S["body"],
    ))
    story.append(code_block(
        "ANOMALY_THRESHOLD        = 0.55   # anomaly_score > 0.55\n"
        "ERROR_RATE_MULTIPLIER    = 2.5    # current > baseline × 2.5\n"
        "RATE_OF_CHANGE_THRESHOLD = 0.25   # roc > 0.25 %/min AND trend = \"increasing\"\n"
        "\n"
        "def _should_predict(trend):\n"
        "    return (\n"
        "        anomaly_score > 0.55\n"
        "        OR current_error_rate > baseline * 2.5\n"
        "        OR (trend == \"increasing\" AND rate_of_change > 0.25)\n"
        "    )",
        S,
    ))

    story.append(Paragraph("4.4  Confidence and severity mapping", S["h2"]))
    conf_data = [
        ["anomaly_score range", "Confidence", "Predicted Severity"],
        ["> 0.8",   "High",   "P2"],
        ["0.6–0.8", "Medium", "P3"],
        ["< 0.6",   "Low",    "P3"],
    ]
    ct = Table(conf_data, colWidths=[5*cm, 4*cm, 7.2*cm])
    ct.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BG, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(ct)
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("4.5  Alert type inference from error codes", S["h2"]))
    story.append(Paragraph(
        "The top error codes from the trend response are mapped to known alert types:",
        S["body"],
    ))
    story.append(code_block(
        "CONN_TIMEOUT_5023  →  DB_CONNECTION_TIMEOUT\n"
        "DB_POOL_EXHAUSTED  →  DB_CONNECTION_TIMEOUT\n"
        "CACHE_MISS_HIGH    →  HIGH_ERROR_RATE\n"
        "OOM_ERROR          →  MEMORY_LEAK\n"
        "HEAP_HIGH          →  MEMORY_LEAK\n"
        "NPE_CHECKOUT       →  DEPLOY_REGRESSION\n"
        "DEPENDENCY_503     →  DEPENDENCY_FAILURE\n"
        "SMS_TIMEOUT        →  DEPENDENCY_FAILURE",
        S,
    ))

    story.append(Paragraph("4.6  How the mock generates spikes  (demo realism)", S["h2"]))
    story.append(Paragraph(
        "The Mock Splunk trends endpoint injects random spikes so predictions fire "
        "occasionally but not on every poll cycle. The spike logic:",
        S["body"],
    ))
    story.append(code_block(
        "# mock_splunk.py — /api/logs/trends\n"
        "spike = random.choice([0, 0, 0, random.uniform(2.0, 6.0)])\n"
        "# 3 out of 4 polls → no spike (stable)\n"
        "# 1 out of 4 polls → spike of 2x–6x baseline injected\n"
        "\n"
        "anomaly = (current - baseline) / baseline * 0.5 + random.uniform(0, 0.25)\n"
        "# anomaly_score is proportional to how far current deviates from baseline",
        S,
    ))
    story.append(Paragraph(
        "4.7  What happens in the UI when a prediction fires", S["h2"],
    ))
    story.append(Paragraph(
        "The backend broadcasts a <b>prediction</b> WebSocket event. The React UI adds "
        "a new ⚠️ card to the alert feed (visually distinct from real incidents). "
        "Selecting it shows a prediction detail view — no agent pipeline runs, because "
        "no incident has occurred yet. If a real alert later fires for the same service, "
        "it appears as a separate incident card and the full triage pipeline runs.",
        S["body"],
    ))

    # ══════════════════════════════════════════════════════════
    # SECTION 5 — RAG PIPELINE
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("5.  RAG Pipeline  (Runbook Retrieval)", S["h1"]))
    story.append(Paragraph(
        "Retrieval-Augmented Generation provides the LLM with relevant runbook "
        "knowledge at triage time, grounding its reasoning in actual operational procedures.",
        S["body"],
    ))

    story.append(Paragraph("Build phase  (runs once at startup if index missing):", S["h3"]))
    story.append(code_block(
        "backend/rag/pipeline.py\n"
        "  1. Read runbook text files from backend/data/\n"
        "  2. Split into overlapping chunks (~500 tokens each)\n"
        "  3. Call Azure OpenAI Embeddings API → each chunk → float32 vector\n"
        "  4. Store vectors in FAISS flat index\n"
        "  5. Save index.faiss + metadata.pkl to backend/rag/faiss_index/",
        S,
    ))

    story.append(Paragraph("Query phase  (runs inside runbook_node per incident):", S["h3"]))
    story.append(code_block(
        "RAGRetriever.search(query=\"DB_CONNECTION_TIMEOUT payment-service\")\n"
        "  1. Embed the query string via Azure OpenAI Embeddings\n"
        "  2. FAISS.search(query_vector, top_k=5)  ← cosine-like L2 nearest-neighbour\n"
        "  3. Return top-5 chunks ranked by similarity score\n"
        "  4. Chunks are concatenated and passed as \"RUNBOOK GUIDANCE\" in the LLM prompt",
        S,
    ))

    # ══════════════════════════════════════════════════════════
    # SECTION 6 — MCP GATEWAY
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("6.  MCP Gateway  (The Tool Bus)", S["h1"]))
    story.append(Paragraph(
        "Every external call — Splunk, Jira, ServiceNow, Slack, On-Call — goes through "
        "<b>MCPGateway.call_tool(name, params)</b>. Agents never make HTTP calls directly. "
        "This is the <b>Model Context Protocol</b> pattern: a registry of named, typed tools "
        "with JSON schemas, making it trivial to swap mock services for real ones.",
        S["body"],
    ))

    tool_data = [
        ["Tool Name", "Routes To", "Used By"],
        ["search_logs",                 "Splunk /api/logs/search",           "LogAnalyzerAgent"],
        ["get_log_trends",              "Splunk /api/logs/trends",           "PredictiveMonitorAgent"],
        ["search_past_incidents",       "Jira /api/incidents/search",        "PastTicketAgent"],
        ["search_servicenow_incidents", "ServiceNow /api/incidents/search",  "PastTicketAgent"],
        ["get_incident_details",        "ServiceNow /api/incidents/{id}",    "PastTicketAgent"],
        ["create_incident_ticket",      "ServiceNow POST /api/incidents",    "available for future use"],
        ["post_slack_report",           "Slack /api/slack/post",             "report_node"],
        ["get_oncall_engineer",         "On-Call /api/oncall/current",       "report_node"],
        ["page_oncall_engineer",        "On-Call /api/oncall/page",          "report_node (P1 auto-page)"],
    ]
    tt = Table(tool_data, colWidths=[5.5*cm, 5.5*cm, 5.2*cm])
    tt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BG, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tt)
    story.append(Spacer(1, 0.2*cm))

    # ══════════════════════════════════════════════════════════
    # SECTION 7 — WEBSOCKET REAL-TIME EVENTS
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("7.  WebSocket Real-Time Event Flow", S["h1"]))
    story.append(Paragraph(
        "The React UI maintains a persistent WebSocket connection to "
        "<b>ws://localhost:8000/ws</b> with automatic 3-second reconnection. "
        "The backend broadcasts the following event types:",
        S["body"],
    ))

    ws_data = [
        ["Event",                 "When fired",                                "UI reaction"],
        ["connected",             "Client connects",                           "Fetch full incident list"],
        ["new_alert",             "POST /alert received",                      "New incident card appears, selected"],
        ["incident_update",       "Each pipeline node completes",              "Progress bar, agent steps update"],
        ["prediction",            "PredictiveMonitor fires",                   "⚠️ prediction card appears"],
        ["post_mortem_complete",  "PostMortemAgent finishes",                  "Incident status → resolved"],
    ]
    wt = Table(ws_data, colWidths=[4.2*cm, 5.5*cm, 6.5*cm])
    wt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BG, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(wt)
    story.append(Spacer(1, 0.2*cm))

    # ══════════════════════════════════════════════════════════
    # SECTION 8 — SYSTEM PROMPTS & TOKEN OPTIMIZATION
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("8.  System Prompts &amp; Token Optimization", S["h1"]))

    story.append(Paragraph("8.1  What is a System Prompt?", S["h2"]))
    story.append(Paragraph(
        "A <b>system prompt</b> is the static instruction block sent to the LLM before any "
        "user content on every call. It defines the model's persona, output contract, task "
        "scope, and constraints. It never changes between requests — only the "
        "<b>user message</b> (HumanMessage) changes with each incident's live data.",
        S["body"],
    ))
    story.append(code_block(
        "messages = [\n"
        "    SystemMessage(content='You are a principal SRE...')  # static every call\n"
        "    HumanMessage(content='Alert: DB_TIMEOUT | Logs: ...')  # dynamic per incident\n"
        "]",
        S,
    ))
    story.append(Paragraph(
        "Because the system prompt is <b>repeated on every LLM call</b>, keeping it concise "
        "directly reduces cost and latency. Each unnecessary word in a system prompt is "
        "billed on every single triage.",
        S["note"],
    ))

    story.append(Paragraph("8.2  System Prompts in This Project", S["h2"]))
    story.append(Paragraph(
        "Every agent has its own system prompt defining a different specialist role:",
        S["body"],
    ))
    sp_data = [
        ["Agent", "Persona defined", "Output format"],
        ["LogAnalyzerAgent",  "Expert SRE log analyst",             "JSON — error spikes, exceptions, latency"],
        ["PastTicketAgent",   "Incident management specialist",     "JSON — ranked_incidents + open_tickets"],
        ["RunbookAgent",      "Senior SRE runbook specialist",      "Plain text — 4 markdown sections"],
        ["RootCauseAgent",    "Principal SRE / incident commander", "JSON — hypotheses + checklist + escalation"],
        ["PostMortemAgent",   "Senior SRE post-mortem writer",      "JSON — full post-mortem document"],
    ]
    sp_table = Table(sp_data, colWidths=[4.2*cm, 5.5*cm, 6.5*cm])
    sp_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BG, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(sp_table)
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("8.3  Token Optimization — Before vs After", S["h2"]))
    story.append(Paragraph(
        "Six optimizations were applied. The table below shows the measured token "
        "reduction per agent:",
        S["body"],
    ))
    tok_data = [
        ["Agent", "Sys tokens before", "Sys tokens after", "Saved", "max_tokens before", "max_tokens after"],
        ["LogAnalyzerAgent",  "186",  "102",  "-84",  "1500", "1000"],
        ["PastTicketAgent",   "197",  "114",  "-83",  "2500", "1500"],
        ["RunbookAgent",      "130",  "54",   "-76",  "1500", "1000"],
        ["RootCauseAgent",    "379",  "144",  "-235", "3000", "2000"],
        ["PostMortemAgent",   "206",  "162",  "-44",  "2500", "2000"],
        ["TOTAL",             "1098", "576",  "-522", "11500","8500"],
    ]
    tok_table = Table(tok_data, colWidths=[3.8*cm, 3*cm, 3*cm, 2*cm, 3.3*cm, 3.1*cm])
    tok_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),  DARK_BG),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0),  (-1, 0),  "Helvetica-Bold"),
        ("BACKGROUND",    (0, -1), (-1, -1), colors.HexColor("#0F172A")),
        ("TEXTCOLOR",     (0, -1), (-1, -1), GREEN),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0),  (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1),  (-1, -2), [LIGHT_BG, WHITE]),
        ("GRID",          (0, 0),  (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0),  (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 5),
        ("LEFTPADDING",   (0, 0),  (-1, -1), 7),
        ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0),  (-1, -1), "CENTER"),
    ]))
    story.append(tok_table)
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("8.4  The 6 Optimization Techniques", S["h2"]))

    opt_data = [
        ["Technique", "What changed", "Token saving"],
        ["1. Trim log payload",
         "LogAnalyzerAgent capped at top 30 log entries (FATAL→ERROR→WARN priority). "
         "Heavy fields (trace_id, region) stripped per entry.",
         "~8,139 tokens (79% reduction on a typical 116-entry payload)"],
        ["2. Compact system prompts",
         "Removed tutorial prose and numbered lists that GPT-4o already knows. "
         "Kept: role statement + output JSON schema only.",
         "-522 system-prompt tokens across all 5 agents"],
        ["3. Singleton LLM clients",
         "@lru_cache(maxsize=1) factory per agent. One AzureChatOpenAI client "
         "shared across all requests instead of instantiating per call.",
         "No token saving — eliminates HTTP client cold-start latency"],
        ["4. Lower max_tokens caps",
         "Measured actual output sizes, then set caps to match: "
         "1000 for structured summaries, 1500–2000 for complex JSON.",
         "-3,500 output token budget per triage (5 agents combined)"],
        ["5. Slim ticket payloads",
         "PastTicketAgent strips heavy fields (comments arrays, internal notes) "
         "before sending tickets to the LLM for ranking.",
         "Varies — removes ~30–60% of per-ticket payload size"],
        ["6. Cap chained context",
         "RootCauseAgent receives outputs of 3 upstream agents. Log findings "
         "capped at 2,000 chars, runbook context at 1,500 chars before forwarding.",
         "Prevents upstream verbosity from compounding into the synthesis call"],
    ]
    opt_table = Table(opt_data, colWidths=[3.5*cm, 8.0*cm, 4.7*cm])
    opt_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BG, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(opt_table)
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("8.5  Measured Results  (live test — 5 incidents)", S["h2"]))
    res_data = [
        ["Metric", "Before", "After", "Improvement"],
        ["Triage time per incident",   "90–120 s",       "21–47 s",        "~60% faster"],
        ["Log payload tokens",         "~10,300",         "~2,162",          "-79%  (8,139 saved)"],
        ["System prompt tokens",       "1,098",           "576",             "-47%  (522 saved)"],
        ["max_tokens budget (5 agents)","11,500",         "8,000",           "-3,500 tokens"],
        ["Input tokens saved per incident", "—",          "~8,661",          ""],
        ["Input tokens saved per 5-run",    "—",          "~43,305",         ""],
        ["Output quality (5/5 incidents)",  "Full output", "Full output",    "No regression"],
    ]
    res_table = Table(res_data, colWidths=[5.5*cm, 3.3*cm, 3.3*cm, 4.1*cm])
    res_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BG, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR",     (3, 1), (3, -1),  GREEN),
        ("FONTNAME",      (3, 1), (3, -1),  "Helvetica-Bold"),
    ]))
    story.append(res_table)
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "The speed improvement comes from both smaller inputs (less prompt context to process) "
        "and lower max_tokens caps (model stops generating sooner). "
        "Output quality is fully preserved — all 5 incidents produced complete "
        "root-cause hypotheses, remediation checklists, escalation decisions, "
        "on-call paging, and Slack posts.",
        S["note"],
    ))

    # ══════════════════════════════════════════════════════════
    # SECTION 9 — END-TO-END SUMMARY
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("9.  End-to-End Summary", S["h1"]))

    summary_data = [
        ["Path", "In one sentence"],
        ["Reactive triage",
         "Alert in → 3 agents gather evidence in parallel (Splunk + Jira/ServiceNow + RAG) "
         "→ Azure OpenAI synthesises ranked root causes → auto-pages on-call engineer "
         "→ posts to Slack → all streamed live to UI via WebSocket."],
        ["Predictive monitoring",
         "Background loop polls Splunk trend data every N seconds → 3 statistical thresholds "
         "detect anomalies → predictions pushed to UI before the incident actually fires."],
        ["RAG knowledge base",
         "Runbook documents pre-embedded into FAISS at startup → semantically searched at "
         "triage time → top-5 relevant chunks injected into the LLM reasoning prompt."],
        ["MCP Gateway",
         "Single tool-call bus between agents and all external systems — "
         "9 registered tools, all swappable for real services without changing agent code."],
    ]
    st = Table(summary_data, colWidths=[3.8*cm, 12.4*cm])
    st.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BG, WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(st)
    story.append(Spacer(1, 0.4*cm))
    story.append(hr(ACCENT, 1))
    story.append(Paragraph(
        "Generated from the incident-triage-agent source code  ·  2026  ·  Includes token optimization results",
        S["body_small"],
    ))

    # ── Build PDF ─────────────────────────────────────────────
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
        title="Incident Triage Agent — Architecture & Flow",
        author="Incident Triage Agent",
    )
    doc.build(story)
    print(f"PDF written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_doc()
