#!/usr/bin/env bash
# ============================================================
#  One-time GCP setup for the Incident Triage Agent CI/CD.
#  Run once (e.g. in Cloud Shell). Safe to re-run — each step
#  is idempotent or tolerates "already exists".
# ============================================================
set -euo pipefail

# ── Edit these ───────────────────────────────────────────────
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-us-central1}"
AR_REPO="${AR_REPO:-triage}"
RUNTIME_SA="${RUNTIME_SA:-triage-run}"
GITHUB_OWNER="${GITHUB_OWNER:-your-github-username-or-org}"
GITHUB_REPO="${GITHUB_REPO:-incident-triage-agent}"
# Azure OpenAI config injected into the backend at deploy time.
# Endpoint + deployment names are plain env vars; the API key is stored in
# Secret Manager (created below) and mounted at runtime.
AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT:-https://your-resource.openai.azure.com/}"
AZURE_OPENAI_API_VERSION="${AZURE_OPENAI_API_VERSION:-2024-10-21}"
AZURE_OPENAI_CHAT_DEPLOYMENT="${AZURE_OPENAI_CHAT_DEPLOYMENT:-gpt-4o}"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT="${AZURE_OPENAI_EMBEDDING_DEPLOYMENT:-text-embedding-3-small}"
AZURE_OPENAI_KEY_SECRET="${AZURE_OPENAI_KEY_SECRET:-azure-openai-api-key}"
# Set AZURE_OPENAI_API_KEY in your shell before running to seed the secret.
AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY:-}"
# ─────────────────────────────────────────────────────────────

echo ">> Project: $PROJECT_ID   Region: $REGION"
gcloud config set project "$PROJECT_ID"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

echo ">> Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com

echo ">> Creating Artifact Registry repo '$AR_REPO'..."
gcloud artifacts repositories create "$AR_REPO" \
  --repository-format=docker --location="$REGION" \
  --description="Incident Triage images" 2>/dev/null || echo "   (already exists)"

echo ">> Creating runtime service account '$RUNTIME_SA'..."
gcloud iam service-accounts create "$RUNTIME_SA" \
  --display-name="Triage backend runtime" 2>/dev/null || echo "   (already exists)"
RUNTIME_SA_EMAIL="${RUNTIME_SA}@${PROJECT_ID}.iam.gserviceaccount.com"

echo ">> Creating Secret Manager secret '$AZURE_OPENAI_KEY_SECRET' for the Azure OpenAI API key..."
gcloud secrets create "$AZURE_OPENAI_KEY_SECRET" \
  --replication-policy=automatic 2>/dev/null || echo "   (already exists)"
if [ -n "$AZURE_OPENAI_API_KEY" ]; then
  printf '%s' "$AZURE_OPENAI_API_KEY" | gcloud secrets versions add "$AZURE_OPENAI_KEY_SECRET" --data-file=-
  echo "   (added a new secret version from \$AZURE_OPENAI_API_KEY)"
else
  echo "   NOTE: \$AZURE_OPENAI_API_KEY not set — add the key manually with:"
  echo "         printf '%s' '<your-key>' | gcloud secrets versions add $AZURE_OPENAI_KEY_SECRET --data-file=-"
fi

echo ">> Granting runtime SA access to the Azure OpenAI key secret..."
gcloud secrets add-iam-policy-binding "$AZURE_OPENAI_KEY_SECRET" \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role=roles/secretmanager.secretAccessor >/dev/null

# Cloud Build's default service account (used by GitHub-App triggers).
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
echo ">> Granting Cloud Build SA ($CB_SA) deploy permissions..."
for role in roles/run.admin roles/iam.serviceAccountUser \
            roles/artifactregistry.writer roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CB_SA}" --role="$role" >/dev/null
done
# Cloud Build must be able to "act as" the runtime SA to deploy the backend with it.
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA_EMAIL" \
  --member="serviceAccount:${CB_SA}" --role=roles/iam.serviceAccountUser >/dev/null

cat <<EOF

============================================================
 MANUAL STEP — connect GitHub (one time):
   Console > Cloud Build > Triggers > Connect Repository
   Install the "Google Cloud Build" GitHub App on:
     ${GITHUB_OWNER}/${GITHUB_REPO}
 Then create the push-to-main trigger:

 gcloud builds triggers create github \\
   --name=triage-main \\
   --repo-owner=${GITHUB_OWNER} \\
   --repo-name=${GITHUB_REPO} \\
   --branch-pattern='^main\$' \\
   --build-config=cloudbuild.yaml \\
   --substitutions=_REGION=${REGION},_AR_REPO=${AR_REPO},_RUNTIME_SA=${RUNTIME_SA},_AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT},_AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION},_AZURE_OPENAI_CHAT_DEPLOYMENT=${AZURE_OPENAI_CHAT_DEPLOYMENT},_AZURE_OPENAI_EMBEDDING_DEPLOYMENT=${AZURE_OPENAI_EMBEDDING_DEPLOYMENT},_AZURE_OPENAI_KEY_SECRET=${AZURE_OPENAI_KEY_SECRET}

 Bootstrap complete. Push to main to run the pipeline, or run it
 manually now with:

 gcloud builds submit --config=cloudbuild.yaml \\
   --substitutions=SHORT_SHA=manual,_AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
============================================================
EOF
