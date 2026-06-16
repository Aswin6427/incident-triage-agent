# Interview / Client Prep — Incident Triage Agent

A one-stop cheat sheet. **Every answer is anchored to this project** — a multi-agent,
RAG-powered incident-triage system, originally built on GCP/Vertex AI and migrated to
Azure (Azure OpenAI + Azure Postgres/pgvector + Azure Container Apps).

> **Golden rule for the interview:** state the concept, then say *"…and here's how I did it in my project."*
> Your strongest asset is one lived end-to-end system: multi-agent orchestration + RAG + MCP gateway +
> full Azure deployment + a real Vertex→Azure migration + real prod bugs fixed (cold-start, ACA 426).

---

## 0. The project in 60 seconds (your anchor)

An **autonomous incident-triage agent**: a monitoring alert fires → agents gather evidence from
logs, ticketing, and runbooks **in parallel** → an LLM synthesizes a ranked root cause +
remediation → it pages on-call and posts to Slack → a human only confirms resolution. It also
**predicts** incidents before they fire.

**Architecture (one diagram):**
```
React UI ──(REST + WebSocket)──► FastAPI backend ──► LangGraph DAG
                                       │                ingest → [LogAnalyzer ∥ PastTicket ∥ Runbook] → RootCause → report
                                       │  (all tool calls go through ONE MCP Gateway)
                                       ├─► Splunk / Jira / ServiceNow / Slack / On-Call (mock services)
                                       ├─► Azure OpenAI        (gpt-4o + text-embedding-3-small)
                                       └─► Azure PostgreSQL    (pgvector: runbook + incident knowledge)
Deployed on Azure Container Apps · images in ACR · secrets in Key Vault · IaC in Bicep
```

**Stack:** Python · FastAPI · LangChain · LangGraph · Azure OpenAI · pgvector · React/TypeScript ·
Azure Container Apps · Bicep · GitHub Actions.

**Agent count:** 6 agents (LogAnalyzer, PastTicket, Runbook, RootCause + background
PredictiveMonitor + PostMortem); **3 run in parallel** (fan-out/fan-in).

---

## 1. GenAI & LLM fundamentals

### Setting the system context to a pretrained model
You steer at **inference time**, not by retraining — via the **system prompt** (`system` role): persona,
task, constraints, and an **output contract**. In the project each agent has a focused `SystemMessage`
(e.g. RootCauseAgent: *"You are a principal SRE… return ONLY valid JSON with this schema"*); per-incident
data goes in as the `HumanMessage`. Layers from cheapest → most involved: **(1) system prompt + output
schema → (2) few-shot examples → (3) RAG (dynamic knowledge) → (4) tool definitions → (5) fine-tuning.**
I use 1–4; fine-tuning is rarely needed for well-scoped agents.

### Making responses deterministic (temperature)
`temperature` controls sampling randomness. **temperature = 0** ≈ greedy decoding → near-identical output
for the same input. **Every agent in the project runs at `temperature=0`** because they emit **structured
JSON** (hypotheses, checklists) that must be consistent and parseable. Paired with tight `max_tokens` and a
strict "JSON only" prompt + a fallback parser. (Caveat: 0 is *near*-deterministic, not 100% — backend
batching/float math can still vary slightly. Raise temperature only when you *want* variety.)

### Vertex AI vs GPT
Category mismatch: **Vertex AI is a *platform*** (GCP's managed ML — Model Garden incl. Gemini, endpoints,
training, vector search; auth via ADC/service account, keyless). **GPT is a *model family*** (OpenAI,
served via OpenAI or **Azure OpenAI**). Fair comparison = **Gemini-on-Vertex vs GPT-on-Azure-OpenAI**.
Differences: auth (ADC vs API key/managed identity), model family, and cloud ecosystem. **I built on
Vertex (Gemini + text-embedding-004) then migrated to Azure OpenAI (gpt-4o + text-embedding-3-small)** —
mostly swapping LangChain client classes + auth, agent logic unchanged.

---

## 2. RAG & Vectorization

