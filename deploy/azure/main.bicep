// ============================================================
//  Incident Triage Agent — Azure Container Apps infrastructure
//
//  Provisions (in one deployment):
//    - Log Analytics workspace
//    - Azure Container Apps managed environment
//    - Azure Container Registry (ACR)
//    - User-assigned managed identity (ACR pull + Key Vault read)
//    - Key Vault (RBAC) + secrets (OpenAI key, DATABASE_URL)
//    - Role assignments: identity -> AcrPull, identity -> KV Secrets User
//    - 7 container apps:
//        triage-backend   (INTERNAL ingress, single replica, stateful)
//        mock-* x5        (INTERNAL ingress)
//        triage-frontend  (EXTERNAL ingress, nginx)
//    - triage-index-build (manual ACA Job: python -m backend.rag.pipeline)
//
//  Images default to a placeholder so the first deploy succeeds before CI
//  has built anything; the GitHub Actions workflow then updates each app to
//  the real ACR image. Pass real image refs to skip the placeholder.
// ============================================================

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Globally-unique ACR name.')
param acrName string = 'acr${uniqueString(resourceGroup().id)}'

@description('Backend container image (backend + mocks share this image).')
param backendImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Frontend (nginx) container image.')
param frontendImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

// ── Azure OpenAI (non-secret) ──────────────────────────────
param azureOpenAiEndpoint string
param azureOpenAiApiVersion string = '2024-10-21'
param azureOpenAiChatDeployment string = 'gpt-4o'
param azureOpenAiEmbeddingDeployment string = 'text-embedding-3-small'
param pgCollectionName string = 'incident_triage_kb'

// ── Secrets (provided at deploy time, never echoed) ────────
@secure()
param azureOpenAiApiKey string

@description('Full psycopg URL incl. password, e.g. postgresql+psycopg://user:pwd@host:5432/db?sslmode=require')
@secure()
param databaseUrl string

// ── Fixed names ────────────────────────────────────────────
var lawName     = 'log-triage'
var envName     = 'triage-env'
var kvName      = take('kv-triage-${uniqueString(resourceGroup().id)}', 24)
var identityName = 'triage-identity'

var mocks = [
  { name: 'mock-jira',       module: 'mocks.mock_jira:app' }
  { name: 'mock-splunk',     module: 'mocks.mock_splunk:app' }
  { name: 'mock-servicenow', module: 'mocks.mock_servicenow:app' }
  { name: 'mock-slack',      module: 'mocks.mock_slack:app' }
  { name: 'mock-oncall',     module: 'mocks.mock_oncall:app' }
]

// NOTE: This template avoids Azure role assignments entirely, so it can be
// deployed by a plain *Contributor* (no Owner / User Access Administrator).
//   - ACR pull uses the registry's ADMIN credentials (vault-stored password)
//     instead of an AcrPull role assignment.
//   - Key Vault uses ACCESS POLICIES (a vault property Contributor can set)
//     instead of RBAC role assignments. The managed identity still reads
//     secrets at runtime — just authorized by policy.

// ── Identity ───────────────────────────────────────────────
resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

// ── Container registry (admin creds → no AcrPull role needed) ──
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: true
  }
}

// ── Key Vault + secrets (access policies → no RBAC role needed) ──
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: false
    enableSoftDelete: true
    accessPolicies: [
      {
        // runtime: the managed identity reads secret values
        tenantId: subscription().tenantId
        objectId: uami.properties.principalId
        permissions: { secrets: [ 'get', 'list' ] }
      }
      {
        // deploy-time: the principal running the deployment seeds secrets
        tenantId: subscription().tenantId
        objectId: deployer().objectId
        permissions: { secrets: [ 'get', 'list', 'set' ] }
      }
    ]
  }
}

resource kvSecretOpenAi 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'azure-openai-api-key'
  properties: { value: azureOpenAiApiKey }
}

resource kvSecretDbUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'database-url'
  properties: { value: databaseUrl }
}

// ── Observability + ACA environment ────────────────────────
resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: lawName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30                 // minimum for the SKU
    workspaceCapping: { dailyQuotaGb: 1 } // demo cost guard against log spikes
  }
}

resource acaEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: envName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: law.listKeys().primarySharedKey
      }
    }
  }
}

// Internal-ingress apps get FQDN <app>.internal.<defaultDomain>; external get <app>.<defaultDomain>.
var envDomain   = acaEnv.properties.defaultDomain
var backendFqdn = 'triage-backend.internal.${envDomain}'

var identityBlock = {
  type: 'UserAssigned'
  userAssignedIdentities: { '${uami.id}': {} }
}

// Registry pull via ACR admin creds (password stored as an app secret).
var registries = [
  { server: acr.properties.loginServer, username: acr.listCredentials().username, passwordSecretRef: 'acr-password' }
]
var acrPasswordSecret = {
  name: 'acr-password'
  value: acr.listCredentials().passwords[0].value
}

