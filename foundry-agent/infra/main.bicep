// Solution C — Microsoft Foundry hosted agent
// Resources:
//   - Microsoft Foundry account (CognitiveServices kind=AIServices) + two
//     projects (`hr-concierge` for the runtime agent, `hr-concierge-evals`
//     for the offline evaluation harness)
//   - Project-scoped connections wiring the runtime project to its BYO
//     dependencies (Cosmos for thread storage, AI Search for vector store,
//     Storage for file uploads, App Insights for traces, Speech for voice)
//   - Project capabilityHost (`agents-host`, kind=Agents) so the hosted
//     agent runtime knows which connections to use for thread / vector /
//     storage state
//   - Azure AI Search (used by Foundry File Search + capabilityHost)
//   - Storage account (BYO file storage for the agents runtime)
//   - Container Apps Environment + 1 app (FastAPI backend exposed as the
//     OpenAPI tool the hosted agent calls)
//   - Container Registry (UAMI pull only)
//   - Cosmos DB (agent thread metadata) — RBAC only, key auth disabled
//   - Application Insights, Log Analytics, Key Vault, user-assigned MI
//   - Optional voice/IVR layer (enableVoice=true): Azure AI Speech for
//     STT/TTS (wired to the Foundry project as a connection so the hosted
//     agent can mint AAD tokens) and Azure Communication Services for
//     PSTN inbound. This is the path used for telephony IVR; voice inside
//     Microsoft Teams and Microsoft 365 Copilot is handled by those hosts
//     when the agent is published there — no extra Azure resources are
//     required for the in-Teams / in-Copilot UI voice path.
//   - Role assignments so each project's MI can call Foundry, Search, Cosmos,
//     Storage, and Speech
//   - Diagnostic settings for chargeable resources
//
// The hosted agent itself is created by `az ml agent create` (or the Foundry
// portal) in the deploy workflow — Bicep doesn't model the agent directly.

targetScope = 'resourceGroup'

@description('Short prefix for resource names (3-8 chars).')
@minLength(3)
@maxLength(8)
param namePrefix string = 'hrfdy'

@description('Azure region.')
param location string = resourceGroup().location

@description('Microsoft Foundry model deployment used by the Foundry agent.')
param foundryDeployment string = 'gpt-4o'

@description('Provision voice/IVR resources (Azure AI Speech + Azure Communication Services).')
param enableVoice bool = true

@description('Data residency for Azure Communication Services (e.g., United States, Europe, Asia Pacific).')
param acsDataLocation string = 'United States'

@description('Tags applied to every resource.')
param tags object = {
  workload: 'hr-concierge'
  solution: 'foundry-agent'
  managedBy: 'bicep'
}

var uniq = uniqueString(resourceGroup().id, namePrefix)

// ───────────────────────── Observability ────────────────────────────────

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-law-${uniq}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${namePrefix}-ai-${uniq}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
  }
}

// ─────────────────────────── Identity & ACR ─────────────────────────────

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id-${uniq}'
  location: location
  tags: tags
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: replace('${namePrefix}acr${uniq}', '-', '')
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled' // demo only.
  }
}

var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, identity.id, acrPullRoleId)
  scope: acr
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
  }
}

resource acrDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: acr
  properties: {
    workspaceId: law.id
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

// ─────────────────────────── Key Vault ──────────────────────────────────

resource kv 'Microsoft.KeyVault/vaults@2024-04-01-preview' = {
  name: '${namePrefix}-kv-${uniq}'
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled' // demo only.
  }
}

// ───────────────────── Storage (agent file uploads) ─────────────────────

resource agentStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: replace('${namePrefix}st${uniq}', '-', '')
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled' // demo only.
    networkAcls: { defaultAction: 'Allow', bypass: 'AzureServices' }
    supportsHttpsTrafficOnly: true
  }
}

resource agentStorageDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: agentStorage
  properties: {
    workspaceId: law.id
    metrics: [ { category: 'Transaction', enabled: true } ]
  }
}

// ──────────────────────── Container Apps ────────────────────────────

resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-cae-${uniq}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: listKeys(law.id, '2023-09-01').primarySharedKey
      }
    }
  }
}

// ─────────────────────────── Cosmos DB ──────────────────────────────────

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: '${namePrefix}-cos-${uniq}'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [ { locationName: location, failoverPriority: 0 } ]
    capabilities: [ { name: 'EnableServerless' } ]
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled' // demo only.
    minimalTlsVersion: 'Tls12'
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'hr'
  properties: { resource: { id: 'hr' } }
}

resource cosmosContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: cosmosDb
  name: 'threads'
  properties: {
    resource: {
      id: 'threads'
      partitionKey: { paths: [ '/id' ], kind: 'Hash' }
    }
  }
}

