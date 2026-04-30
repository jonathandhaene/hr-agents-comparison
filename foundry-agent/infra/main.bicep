// Solution C — Microsoft Foundry hosted agent
// Resources:
//   - Microsoft Foundry account (CognitiveServices kind=AIServices) + project
//   - Azure AI Search (used by Foundry File Search)
//   - Container Apps Environment + 1 app (FastAPI backend exposed as the
//     OpenAPI tool the hosted agent calls)
//   - Container Registry (UAMI pull only)
//   - Cosmos DB (agent thread metadata) — RBAC only, key auth disabled
//   - Application Insights, Log Analytics, Key Vault, user-assigned MI
//   - Role assignments so the Foundry project's MI can call AOAI + Search
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

@description('Azure OpenAI deployment used by the Foundry agent.')
param openAiDeployment string = 'gpt-4o'

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

// ─────────────────────────── Container Apps ─────────────────────────────

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
  name: openAiDeployment
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

// Foundry project's MI → AOAI (Cognitive Services OpenAI User)
var aoaiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
resource aoaiUserForProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, project.id, 'aoai-user')
  scope: foundry
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', aoaiUserRoleId)
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

// ─────────────────────────────── Outputs ────────────────────────────────

output backendUrl string = 'https://${backend.properties.configuration.ingress.fqdn}'
output foundryEndpoint string = foundry.properties.endpoint
output projectName string = project.name
output projectEndpoint string = '${foundry.properties.endpoint}projects/${project.name}'
output acrLoginServer string = acr.properties.loginServer
output identityClientId string = identity.properties.clientId
output keyVaultUri string = kv.properties.vaultUri
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output searchEndpoint string = 'https://${search.name}.search.windows.net'
