# CI/CD — Cloud Build → Cloud Run

Automated pipeline: **push to `main`** → Cloud Build runs tests, builds two
images, pushes them to Artifact Registry, and deploys 7 Cloud Run services.

## Architecture

```
                    ┌──────────────────────────────────────────┐
   GitHub (main) ──▶│ Cloud Build (cloudbuild.yaml)            │
        push        │  test → build → push → deploy            │
                    └──────────────────────────────────────────┘
                                     │
              Artifact Registry ◀────┘ (backend + frontend images)
                                     │ deploy
        ┌────────────────────────────┼─────────────────────────────┐
        ▼                            ▼                              ▼
  triage-frontend            triage-backend                 mock-jira / splunk /
  (nginx + SPA,              (1 instance, CPU-always-on,     servicenow / slack /
   proxies /ws + API)        session affinity, WebSocket)    oncall  (same image,
        │                            │                        APP_MODULE per svc)
   browser ◀── wss/https ────────────┘
```

- **One backend image** runs the backend and all 5 mocks; the `APP_MODULE` env
  var selects which FastAPI app starts (see `docker/backend-entrypoint.sh`).
- **One frontend image** (nginx) serves the Vite build and reverse-proxies the
  API + WebSocket to the backend, so the app is single-origin.
- Backend is pinned to **1 instance / no CPU throttling / session affinity**
  because it keeps incident state in memory, serves a WebSocket, and runs the
  background predictive-monitor task. Do not raise `--max-instances` without
  first moving that state to Memorystore/Firestore.

## First-time setup

1. Push this repo to GitHub (`main` branch).
2. In Cloud Shell (or any shell with `gcloud`):
   ```bash
   export PROJECT_ID=your-project GITHUB_OWNER=you GITHUB_REPO=incident-triage-agent
   export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   bash deploy/bootstrap.sh
   ```
   It enables APIs, creates the Artifact Registry repo, the runtime service
   account, the `azure-openai-key` secret, and grants IAM. It then prints the
   manual GitHub-connect step and the `triggers create` command.
3. Connect the repo + create the trigger as printed.

## What runs on each push

`cloudbuild.yaml` stages: `test → build-backend/-frontend → push → deploy-mocks
→ deploy-backend → deploy-frontend`. The backend is wired to the mock service
URLs and the Azure key (from Secret Manager) at deploy time; the frontend is
wired to the backend URL. The final log line prints the public frontend URL.

## Secrets & config

| Item | Where |
|------|-------|
| `AZURE_OPENAI_API_KEY` | Secret Manager `azure-openai-key` → injected via `--set-secrets` |
| Endpoint / deployment names / API version | trigger substitutions (`_AZURE_OPENAI_*`) |
| Mock service URLs | resolved at deploy time, set as backend env vars |

Rotate the key: `gcloud secrets versions add azure-openai-key --data-file=-`
then redeploy (push or re-run the trigger).

## Run the pipeline manually (without a push)

```bash
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=SHORT_SHA=manual,_AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

## Notes / hardening

- **CORS** in `backend/main.py` is `allow_origins=["*"]`. Lock it to the frontend
  URL for anything beyond a demo.
- **Mocks are public** (`--allow-unauthenticated`) so the backend can reach them
  simply. To lock down, make them internal and have the backend send ID tokens.
- **Custom domain / TLS:** map a domain to `triage-frontend` via
  `gcloud run domain-mappings create`, or front it with an HTTPS Load Balancer.