resource cosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmos
  name: guid(cosmos.id, identity.id, 'data-contributor')
  properties: {
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    principalId: identity.properties.principalId
    scope: cosmos.id
  }
}

resource cosmosDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: cosmos
  properties: {
    workspaceId: law.id
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'Requests', enabled: true } ]
  }
}

// ─────────────────────────── AI Search ──────────────────────────────────

resource search 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: '${namePrefix}-srch-${uniq}'
  location: location
  tags: tags
  sku: { name: 'basic' }
  properties: {
    authOptions: { aadOrApiKey: { aadAuthFailureMode: 'http401WithBearerChallenge' } }
    disableLocalAuth: true
    publicNetworkAccess: 'enabled' // demo only.
  }
}

resource searchDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: search
  properties: {
    workspaceId: law.id
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

// ───────────────────────── Foundry account + project ────────────────────

resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${namePrefix}-fdy-${uniq}'
  location: location
  tags: tags
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    allowProjectManagement: true
    customSubDomainName: '${namePrefix}-fdy-${uniq}'
    publicNetworkAccess: 'Enabled' // demo only.
    disableLocalAuth: true
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: foundry
  name: 'hr-concierge'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: 'Contoso HR Concierge'
    description: 'Foundry project hosting the HR Concierge agent.'
  }
}

resource gpt 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: foundry
  name: foundryDeployment
  sku: { name: 'GlobalStandard', capacity: 30 }
  properties: { model: { format: 'OpenAI', name: 'gpt-4o', version: '2024-08-06' } }
}

resource foundryDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: foundry
  properties: {
    workspaceId: law.id
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

// Foundry project's MI → Foundry (Cognitive Services OpenAI User)
var foundryUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
resource foundryUserForProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, project.id, 'aoai-user')
  scope: foundry
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleId)
  }
}

// Foundry project's MI → Search (Search Index Data Reader)
var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
resource searchReaderForProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, project.id, 'search-reader')
  scope: search
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataReaderRoleId)
  }
}

// Foundry project's MI → Search (Search Service Contributor, for index management)
var searchServiceContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
resource searchContribForProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, project.id, 'search-contrib')
  scope: search
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
  }
}

// Foundry project's MI → Storage (Storage Blob Data Contributor)
var blobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
resource storageContribForProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(agentStorage.id, project.id, 'blob-contrib')
  scope: agentStorage
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobDataContributorRoleId)
  }
}

// Foundry project's MI → Cosmos (SQL data contributor) for agent thread storage
resource cosmosRoleAssignmentProject 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmos
  name: guid(cosmos.id, project.id, 'data-contributor')
  properties: {
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    principalId: project.identity.principalId
    scope: cosmos.id
  }
}

// ────────────────────── Project-scoped connections ───────────────────
// These connections expose backing Azure resources to the Foundry project so
// the agent runtime (and tools like File Search) can reach them via Entra ID.
// All four are referenced by the project capabilityHost below.

resource cosmosConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: 'cosmos-thread-storage'
  properties: {
    category: 'CosmosDB'
    target: cosmos.properties.documentEndpoint
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: cosmos.id
      Location: location
    }
  }
  dependsOn: [ cosmosRoleAssignmentProject ]
}

resource searchConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: 'aisearch-vector-store'
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${search.name}.search.windows.net'
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: search.id
      Location: location
    }
  }
  dependsOn: [ searchReaderForProject, searchContribForProject ]
}

resource storageConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: 'storage-files'
  properties: {
    category: 'AzureStorageAccount'
    target: agentStorage.properties.primaryEndpoints.blob
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: agentStorage.id
      Location: location
    }
  }
  dependsOn: [ storageContribForProject ]
}

resource appInsightsConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: 'app-insights'
  properties: {
    category: 'AppInsights'
    target: appInsights.id
    authType: 'ApiKey'
    credentials: {
      key: appInsights.properties.ConnectionString
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: appInsights.id
    }
  }
}

// ─────────────────────── Project capabilityHost ───────────────────────
// Tells the Foundry agents runtime which project connections to use for
// agent thread storage, vector stores, and uploaded files. Required for
// the "standard" agent setup; without it the runtime falls back to
// Microsoft-managed defaults ("basic" setup).

resource projectCapabilityHost 'Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-04-01-preview' = {
  parent: project
  name: 'agents-host'
  properties: any({
    capabilityHostKind: 'Agents'
    threadStorageConnections: [ cosmosConnection.name ]
    vectorStoreConnections: [ searchConnection.name ]
    storageConnections: [ storageConnection.name ]
  })
}

