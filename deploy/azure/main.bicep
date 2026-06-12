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

// Built-in role definition IDs
var acrPullRoleId          = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var kvSecretsUserRoleId    = '4633458b-17de-408a-b874-0445c86b69e6'  // read secret values (runtime)
var kvSecretsOfficerRoleId = 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7'  // write secret values (deploy-time seed)

// ── Identity ───────────────────────────────────────────────
resource uami 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

// ── Container registry ─────────────────────────────────────
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, uami.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// ── Key Vault + secrets ────────────────────────────────────
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
  }
}

// The principal running this deployment must be able to WRITE secret values.
// On an RBAC-authorized vault that requires a data-plane role, not just
// Contributor — grant it here and seed the secrets only after it lands.
resource deployerSecretsOfficer 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, deployer().objectId, kvSecretsOfficerRoleId)
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsOfficerRoleId)
    principalId: deployer().objectId
    principalType: 'User'
  }
}

resource kvSecretOpenAi 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'azure-openai-api-key'
  properties: { value: azureOpenAiApiKey }
  dependsOn: [ deployerSecretsOfficer ]
}

resource kvSecretDbUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'database-url'
  properties: { value: databaseUrl }
  dependsOn: [ deployerSecretsOfficer ]
}

resource kvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, uami.id, kvSecretsUserRoleId)
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: uami.properties.principalId
    principalType: 'ServicePrincipal'
  }
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

// Shared bits for every app's registry + identity block
var registries = [
  { server: acr.properties.loginServer, identity: uami.id }
]
var identityBlock = {
  type: 'UserAssigned'
  userAssignedIdentities: { '${uami.id}': {} }
}

// KV-backed secrets block (backend + index job)
var secretBlock = [
  { name: 'azure-openai-api-key', keyVaultUrl: '${kv.properties.vaultUri}secrets/azure-openai-api-key', identity: uami.id }
  { name: 'database-url',         keyVaultUrl: '${kv.properties.vaultUri}secrets/database-url',          identity: uami.id }
]

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
      secrets: secretBlock
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
  dependsOn: [ acrPull, kvSecretsUser, kvSecretOpenAi, kvSecretDbUrl ]
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
  dependsOn: [ acrPull ]
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
  dependsOn: [ acrPull ]
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
      secrets: secretBlock
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
  dependsOn: [ acrPull, kvSecretsUser, kvSecretOpenAi, kvSecretDbUrl ]
}

// ── Outputs ────────────────────────────────────────────────
output acrLoginServer string = acr.properties.loginServer
output acrName string = acr.name
output keyVaultName string = kv.name
output managedIdentityClientId string = uami.properties.clientId
output backendInternalFqdn string = backendFqdn
output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output indexJobName string = indexJob.name