// KV-backed secrets (backend + index job), resolved at runtime by the identity.
var kvSecrets = [
  { name: 'azure-openai-api-key', keyVaultUrl: '${kv.properties.vaultUri}secrets/azure-openai-api-key', identity: uami.id }
  { name: 'database-url',         keyVaultUrl: '${kv.properties.vaultUri}secrets/database-url',          identity: uami.id }
]
// Apps that need KV secrets carry both the KV refs and the ACR password.
var backendSecrets = concat(kvSecrets, [ acrPasswordSecret ])

// Non-secret env shared by backend + index job
var aiEnv = [
  { name: 'AZURE_OPENAI_ENDPOINT',             value: azureOpenAiEndpoint }
  { name: 'AZURE_OPENAI_API_VERSION',          value: azureOpenAiApiVersion }
  { name: 'AZURE_OPENAI_CHAT_DEPLOYMENT',      value: azureOpenAiChatDeployment }
  { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: azureOpenAiEmbeddingDeployment }
  { name: 'PG_COLLECTION_NAME',                value: pgCollectionName }
  { name: 'AZURE_OPENAI_API_KEY',              secretRef: 'azure-openai-api-key' }
  { name: 'DATABASE_URL',                      secretRef: 'database-url' }
]

// ── Backend (internal, stateful, single replica) ───────────
resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'triage-backend'
  location: location
  identity: identityBlock
  properties: {
    managedEnvironmentId: acaEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8000
        transport: 'auto'
        // Stateful: in-memory incidents + WebSocket + predictive-monitor loop.
        stickySessions: { affinity: 'sticky' }
      }
      registries: registries
      secrets: backendSecrets
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
          // Demo sizing: smallest ACA combo that comfortably runs the
          // LangGraph/langchain stack (mostly I/O-bound on Azure OpenAI).
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: concat(aiEnv, [
            { name: 'APP_MODULE',      value: 'main:app' }
            { name: 'MOCK_JIRA_URL',       value: 'https://mock-jira.internal.${envDomain}' }
            { name: 'MOCK_SPLUNK_URL',     value: 'https://mock-splunk.internal.${envDomain}' }
            { name: 'MOCK_SERVICENOW_URL', value: 'https://mock-servicenow.internal.${envDomain}' }
            { name: 'MOCK_SLACK_URL',      value: 'https://mock-slack.internal.${envDomain}' }
            { name: 'MOCK_ONCALL_URL',     value: 'https://mock-oncall.internal.${envDomain}' }
          ])
        }
      ]
      // The ONLY always-on app: MUST stay 1/1 (in-memory state + WebSocket +
      // predictive-monitor loop can't survive scale-to-zero or >1 replica).
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
  dependsOn: [ kvSecretOpenAi, kvSecretDbUrl ]
}

// ── Mock services (internal) ───────────────────────────────
resource mockApps 'Microsoft.App/containerApps@2024-03-01' = [for m in mocks: {
  name: m.name
  location: location
  identity: identityBlock
  properties: {
    managedEnvironmentId: acaEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8000
        transport: 'auto'
      }
      registries: registries
      secrets: [ acrPasswordSecret ]
    }
    template: {
      containers: [
        {
          name: 'mock'
          image: backendImage
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          env: [
            { name: 'APP_MODULE', value: m.module }
          ]
        }
      ]
      // Demo: scale to zero when idle; the backend's HTTP call wakes them
      // (a few seconds cold start, well within the triage timeout).
      scale: { minReplicas: 0, maxReplicas: 1 }
    }
  }
}]

// ── Frontend (external, nginx) ─────────────────────────────
resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'triage-frontend'
  location: location
  identity: identityBlock
  properties: {
    managedEnvironmentId: acaEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
      }
      registries: registries
      secrets: [ acrPasswordSecret ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          // nginx envsubst injects this into proxy_pass https://${BACKEND_HOST}
          env: [
            { name: 'BACKEND_HOST', value: backendFqdn }
          ]
        }
      ]
      // Demo: scale to zero; first visit after idle has a brief cold start.
      scale: { minReplicas: 0, maxReplicas: 1 }
    }
  }
}

// ── Index-build job (manual trigger): python -m backend.rag.pipeline ──
resource indexJob 'Microsoft.App/jobs@2024-03-01' = {
  name: 'triage-index-build'
  location: location
  identity: identityBlock
  properties: {
    environmentId: acaEnv.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 1800
      replicaRetryLimit: 1
      manualTriggerConfig: { parallelism: 1, replicaCompletionCount: 1 }
      registries: registries
      secrets: backendSecrets
    }
    template: {
      containers: [
        {
          name: 'index-build'
          image: backendImage
          command: [ 'python', '-m', 'backend.rag.pipeline' ]
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: aiEnv
        }
      ]
    }
  }
  dependsOn: [ kvSecretOpenAi, kvSecretDbUrl ]
}

// ── Outputs ────────────────────────────────────────────────
output acrLoginServer string = acr.properties.loginServer
output acrName string = acr.name
output keyVaultName string = kv.name
output managedIdentityClientId string = uami.properties.clientId
output backendInternalFqdn string = backendFqdn
output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output indexJobName string = indexJob.name