### Vectorization
Converting text → high-dimensional **embeddings** that capture meaning, so similarity = math. Project:
runbooks + past incidents → ~400-word overlapping chunks → embed with Azure OpenAI
`text-embedding-3-small` (**1536-dim**) → store in **pgvector** → at query time embed the alert and run
**cosine similarity** for top-5 chunks. *Query and documents must use the same embedding model.*

### RAG implementation (two phases)
- **Ingestion (offline job):** load → chunk → embed → upsert into pgvector (`incident_triage_kb`) via
  `langchain-postgres` PGVector.
- **Query (per incident):** embed query → `similarity_search_with_score(k=5)` → inject chunks into the
  prompt as "RUNBOOK GUIDANCE" → GPT-4o reasons grounded on real procedures.
- **Closing the loop:** PostMortemAgent embeds resolved-incident learnings back into the store.

### MongoDB vs PostgreSQL for vectors
| | When to use |
|---|---|
| **PostgreSQL + pgvector** (used here) | Relational/transactional data; want vectors *with* structured data in one store, SQL joins, one backup. |
| **MongoDB Atlas Vector Search** | Document/flexible-schema data; `$vectorSearch`, vectors as a field. |
Rule: relational → pgvector; document → Mongo Atlas.

### Reducing chunking/embedding cost
1. **Embed once, persist** — biggest win: I moved embedding from app-startup into a **one-off job** that
   writes to pgvector; the app only *reads*.
2. **Re-embed only deltas** — incremental upserts on KB change; hash/dedupe chunks.
3. **Right-size chunks** — larger chunks + sensible overlap = fewer vectors (trade vs retrieval precision);
   trim boilerplate before embedding.
4. **Cheaper model / fewer dims** — `text-embedding-3-small` over -large.
5. **Batch** embedding requests.

### Database selection by scenario (quick reference)
| Need | Pick |
|---|---|
| Vectors + relational data, transactions | **PostgreSQL + pgvector** |
| Vectors + flexible documents | **MongoDB Atlas Vector Search** |
| Managed hybrid (keyword + vector) search & ranking | **Azure AI Search** |
| Low-latency cache / sessions / pub-sub | **Redis** |
| Time-series metrics | InfluxDB / Timescale |
| Structured OLTP, source of truth | PostgreSQL / SQL Server |

---

## 3. Agentic AI & Orchestration

### Agentic AI — real use case
The project itself: agents that **decide and act through tools** (not just answer) — gather evidence, page
on-call, post to Slack, predict incidents. Agentic = LLM + tools + control flow + autonomy with a
human-in-the-loop checkpoint.

### LangChain vs LangGraph
- **LangChain = the toolbox:** model clients (`AzureChatOpenAI`, `AzureOpenAIEmbeddings`), the PGVector
  store, message types. Gives provider-independence (the Vertex→Azure swap touched only these).
- **LangGraph = the control flow:** a state-machine DAG; each node is an agent reading/writing shared
  state. Project graph is **fan-out/fan-in**: `ingest → [3 agents in parallel] → RootCause → report`;
  `astream()` streams node completions to the UI over WebSocket. Chains are linear — LangGraph adds
  parallelism, branching, shared state, and observability.

### Memory in LangGraph (how it's saved)
- **Short-term (thread state):** the shared state between nodes, persisted by a **checkpointer**
  (`graph.compile(checkpointer=...)` + a `thread_id`); backends = `MemorySaver` (in-proc) or durable
  **`PostgresSaver`/`SqliteSaver`** → enables resume / time-travel / crash recovery.
- **Long-term:** a `Store` for facts across threads.
- **In the project:** per-run state is an in-memory `IncidentState`; **long-term memory = pgvector**
  (PostMortemAgent writes learnings back). Adding `PostgresSaver` is what would make triages
  crash-resilient and let the backend scale beyond one replica.

### MCP (Model Context Protocol) / server
A standard for exposing **tools, resources, prompts** to an agent through a uniform interface. Project
implements the **MCP pattern via a Gateway**: `MCPGateway.call_tool(name, params)` is the *only* path to the
outside world — a registry of **9 typed tools** with JSON schemas. Agents never make raw HTTP calls.
Benefits: **swappability** (mocks → real services, no agent change), a **single choke point** for auth /
audit / rate-limit / **PII redaction**, and **standardization** (a true MCP *server* exposes the same tools
over the protocol to any MCP client). *Mine is an MCP-style internal gateway; a full server exposes it over
the MCP transport.*

