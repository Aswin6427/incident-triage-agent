# Deployment — Azure Container Apps

The Incident Triage Agent runs on **Azure Container Apps (ACA)**: the frontend
(nginx) is public; the backend and the five mock services are internal-only and
reached through the frontend's reverse proxy. AI inference uses **Azure OpenAI**
and the RAG knowledge base lives in **Azure Database for PostgreSQL + pgvector**.

```
Internet ──▶ triage-frontend (external)         ACA environment "triage-env"
                 │  nginx reverse-proxy
                 ├─ /alert,/incidents,… ─▶ triage-backend (internal, 1 replica)
                 └─ /ws (WebSocket)      ─▶        │
                                                   ├─▶ mock-jira/splunk/servicenow/slack/oncall (internal)
                                                   ├─▶ Azure OpenAI (gpt-4o + embeddings)
                                                   └─▶ Azure Postgres (pgvector)
```

## Components

| Resource | Role |
|---|---|
| Azure Container Registry | backend + frontend images |
| ACA managed environment + Log Analytics | hosts the 7 apps, centralizes logs |
| User-assigned managed identity | keyless ACR pull + Key Vault secret read |
| Azure Key Vault | `azure-openai-api-key`, `database-url` secrets |
| `triage-backend` | FastAPI app — **internal** ingress, **single replica** (stateful: in-memory state + WebSocket + predictive-monitor loop), session affinity |
| `mock-*` (5) | same backend image, `APP_MODULE` selects the mock — internal ingress |
| `triage-frontend` | nginx SPA + reverse proxy — **external** ingress (port 8080) |
| `triage-index-build` | manual ACA Job: `python -m backend.rag.pipeline` (populates pgvector) |

Everything is defined in [`azure/main.bicep`](azure/main.bicep).

## First-time setup

Prerequisites: an Azure Postgres Flexible Server with the `vector` extension
enabled and a firewall rule allowing Azure services (see the project README),
and an Azure OpenAI resource with `gpt-4o` + `text-embedding-3-small` deployments.

1. From **Azure Cloud Shell** (or any shell with `az login`):
   ```bash
   export AZURE_OPENAI_API_KEY='<your key>'
   export DATABASE_URL='postgresql+psycopg://triageadmin:<pwd>@triage-pg-2226375.postgres.database.azure.com:5432/postgres?sslmode=require'
   export RESOURCE_GROUP=rg-triage GITHUB_OWNER=Aswin6427 GITHUB_REPO=incident-triage-agent
   bash deploy/azure/bootstrap.sh
   ```
   This creates the GitHub OIDC app registration, deploys all infrastructure via
   Bicep, and prints the GitHub secrets/variables to set.

2. In **GitHub → Settings → Secrets and variables → Actions**, add the printed
   secrets (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`) and
   variables (`AZURE_RESOURCE_GROUP`, `ACR_NAME`).

3. Push to `main` (or run the **deploy** workflow manually). The first run builds
   the real images in ACR and rolls them onto the apps (bootstrap initially used a
   placeholder image).

4. Populate the pgvector index once images exist:
   ```bash
   az containerapp job start -g rg-triage -n triage-index-build
   ```

## What runs on each push

`.github/workflows/deploy.yml`: **test → `az acr build` (backend + frontend) →
`az containerapp update`** for all 7 apps. Auth is GitHub OIDC (passwordless) —
no stored service-principal secret.

## AI auth & config

| Item | Where |
|------|-------|
| Azure OpenAI API key | Key Vault secret `azure-openai-api-key`, referenced by the backend + index job via the managed identity (`Key Vault Secrets User`) |
| `DATABASE_URL` (incl. PG password) | Key Vault secret `database-url`, same reference path |
| Endpoint / API version / deployment names / collection | non-secret env vars (Bicep params in `main.parameters.json`) |
| Mock service URLs | internal ACA FQDNs, set as backend env vars by Bicep |
| ACR pull | managed identity with `AcrPull` — no registry admin creds |

## Demo cost posture

Tuned for **very low usage** — minimize always-on compute:

| App | Replicas | Size (CPU / mem) | Always-on? |
|---|---|---|---|
| `triage-backend` | 1 → 1 | 0.5 / 1Gi | **Yes** (stateful) |
| `mock-*` (5) | **0** → 1 | 0.25 / 0.5Gi | No — scale to zero |
| `triage-frontend` | **0** → 1 | 0.25 / 0.5Gi | No — scale to zero |
| `triage-index-build` | job (on-demand) | 0.5 / 1Gi | No |

- Only the backend runs 24/7; the 5 mocks and frontend **scale to zero** when
  idle and wake on the first request (a few seconds cold start — fine for a demo,
  comfortably within the triage timeout).
- Fixed costs are small: **ACR Basic** (~$5/mo) and the always-on backend. ACA
  Consumption bills per vCPU/GiB-second with a monthly free grant; Key Vault and
  the capped Log Analytics workspace are negligible at demo volume.
- Your **Azure Postgres** (Burstable `B1ms`) and **Azure OpenAI** (pay-per-token)
  are billed separately — both already minimal.
- To pause spend entirely between demos: `az containerapp update -n triage-backend
  -g rg-triage --min-replicas 0 --max-replicas 0` (re-set to 1/1 before the next
  demo; note in-memory state resets on restart).

## Notes / hardening

- **Single backend replica** is required until in-memory state (incidents,
  predictions, post-mortems) and the WebSocket/predictive-monitor loop are moved
  to Postgres/Redis. Raising `maxReplicas` on `triage-backend` will break state.
- **Backend + mocks are internal** (not internet-facing); only the frontend is
  public. The browser talks only to the frontend, which proxies REST + WebSocket.
- **Postgres networking:** the demo relies on the "Allow Azure services" firewall
  rule. For production, put Postgres on a private endpoint and VNet-integrate the
  ACA environment.
- **Index builds** must run inside Azure (the `triage-index-build` job, or
  `python -m backend.rag.pipeline` from Cloud Shell). The backend no longer
  rebuilds the index on boot.