// ───────────────────────── Evaluations project ────────────────────────
// Sibling project used by the offline eval harness so eval runs, datasets,
// and red-team experiments don't pollute the runtime project's traces.
// No capabilityHost: evals run via the SDK against the Foundry deployment
// directly and don't need agent thread/vector/file state.

resource evalsProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: foundry
  name: 'hr-concierge-evals'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: 'Contoso HR Concierge — Evaluations'
    description: 'Offline evaluation harness for the HR Concierge agent (datasets, eval runs, red-team).'
  }
}

resource foundryUserForEvalsProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, evalsProject.id, 'aoai-user')
  scope: foundry
  properties: {
    principalId: evalsProject.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleId)
  }
}

// ─────────────────────────── Backend Container App ──────────────────────

resource backend 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-api-${uniq}'
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  dependsOn: [ acrPull, cosmosRoleAssignment ]
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      ingress: { external: true, targetPort: 8000, transport: 'http' }
      registries: [ { server: acr.properties.loginServer, identity: identity.id } ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: '${acr.properties.loginServer}/hr-backend-foundry:latest'
          env: [
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
            { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
            { name: 'COSMOS_ENDPOINT', value: cosmos.properties.documentEndpoint }
            { name: 'COSMOS_DB', value: 'hr' }
            { name: 'COSMOS_CONTAINER', value: 'threads' }
          ]
          resources: { cpu: json('0.5'), memory: '1Gi' }
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

// ────────────────────────────── Voice / IVR ─────────────────────────────
// Speech: Cognitive Services account (kind=SpeechServices) for STT/TTS.
//   Wired into the Foundry project as a connection so the hosted agent
//   can mint AAD tokens at runtime via the project's MI.
// ACS: PSTN-capable Communication Services resource for inbound IVR;
//   pair with the Foundry agent via Bot Service or ACS Call Automation
//   (configured outside Bicep).

resource speech 'Microsoft.CognitiveServices/accounts@2024-10-01' = if (enableVoice) {
  name: '${namePrefix}-spch-${uniq}'
  location: location
  tags: tags
  kind: 'SpeechServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: '${namePrefix}-spch-${uniq}'
    publicNetworkAccess: 'Enabled' // demo only.
    disableLocalAuth: true
  }
}

resource speechDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (enableVoice) {
  name: 'diag'
  scope: speech
  properties: {
    workspaceId: law.id
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

// Cognitive Services Speech User — lets the Foundry project's MI call STT/TTS via AAD.
var speechUserRoleId = 'f2dc8367-1007-4938-bd23-fe263f013447'
resource speechUserForProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableVoice) {
  name: guid('${namePrefix}-speech-user', project.id)
  scope: speech
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', speechUserRoleId)
  }
}

resource speechConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = if (enableVoice) {
  parent: project
  name: 'speech-voice'
  properties: {
    category: 'CognitiveService'
    target: speech.?properties.endpoint ?? ''
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      Kind: 'SpeechServices'
      ResourceId: speech.?id ?? ''
      Location: location
    }
  }
  dependsOn: [ speechUserForProject ]
}

resource acs 'Microsoft.Communication/communicationServices@2023-04-01' = if (enableVoice) {
  name: '${namePrefix}-acs-${uniq}'
  location: 'global'
  tags: tags
  properties: {
    dataLocation: acsDataLocation
  }
}

resource acsDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (enableVoice) {
  name: 'diag'
  scope: acs
  properties: {
    workspaceId: law.id
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

// ─────────────────────────────── Outputs ────────────────────────────────

output backendUrl string = 'https://${backend.properties.configuration.ingress.fqdn}'
output foundryEndpoint string = foundry.properties.endpoint
output foundryAccountId string = foundry.id
output projectName string = project.name
output projectId string = project.id
output projectEndpoint string = '${foundry.properties.endpoint}projects/${project.name}'
output projectCapabilityHostName string = projectCapabilityHost.name
output evalsProjectName string = evalsProject.name
output evalsProjectId string = evalsProject.id
output evalsProjectEndpoint string = '${foundry.properties.endpoint}projects/${evalsProject.name}'
output acrLoginServer string = acr.properties.loginServer
output identityClientId string = identity.properties.clientId
output keyVaultUri string = kv.properties.vaultUri
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output searchEndpoint string = 'https://${search.name}.search.windows.net'
output agentStorageBlobEndpoint string = agentStorage.properties.primaryEndpoints.blob
output speechEndpoint string = speech.?properties.endpoint ?? ''
output speechAccountName string = speech.?name ?? ''
output speechConnectionName string = speechConnection.?name ?? ''
output acsHostName string = acs.?properties.hostName ?? ''
output acsResourceId string = acs.?id ?? ''