---

## 4. Azure / Cloud

### Azure OpenAI Service
OpenAI models (GPT-4o, embeddings) inside **your tenant**: prompts **not used for training**, in-region,
private-network capable. Key concepts: **deployments** (named model instance — called by deployment name,
not model name), pinned **api-version**, built-in **content filters**, auth via key (in Key Vault) or
**managed identity**. Project calls it via `AzureChatOpenAI`/`AzureOpenAIEmbeddings`.

### Azure AI Services (formerly Cognitive Services)
Composable pre-built AI:
- **Document Intelligence** — OCR/layout/forms (the file-parser use case).
- **AI Language** — entities, **PII detection/redaction**, summarization.
- **AI Search** — vector + hybrid search (RAG alternative to pgvector).
- **Vision / Speech / Translator**.
Insight: **Azure OpenAI = reasoning brain; AI Services = specialized perception/extraction.** Real
solutions combine them (Document Intelligence extracts → GPT-4o reasons → AI Language redacts PII).

### End-to-end LLM enablement (Azure or GCP — same shape)
1. **Provision AI service** — Azure OpenAI resource; create chat + embedding **deployments** (GCP: Vertex AI).
2. **Enable RAG** — embed KB → store in pgvector / Azure AI Search (GCP: AlloyDB-pgvector / Vertex Vector Search).
3. **Expose API** — FastAPI (`POST /alert`, `GET /incidents/{id}`, `WS /ws`).
4. **Deploy & consume** — containerize → ACR → **Azure Container Apps**; frontend consumes the API
   (GCP: Cloud Run). Secrets in Key Vault via managed identity.

### Security + restricting models ("model rules")
- **Network:** backend + data services on **internal-only** ingress; only frontend public; Postgres firewalled.
- **Secrets/identity:** keys in **Key Vault**, read via **managed identity** (keyless); scoped RBAC.
- **Data:** minimize (trim logs/tickets), redact at the MCP boundary, in-region model.
- **Restrict to GPT only:** (1) **Azure Policy** limits which model deployments can be created + RBAC on who
  can deploy; (2) **app-level allowlist** pins the deployment name (`gpt-4o`); (3) **content filters**.

