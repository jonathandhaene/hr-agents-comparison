// Solution D — Mixed (Copilot Studio + connected Foundry agent)
// Optimised for lowest resting cost and lowest maintenance.
//
// Resources (Azure side only — Power Platform side is the Copilot Studio solution):
// - Microsoft Foundry account (kind=AIServices) + project for the connected advisor agent
// - Azure OpenAI gpt-4o GlobalStandard (low capacity)
// - Azure Functions Consumption plan + Linux Function App (Python)
// - Storage account (required by Functions)
// - Application Insights + Log Analytics
// - User-assigned managed identity for Functions → Foundry / AOAI
//
// Deliberately NOT included: APIM, Container Apps, Cosmos DB, Azure AI Search.

targetScope = 'resourceGroup'

@description('Short prefix for resource names (3-8 chars).')
param namePrefix string = 'hrmix'

@description('Azure region.')
param location string = resourceGroup().location

@description('AOAI deployment used by the Foundry connected agent.')
param openAiDeployment string = 'gpt-4o'

var uniq = uniqueString(resourceGroup().id, namePrefix)

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-law-${uniq}'
  location: location
  properties: { sku: { name: 'PerGB2018' } }
}

resource ai 'Microsoft.Insights/components@2020-02-02' = {
  name: '${namePrefix}-ai-${uniq}'
  location: location
  kind: 'web'
  properties: { Application_Type: 'web', WorkspaceResourceId: law.id }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id-${uniq}'
  location: location
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: replace('${namePrefix}st${uniq}', '-', '')
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: { allowBlobPublicAccess: false, minimumTlsVersion: 'TLS1_2' }
}

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${namePrefix}-plan-${uniq}'
  location: location
  sku: { name: 'Y1', tier: 'Dynamic' } // Consumption — scales to zero
  properties: { reserved: true } // Linux
}

resource func 'Microsoft.Web/sites@2023-12-01' = {
  name: '${namePrefix}-fn-${uniq}'
  location: location
  kind: 'functionapp,linux'
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.12'
      appSettings: [
        { name: 'AzureWebJobsStorage', value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storage.listKeys().keys[0].value}' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: ai.properties.ConnectionString }
        { name: 'HR_DATA_DIR', value: '/home/site/wwwroot/data' }
        { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
      ]
    }
  }
}

resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${namePrefix}-fdy-${uniq}'
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    allowProjectManagement: true
    customSubDomainName: '${namePrefix}-fdy-${uniq}'
    publicNetworkAccess: 'Enabled'
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
  name: openAiDeployment
  sku: { name: 'GlobalStandard', capacity: 10 } // low capacity — only UC4/UC5 calls
  properties: { model: { format: 'OpenAI', name: 'gpt-4o', version: '2024-08-06' } }
}

// Functions MI → Foundry (Cognitive Services OpenAI User)
resource aoaiRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, identity.id, 'aoai-user')
  scope: foundry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
}

output functionAppHost string = func.properties.defaultHostName
output foundryEndpoint string = foundry.properties.endpoint
output projectEndpoint string = '${foundry.properties.endpoint}projects/${project.name}'
output identityClientId string = identity.properties.clientId
