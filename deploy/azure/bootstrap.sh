#!/usr/bin/env bash
# ============================================================
#  Provision the Incident Triage Agent infrastructure on Azure
#  Container Apps. Designed to run as a plain CONTRIBUTOR (no
#  Owner / User Access Administrator) — it creates NO role
#  assignments. Run from Azure Cloud Shell (recommended) or any
#  shell with `az` logged in (`az login`).
#
#  It deploys deploy/azure/main.bicep: ACR (admin creds), ACA
#  environment, Key Vault (access policies) + secrets, managed
#  identity, the 7 container apps (on a placeholder image) and
#  the index-build job. CI is not wired (GitHub OIDC needs an
#  admin) — build + deploy images manually afterwards (the
#  README and the printed next-steps show how).
#
#  Required env vars (export before running — these are secrets):
#    AZURE_OPENAI_API_KEY   the Azure OpenAI key
#    DATABASE_URL           postgresql+psycopg://user:pwd@host:5432/db?sslmode=require
# ============================================================
set -euo pipefail

# ── Edit these ───────────────────────────────────────────────
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-triage}"
LOCATION="${LOCATION:-eastus}"
# ─────────────────────────────────────────────────────────────

: "${AZURE_OPENAI_API_KEY:?export AZURE_OPENAI_API_KEY before running}"
: "${DATABASE_URL:?export DATABASE_URL before running}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ">> Subscription: $(az account show --query name -o tsv)"
# Use the resource group as-is if it already exists (honour its region);
# only create it when missing.
if az group show -n "$RESOURCE_GROUP" >/dev/null 2>&1; then
  LOCATION="$(az group show -n "$RESOURCE_GROUP" --query location -o tsv)"
  echo ">> Using existing resource group '$RESOURCE_GROUP' ($LOCATION)"
else
  echo ">> Creating resource group '$RESOURCE_GROUP' in $LOCATION"
  az group create -n "$RESOURCE_GROUP" -l "$LOCATION" >/dev/null
fi

echo ">> Validating Bicep..."
az bicep build -f "${SCRIPT_DIR}/main.bicep" --stdout >/dev/null && echo "   Bicep OK"

echo ">> Deploying infrastructure (ACR, ACA env, Key Vault, identity, apps, job)..."
DEPLOY_OUT="$(az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "${SCRIPT_DIR}/main.bicep" \
  --parameters "@${SCRIPT_DIR}/main.parameters.json" \
  --parameters azureOpenAiApiKey="$AZURE_OPENAI_API_KEY" databaseUrl="$DATABASE_URL" \
  --query properties.outputs -o json)"

get() { echo "$DEPLOY_OUT" | python3 -c "import sys,json;print(json.load(sys.stdin)['$1']['value'])"; }
ACR_NAME="$(get acrName)"
FRONTEND_URL="$(get frontendUrl)"

cat <<EOF

============================================================
 Infrastructure deployed. The 7 apps are running a PLACEHOLDER
 image until you build and push the real ones.

 Next — build images and roll them onto the apps (Contributor is
 enough; run from the repo root in Cloud Shell):

   ACR=${ACR_NAME}
   LOGIN_SERVER=\$(az acr show -n "\$ACR" --query loginServer -o tsv)

   # build both images server-side in ACR
   az acr build --registry "\$ACR" --image backend:v1  --file Dockerfile.backend .
   az acr build --registry "\$ACR" --image frontend:v1 --file frontend/Dockerfile frontend

   # roll the real images onto every app
   for app in triage-backend mock-jira mock-splunk mock-servicenow mock-slack mock-oncall; do
     az containerapp update -g ${RESOURCE_GROUP} -n "\$app" --image "\$LOGIN_SERVER/backend:v1"
   done
   az containerapp update     -g ${RESOURCE_GROUP} -n triage-frontend    --image "\$LOGIN_SERVER/frontend:v1"
   az containerapp job  update -g ${RESOURCE_GROUP} -n triage-index-build --image "\$LOGIN_SERVER/backend:v1"

   # populate the pgvector index
   az containerapp job start -g ${RESOURCE_GROUP} -n triage-index-build

 Frontend URL (live once the real frontend image is deployed):
   ${FRONTEND_URL}
============================================================
EOF