### Autoscaling
ACA uses **KEDA**: `min`/`max` replicas, scale rules (HTTP/CPU/queue), **scale-to-zero**. Project is
**asymmetric**: stateless mocks + frontend scale **0→1**; **backend pinned to 1** (in-memory state +
WebSocket + background loop → *can't* scale horizontally). **Key point: autoscaling needs statelessness** —
externalize state to Postgres/Redis (+ LangGraph PostgresSaver) to let the backend scale out.

### Observability — CloudWatch and equivalents
**AWS CloudWatch** = logs + metrics + alarms + dashboards. **Azure** equivalent = **Azure Monitor**
(**Log Analytics** + KQL, **Application Insights** tracing). **GCP** = Cloud Logging + Monitoring. Project
wires ACA → Log Analytics; I debugged cold-start + the 426 issue via `az containerapp logs show`.

---

## 5. Engineering

### Python FastAPI
Async (ASGI) framework, Pydantic validation, auto OpenAPI docs. In project: `async def` routes for I/O-bound
LLM calls; **Pydantic** `AlertPayload` (auto 422 on bad input, enums for severity/type); **`BackgroundTasks`**
→ `POST /alert` returns **202** immediately and runs triage in the background; **WebSocket** `/ws` for live
updates; **`lifespan`** starts the predictive-monitor loop; **`pydantic-settings`** for config; served by
**Uvicorn**, containerized. Be ready for: `Depends` (DI), sync-vs-async routes, `response_model`, middleware
(CORS), and *why 202 + background task for long work*.

### Kafka listener / pub-sub
Decouples producers from consumers via topics. **Kafka** = partitioned distributed log; a **consumer group**
reads with **offsets** (replay, at-least-once). Project: alerts arrive via `POST /alert` today; in
production make ingestion event-driven — publish alert events to **Kafka / Azure Event Hubs / GCP Pub-Sub**
and a **listener** consumes + triggers triage. Handle: consumer groups (scale/partition), offset commits,
**idempotency** (dedupe by `incident_id`), and a dead-letter path.

### Local DB vs external API — routing decision
Decide by **freshness, authority, latency, cost, availability**. **Local DB** for owned/stable/cacheable +
low latency; **external API** for live/authoritative data. Pattern: **cache-aside** (DB first, API on
miss/stale TTL, backfill). Project: RunbookAgent reads **local pgvector** (stable knowledge); logs/tickets/
on-call come from **external services** via the MCP gateway (live source-of-truth). The gateway is the place
to add caching + fallback.

### GitHub Copilot vs Claude Code
**Copilot** = inline autocomplete (boilerplate, stubs — "finish the line"). **Claude Code** = agentic,
multi-file, reasoning-heavy changes. On this project Claude Code did the **Vertex→Azure migration**, wrote
**Bicep** + the Cloud Shell deploy script, and **debugged a live ACA 426** (nginx HTTP/1.0 on proxy). Use:
give context, small verified steps, run tests, review the diff. *"Copilot for keystrokes, Claude Code for
changes that need to understand the system."*

### Programming languages (adapt to your résumé)
Demonstrated here: **Python** (backend, agents, RAG, async), **TypeScript/JavaScript** (React),
**SQL** (Postgres/pgvector), **Bash/PowerShell** (deploy), **Bicep** (IaC), Docker/YAML. *Add your
prior-project languages (Java, C#, Go, …).*

### Handling PII / PHI in agentic systems
Layered: **minimize** (trim what reaches the model — `_trim_logs`, `_slim_ticket`), **mask at the single
MCP egress** (regex/NER or Azure AI Language PII detection — fix in one place), **isolate** (Azure OpenAI:
no training on data, in-region; internal-only ingress; Key Vault + managed identity), **don't persist raw
sensitive data** (store references, scrub embeddings), **audit + human-in-the-loop** for sensitive actions.
Architecture already gives clean choke points (MCP gateway + single model provider).

---

## 6. Solutioning — multi-format file parser with Agentic AI

```
FastAPI (POST /parse, GET /jobs/{id}, WS)
 Ingestion ─► Detection/Router ─► Extraction (parallel) ─► Validate/Synthesize ─► Output
 (blob)       (file type +         specialist agents per     critic agent +         structured JSON
              Document Intelligence  doc type, temp=0,         schema + confidence    → DB / queue
              OCR/layout)            JSON-schema output)       → human-in-loop if low
 All external calls go through an MCP Gateway (OCR, storage, LLM, PII-redaction, DB).
 Orchestration: LangGraph · Compute: Azure Container Apps · Perception: Document Intelligence + AI Language
```
Talking points: **don't make the LLM do OCR** (Document Intelligence first); **router → specialist
extractors** (new type = new agent + schema, no rewrite); **structured outputs at temp 0**; **critic +
confidence + human review**; **MCP gateway** for swappable tools + PII redaction + audit; **start with one
file type end-to-end**, then expand. *Same pattern as the incident agent: detect → route → parallel
specialists → validate → structured output behind a tool gateway.*

---

## 7. GCP ↔ Azure mapping (you've used both)

| Concern | GCP (original) | Azure (current) |
|---|---|---|
| LLM + embeddings | Vertex AI (Gemini, text-embedding-004) | Azure OpenAI (gpt-4o, text-embedding-3-small) |
| Vector store | FAISS / AlloyDB-pgvector | Azure Postgres + pgvector |
| Compute | Cloud Run | Azure Container Apps |
| Registry | Artifact Registry | Azure Container Registry |
| Secrets | Secret Manager | Key Vault |
| Identity | Service account (ADC) | Managed Identity |
| CI/CD | Cloud Build | GitHub Actions |
| Logs/metrics | Cloud Logging/Monitoring | Azure Monitor (Log Analytics + App Insights) |
| Eventing | Pub/Sub | Event Hubs |

---

*Generated for interview prep — anchored to the incident-triage-agent project (GCP→Azure migration).*
