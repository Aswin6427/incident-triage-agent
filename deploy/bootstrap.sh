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
# Non-secret Azure OpenAI config injected into the backend at deploy time:
AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT:-https://YOUR-RESOURCE.openai.azure.com/}"
AZURE_OPENAI_DEPLOYMENT_NAME="${AZURE_OPENAI_DEPLOYMENT_NAME:-gpt-4o}"
AZURE_OPENAI_EMBEDDING_DEPLOYMENT="${AZURE_OPENAI_EMBEDDING_DEPLOYMENT:-text-embedding-3-small}"
AZURE_OPENAI_API_VERSION="${AZURE_OPENAI_API_VERSION:-2024-02-15-preview}"
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

echo ">> Creating secret 'azure-openai-key'..."
if ! gcloud secrets describe azure-openai-key >/dev/null 2>&1; then
  read -r -s -p "   Paste your Azure OpenAI API key: " AZ_KEY; echo
  printf '%s' "$AZ_KEY" | gcloud secrets create azure-openai-key \
    --replication-policy=automatic --data-file=-
else
  echo "   (already exists — to rotate: gcloud secrets versions add azure-openai-key --data-file=-)"
fi

echo ">> Granting runtime SA access to the secret..."
gcloud secrets add-iam-policy-binding azure-openai-key \
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
   --substitutions=_REGION=${REGION},_AR_REPO=${AR_REPO},_RUNTIME_SA=${RUNTIME_SA},_AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT},_AZURE_OPENAI_DEPLOYMENT_NAME=${AZURE_OPENAI_DEPLOYMENT_NAME},_AZURE_OPENAI_EMBEDDING_DEPLOYMENT=${AZURE_OPENAI_EMBEDDING_DEPLOYMENT},_AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION}

 Bootstrap complete. Push to main to run the pipeline, or run it
 manually now with:

 gcloud builds submit --config=cloudbuild.yaml \\
   --substitutions=SHORT_SHA=manual,_AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
============================================================
EOF
