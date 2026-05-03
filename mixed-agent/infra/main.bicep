// Solution D — Mixed (Copilot Studio orchestrator + connected Foundry agent)
// Optimised for lowest resting cost and lowest maintenance.
//
// Resources (Azure side only — Power Platform side is the Copilot Studio solution):
//   - Microsoft Foundry account (kind=AIServices) + project for the connected advisor agent
//   - Microsoft Foundry gpt-4o GlobalStandard (low capacity)
//   - Azure Functions Consumption plan + Linux Function App (Python v2)
//     hosting the HR API as the connector backend
//   - Storage account (required by Functions) — identity-based (no shared keys)
//   - Application Insights + Log Analytics
//   - User-assigned managed identity used by the Function App
//
// Voice / IVR: nothing to provision in Azure. Copilot Studio is the
// orchestrator and ships voice via Teams, Microsoft 365 Copilot, and the
// built-in voice/telephony channel. The connected Foundry agent inherits
// voice from that surface. See README § "Voice / IVR".
//
// Deliberately NOT included: APIM, Container Apps, Cosmos DB, Azure AI Search.
// All durable state lives in-memory in the demo Function App (see README).
//
// Cost note (illustrative): Functions Consumption + Foundry gpt-4o pay-per-token
// is the cheapest tier we ship. Tear down the resource group when not in use.

targetScope = 'resourceGroup'

@description('Short prefix for resource names (3-8 chars).')
@minLength(3)
@maxLength(8)
param namePrefix string = 'hrmix'

@description('Azure region.')
param location string = resourceGroup().location

@description('Microsoft Foundry model deployment name used by the connected agent.')
param foundryDeployment string = 'gpt-4o'

@description('Tags applied to every resource.')
param tags object = {
  workload: 'hr-concierge'
  solution: 'mixed-agent'
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

resource ai 'Microsoft.Insights/components@2020-02-02' = {
  name: '${namePrefix}-ai-${uniq}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
  }
}

// ─────────────────────────── Identity ──────────────────────────────────

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id-${uniq}'
  location: location
  tags: tags
}

// ─────────────────────────── Storage ───────────────────────────────────

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: replace('${namePrefix}st${uniq}', '-', '')
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false // identity-based AzureWebJobsStorage
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Enabled' // demo only — restrict to private endpoint for prod.
  }
}

// Functions MI needs Storage Blob Data Owner + Queue Data Contributor +
// Table Data Contributor on the AzureWebJobs storage account when shared
// keys are disabled.
var blobDataOwnerRoleId = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
resource storageBlobOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, identity.id, blobDataOwnerRoleId)
  scope: storage
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobDataOwnerRoleId)
  }
}

var queueDataContributorRoleId = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
resource storageQueueContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, identity.id, queueDataContributorRoleId)
  scope: storage
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', queueDataContributorRoleId)
  }
}

var tableDataContributorRoleId = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
resource storageTableContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, identity.id, tableDataContributorRoleId)
  scope: storage
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', tableDataContributorRoleId)
  }
}

// ─────────────────────────── Functions ─────────────────────────────────

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${namePrefix}-plan-${uniq}'
  location: location
  tags: tags
  sku: { name: 'Y1', tier: 'Dynamic' }
  properties: { reserved: true }
}

resource func 'Microsoft.Web/sites@2023-12-01' = {
  name: '${namePrefix}-fn-${uniq}'
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  dependsOn: [ storageBlobOwner, storageQueueContributor, storageTableContributor ]
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    keyVaultReferenceIdentity: identity.id
    siteConfig: {
      linuxFxVersion: 'Python|3.12'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        // Identity-based AzureWebJobsStorage — no account keys.
        { name: 'AzureWebJobsStorage__accountName', value: storage.name }
        { name: 'AzureWebJobsStorage__credential', value: 'managedidentity' }
        { name: 'AzureWebJobsStorage__clientId', value: identity.properties.clientId }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: ai.properties.ConnectionString }
        { name: 'HR_DATA_DIR', value: '/home/site/wwwroot/data' }
        { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
      ]
    }
  }
}

resource funcDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: func
  properties: {
    workspaceId: law.id
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

// ─────────────────────────── Microsoft Foundry ─────────────────────────

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
    publicNetworkAccess: 'Enabled' // demo only — restrict to private endpoint for prod.
    disableLocalAuth: true
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: foundry
  name: 'hr-mobility-advisor'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: 'HR Mobility & Feedback Advisor'
    description: 'Connected agent invoked by the Copilot Studio Mixed solution.'
  }
}

resource gpt 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: foundry
  name: foundryDeployment
  sku: { name: 'GlobalStandard', capacity: 10 } // low capacity — only UC4/UC5 calls
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

// Functions UAMI → Foundry (Cognitive Services OpenAI User)
var foundryUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
resource foundryRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, identity.id, foundryUserRoleId)
  scope: foundry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleId)
  }
}

// ───────────────────────────── Outputs ────────────────────────────────

output functionAppHost string = func.properties.defaultHostName
output foundryEndpoint string = foundry.properties.endpoint
output projectEndpoint string = '${foundry.properties.endpoint}projects/${project.name}'
output identityClientId string = identity.properties.clientId
