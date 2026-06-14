#!/usr/bin/env bash
# ============================================================
#  Incident Triage Agent — ONE-SHOT Azure Container Apps deploy.
#
#  Designed to be run from a FRESH Azure Cloud Shell session (or
#  re-run any time to redeploy). Idempotent end to end:
#    provision infra (Bicep) -> build images (ACR) -> roll onto
#    all apps + job -> build the pgvector index -> warm the mocks.
#
#  Runs as a plain CONTRIBUTOR — no role assignments (ACR admin
#  creds + Key Vault access policies).
#
#  PREREQS — export these two secrets first:
#    export AZURE_OPENAI_API_KEY='<your Azure OpenAI key>'
#    export DATABASE_URL='postgresql+psycopg://user:pwd@host:5432/postgres?sslmode=require'
#
#  Optional overrides: RESOURCE_GROUP, LOCATION, REPO_URL, IMAGE_TAG
#
#  Usage from a fresh Cloud Shell:
#    export AZURE_OPENAI_API_KEY=... DATABASE_URL=...
#    git clone https://github.com/Aswin6427/incident-triage-agent.git
#    cd incident-triage-agent
#    bash deploy/azure/cloud-shell-deploy.sh
# ============================================================
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-GenAI_Mentorship_Group}"
LOCATION="${LOCATION:-eastus2}"
REPO_URL="${REPO_URL:-https://github.com/Aswin6427/incident-triage-agent.git}"
DEPLOYMENT_NAME="triage-infra"

: "${AZURE_OPENAI_API_KEY:?export AZURE_OPENAI_API_KEY before running}"
: "${DATABASE_URL:?export DATABASE_URL before running}"

# ── 0. Make sure we're in the repo (clone on a fresh session) ──
if [ ! -f deploy/azure/main.bicep ]; then
  if [ -d incident-triage-agent ] && [ -f incident-triage-agent/deploy/azure/main.bicep ]; then
    cd incident-triage-agent
  else
    echo ">> Cloning $REPO_URL"
    git clone "$REPO_URL"
    cd incident-triage-agent
  fi
fi
echo ">> Updating repo to latest main"
git pull --ff-only origin main || true

IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%s)}"
SD="deploy/azure"

# ── 1. Provision infrastructure (idempotent) ──
echo ">> [1/6] Provisioning infrastructure via Bicep..."
if az group show -n "$RESOURCE_GROUP" >/dev/null 2>&1; then
  LOCATION="$(az group show -n "$RESOURCE_GROUP" --query location -o tsv)"
  echo "   using existing resource group '$RESOURCE_GROUP' ($LOCATION)"
else
  echo "   creating resource group '$RESOURCE_GROUP' in $LOCATION"
  az group create -n "$RESOURCE_GROUP" -l "$LOCATION" >/dev/null
fi

az deployment group create \
  --name "$DEPLOYMENT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "$SD/main.bicep" \
  --parameters "@$SD/main.parameters.json" \
  --parameters azureOpenAiApiKey="$AZURE_OPENAI_API_KEY" databaseUrl="$DATABASE_URL" \
  -o none

out() { az deployment group show -g "$RESOURCE_GROUP" -n "$DEPLOYMENT_NAME" --query "properties.outputs.$1.value" -o tsv; }
ACR="$(out acrName)"
FRONTEND_URL="$(out frontendUrl)"
LOGIN_SERVER="$(az acr show -n "$ACR" --query loginServer -o tsv)"
echo "   ACR=$ACR  tag=$IMAGE_TAG"

# ── 2. Build images server-side in ACR ──
echo ">> [2/6] Building backend image..."
az acr build --registry "$ACR" --image "backend:$IMAGE_TAG"  --file Dockerfile.backend . -o none
echo ">> [3/6] Building frontend image..."
az acr build --registry "$ACR" --image "frontend:$IMAGE_TAG" --file frontend/Dockerfile frontend -o none

# ── 3. Roll the images onto every app + the job ──
echo ">> [4/6] Rolling images onto container apps..."
for app in triage-backend mock-jira mock-splunk mock-servicenow mock-slack mock-oncall; do
  az containerapp update -g "$RESOURCE_GROUP" -n "$app" --image "$LOGIN_SERVER/backend:$IMAGE_TAG" -o none
done
az containerapp update     -g "$RESOURCE_GROUP" -n triage-frontend    --image "$LOGIN_SERVER/frontend:$IMAGE_TAG" -o none
az containerapp job  update -g "$RESOURCE_GROUP" -n triage-index-build --image "$LOGIN_SERVER/backend:$IMAGE_TAG"  -o none

# ── 4. Build the pgvector index (runs inside Azure) ──
echo ">> [5/6] Starting index-build job (embeds knowledge base into pgvector)..."
az containerapp job start -g "$RESOURCE_GROUP" -n triage-index-build -o none || true

# ── 5. Warm the scale-to-zero mocks so the first demo triage is clean ──
echo ">> [6/6] Warming services (a throwaway triage wakes the mocks)..."
curl -s "$FRONTEND_URL/health" >/dev/null 2>&1 || true
curl -s -X POST "$FRONTEND_URL/alert" -H 'Content-Type: application/json' \
  -d '{"incident_id":"INC-WARMUP","service":"payment-service","alert_type":"DB_CONNECTION_TIMEOUT","severity":"P3"}' \
  >/dev/null 2>&1 || true

cat <<EOF

============================================================
 Deploy complete.

   Frontend URL : $FRONTEND_URL
   Image tag    : $IMAGE_TAG
   Resource grp : $RESOURCE_GROUP

 Mocks were just warmed (INC-WARMUP). Wait ~30s, then demo a real triage:

   curl -s -X POST "$FRONTEND_URL/alert" -H 'Content-Type: application/json' \\
     -d '{"incident_id":"INC-DEMO","service":"payment-service","alert_type":"DB_CONNECTION_TIMEOUT","severity":"P1","metrics":{"error_rate":"23%","latency_p99":"8200ms"}}'

 ...or just open $FRONTEND_URL in a browser and watch the live dashboard.
============================================================
EOF
