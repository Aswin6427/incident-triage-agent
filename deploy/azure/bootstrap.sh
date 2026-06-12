#!/usr/bin/env bash
# ============================================================
#  One-time Azure setup for the Incident Triage Agent on
#  Azure Container Apps. Run from Azure Cloud Shell (recommended)
#  or any shell with `az` logged in (`az login`).
#
#  It:
#    1. ensures the resource group exists
#    2. creates an Entra app registration + GitHub OIDC federated
#       credential and grants it Contributor on the resource group
#    3. deploys deploy/azure/main.bicep (ACR, ACA env, Key Vault,
#       identity, the 7 apps + index-build job)
#    4. prints the GitHub repo secrets/variables to configure
#
#  Required env vars (export before running — these are secrets):
#    AZURE_OPENAI_API_KEY   the Azure OpenAI key
#    DATABASE_URL           postgresql+psycopg://user:pwd@host:5432/db?sslmode=require
#
#  The signed-in principal needs Owner (or Contributor + User Access
#  Administrator) on the resource group: this script creates role
#  assignments (GitHub SP, managed identity, Key Vault data-plane).
# ============================================================
set -euo pipefail

# ── Edit these ───────────────────────────────────────────────
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-triage}"
LOCATION="${LOCATION:-eastus}"
GITHUB_OWNER="${GITHUB_OWNER:-Aswin6427}"
GITHUB_REPO="${GITHUB_REPO:-incident-triage-agent}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"
APP_REG_NAME="${APP_REG_NAME:-triage-github-oidc}"
# ─────────────────────────────────────────────────────────────

: "${AZURE_OPENAI_API_KEY:?export AZURE_OPENAI_API_KEY before running}"
: "${DATABASE_URL:?export DATABASE_URL before running}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUB_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"

echo ">> Subscription: $SUB_ID   RG: $RESOURCE_GROUP   Region: $LOCATION"
az group create -n "$RESOURCE_GROUP" -l "$LOCATION" >/dev/null

# ── 1. GitHub OIDC app registration + federated credential ───
echo ">> Creating Entra app registration '$APP_REG_NAME' for GitHub OIDC..."
APP_ID="$(az ad app list --display-name "$APP_REG_NAME" --query '[0].appId' -o tsv)"
if [ -z "$APP_ID" ]; then
  APP_ID="$(az ad app create --display-name "$APP_REG_NAME" --query appId -o tsv)"
fi
# Service principal for the app (idempotent)
az ad sp create --id "$APP_ID" >/dev/null 2>&1 || true

echo ">> Adding federated credential (repo:${GITHUB_OWNER}/${GITHUB_REPO}, branch ${GITHUB_BRANCH})..."
az ad app federated-credential create --id "$APP_ID" --parameters "{
  \"name\": \"github-${GITHUB_BRANCH}\",
  \"issuer\": \"https://token.actions.githubusercontent.com\",
  \"subject\": \"repo:${GITHUB_OWNER}/${GITHUB_REPO}:ref:refs/heads/${GITHUB_BRANCH}\",
  \"audiences\": [\"api://AzureADTokenExchange\"]
}" 2>/dev/null || echo "   (federated credential already exists)"

echo ">> Granting the app Contributor on the resource group..."
az role assignment create \
  --assignee "$APP_ID" \
  --role Contributor \
  --scope "/subscriptions/${SUB_ID}/resourceGroups/${RESOURCE_GROUP}" >/dev/null 2>&1 || true

# ── 2. Deploy the infrastructure ─────────────────────────────
echo ">> Deploying main.bicep (this provisions ACR, ACA env, Key Vault, identity, apps, job)..."
DEPLOY_OUT="$(az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "${SCRIPT_DIR}/main.bicep" \
  --parameters "@${SCRIPT_DIR}/main.parameters.json" \
  --parameters azureOpenAiApiKey="$AZURE_OPENAI_API_KEY" databaseUrl="$DATABASE_URL" \
  --query properties.outputs -o json)"

ACR_NAME="$(echo "$DEPLOY_OUT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["acrName"]["value"])')"
FRONTEND_URL="$(echo "$DEPLOY_OUT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["frontendUrl"]["value"])')"

cat <<EOF

============================================================
 Bootstrap complete.

 Configure these in GitHub → Settings → Secrets and variables → Actions:

   Repository SECRETS:
     AZURE_CLIENT_ID        = ${APP_ID}
     AZURE_TENANT_ID        = ${TENANT_ID}
     AZURE_SUBSCRIPTION_ID  = ${SUB_ID}

   Repository VARIABLES:
     AZURE_RESOURCE_GROUP   = ${RESOURCE_GROUP}
     ACR_NAME               = ${ACR_NAME}

 Then push to '${GITHUB_BRANCH}' (or run the 'deploy' workflow manually).
 The first run builds the real images and rolls them onto the apps
 (the initial deploy used a placeholder image).

 After images are built, populate the pgvector index by starting the job:
   az containerapp job start -g ${RESOURCE_GROUP} -n triage-index-build

 Frontend URL (live once the real frontend image is deployed):
   ${FRONTEND_URL}
============================================================
EOF
