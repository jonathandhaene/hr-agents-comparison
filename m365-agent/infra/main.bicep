// Solution A — M365 Agents SDK
// Resources:
//   - Log Analytics + Application Insights
//   - Container Registry (managed-identity pull only)
//   - Container Apps Environment + 2 apps (agent + backend)
//   - Azure Bot service (Teams + M365 Copilot channels)
//   - Azure OpenAI (gpt-4o) via Microsoft Foundry / AIServices account
//   - Azure AI Search (RBAC only, key auth disabled)
//   - Cosmos DB (SQL API, key auth disabled, RBAC for the agent UAMI)
//   - Key Vault (for any future shared secrets)
//   - User-assigned managed identity used by both Container Apps
//   - Diagnostic settings forwarding all logs to Log Analytics
//   - Tags on every resource
//
// Voice / IVR: nothing to provision in Azure. The agent is published to
// Microsoft Teams and Microsoft 365 Copilot, both of which are voice-
// enabled hosts — they handle STT/TTS and (in Teams) call routing. See
// README § "Voice / IVR".
//
// All resources for this solution live in a SINGLE resource group so it can
// be torn down independently of the other solutions.
//
// Cost note (illustrative): Always-on Container Apps + Cosmos serverless +
// AOAI gpt-4o is the most expensive of the four solutions. Tear down the
// resource group when not in use.

targetScope = 'resourceGroup'

// ────────────────────────────── Parameters ──────────────────────────────

@description('Short prefix for resource names (3-8 chars).')
@minLength(3)
@maxLength(8)
param namePrefix string = 'hrm365'

@description('Azure region.')
param location string = resourceGroup().location

@description('Microsoft Entra app id used for the bot registration.')
param botAppId string

@description('Azure OpenAI deployment to call from the agent.')
param openAiDeployment string = 'gpt-4o'

@description('Tags applied to every resource.')
param tags object = {
  workload: 'hr-concierge'
  solution: 'm365-agent'
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

resource kvDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: kv
  properties: {
    workspaceId: law.id
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
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
  name: 'state'
  properties: {
    resource: {
      id: 'state'
      partitionKey: { paths: [ '/id' ], kind: 'Hash' }
    }
  }
}

// Cosmos DB Built-in Data Contributor (data plane RBAC).
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

// Agent UAMI → Search (Search Index Data Reader)
var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
resource searchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, identity.id, searchIndexDataReaderRoleId)
  scope: search
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataReaderRoleId)
  }
}

// We also need Search Service Contributor at index-creation time (the seed
// script runs from the deploy workflow with the workflow identity, not this
// UAMI, so no role assignment is needed here for that path). If you run the
// seed script as the UAMI, grant Search Index Data Contributor explicitly.

resource searchDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: search
  properties: {
    workspaceId: law.id
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

// ───────────────────── Azure OpenAI (Foundry account) ──────────────────

resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${namePrefix}-aoai-${uniq}'
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: '${namePrefix}-aoai-${uniq}'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled' // demo only.
  }
}

resource gpt 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aoai
  name: openAiDeployment
  sku: { name: 'GlobalStandard', capacity: 30 }
  properties: { model: { format: 'OpenAI', name: 'gpt-4o', version: '2024-08-06' } }
}

// Agent UAMI → AOAI (Cognitive Services OpenAI User)
var aoaiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
resource aoaiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aoai.id, identity.id, aoaiUserRoleId)
  scope: aoai
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', aoaiUserRoleId)
  }
}

resource aoaiDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: aoai
  properties: {
    workspaceId: law.id
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
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

resource backend 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-api-${uniq}'
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  dependsOn: [ acrPull ]
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
          image: '${acr.properties.loginServer}/hr-backend:latest'
          env: [
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
            { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
          ]
          resources: { cpu: json('0.5'), memory: '1Gi' }
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

resource agent 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-agent-${uniq}'
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  dependsOn: [ acrPull, cosmosRoleAssignment, searchReader, aoaiUser ]
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      ingress: { external: true, targetPort: 3978, transport: 'http' }
      registries: [ { server: acr.properties.loginServer, identity: identity.id } ]
    }
    template: {
      containers: [
        {
          name: 'agent'
          image: '${acr.properties.loginServer}/hr-agent:latest'
          env: [
            { name: 'HR_API_BASE', value: 'https://${backend.properties.configuration.ingress.fqdn}' }
            { name: 'COSMOS_ENDPOINT', value: cosmos.properties.documentEndpoint }
            { name: 'COSMOS_DB', value: 'hr' }
            { name: 'COSMOS_CONTAINER', value: 'state' }
            { name: 'SEARCH_ENDPOINT', value: 'https://${search.name}.search.windows.net' }
            { name: 'SEARCH_INDEX', value: 'hr-policies' }
            { name: 'AOAI_ENDPOINT', value: aoai.properties.endpoint }
            { name: 'AOAI_DEPLOYMENT', value: openAiDeployment }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
            { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
          ]
          resources: { cpu: json('0.5'), memory: '1Gi' }
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 5 }
    }
  }
}

// ───────────────────────────── Azure Bot ────────────────────────────────

resource bot 'Microsoft.BotService/botServices@2022-09-15' = {
  name: '${namePrefix}-bot-${uniq}'
  location: 'global'
  tags: tags
  sku: { name: 'F0' }
  kind: 'azurebot'
  properties: {
    displayName: 'Contoso HR Concierge (M365 SDK)'
    msaAppId: botAppId
    msaAppType: 'UserAssignedMSI'
    msaAppMSIResourceId: identity.id
    msaAppTenantId: subscription().tenantId
    endpoint: 'https://${agent.properties.configuration.ingress.fqdn}/api/messages'
  }
}

resource teamsChannel 'Microsoft.BotService/botServices/channels@2022-09-15' = {
  parent: bot
  name: 'MsTeamsChannel'
  location: 'global'
  properties: { channelName: 'MsTeamsChannel', properties: { isEnabled: true } }
}

resource m365CopilotChannel 'Microsoft.BotService/botServices/channels@2022-09-15' = {
  parent: bot
  name: 'M365Extensions'
  location: 'global'
  properties: { channelName: 'M365Extensions', properties: { isEnabled: true } }
}

// ───────────────────────────── Outputs ────────────────────────────────

output backendUrl string = 'https://${backend.properties.configuration.ingress.fqdn}'
output agentUrl string = 'https://${agent.properties.configuration.ingress.fqdn}'
output botName string = bot.name
output acrLoginServer string = acr.properties.loginServer
output identityClientId string = identity.properties.clientId
output keyVaultUri string = kv.properties.vaultUri
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output searchEndpoint string = 'https://${search.name}.search.windows.net'
output aoaiEndpoint string = aoai.properties.endpoint
