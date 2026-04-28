// Solution C — Microsoft Foundry hosted agent
// Resources:
// - Microsoft Foundry account (CognitiveServices kind=AIServices) + Foundry project
// - Azure AI Search (used by Foundry File Search)
// - Container Apps Environment + 1 app (FastAPI backend)
// - Cosmos DB (agent state — Foundry agent threads + thread metadata)
// - Application Insights, Log Analytics, Key Vault, user-assigned Managed Identity
// - Role assignments so the project can call AOAI + Search + Cosmos
//
// The hosted agent itself is created by `az ai-foundry agent create --file project/agent.yaml`
// in the deploy workflow — Bicep doesn't model the agent directly.

targetScope = 'resourceGroup'

@description('Short prefix for resource names (3-8 chars).')
param namePrefix string = 'hrfdy'

@description('Azure region.')
param location string = resourceGroup().location

@description('Azure OpenAI deployment used by the Foundry agent.')
param openAiDeployment string = 'gpt-4o'

var uniq = uniqueString(resourceGroup().id, namePrefix)

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-law-${uniq}'
  location: location
  properties: { sku: { name: 'PerGB2018' } }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${namePrefix}-ai-${uniq}'
  location: location
  kind: 'web'
  properties: { Application_Type: 'web', WorkspaceResourceId: law.id }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-id-${uniq}'
  location: location
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: replace('${namePrefix}acr${uniq}', '-', '')
  location: location
  sku: { name: 'Basic' }
}

resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-cae-${uniq}'
  location: location
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

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: '${namePrefix}-cos-${uniq}'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [ { locationName: location, failoverPriority: 0 } ]
    capabilities: [ { name: 'EnableServerless' } ]
  }
}

resource search 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: '${namePrefix}-srch-${uniq}'
  location: location
  sku: { name: 'basic' }
  properties: { authOptions: { aadOrApiKey: { aadAuthFailureMode: 'http401WithBearerChallenge' } } }
}

// Microsoft Foundry account (AIServices kind enables hub-less project model)
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

// Foundry project (modern hub-less project)
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

resource backend 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-api-${uniq}'
  location: location
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      ingress: { external: true, targetPort: 8000, transport: 'http' }
      registries: [ { server: acr.properties.loginServer, identity: identity.id } ]
    }
    template: {
      containers: [
        { name: 'api', image: '${acr.properties.loginServer}/hr-backend-foundry:latest' }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
}

// Role assignments — Foundry project's MI calls AOAI + Search
resource aoaiUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, project.id, 'aoai-user')
  scope: foundry
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd') // Cognitive Services OpenAI User
  }
}

resource searchIndexDataReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, project.id, 'search-reader')
  scope: search
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '1407120a-92aa-4202-b7e9-c0e197c71c8f') // Search Index Data Reader
  }
}

output backendUrl string = 'https://${backend.properties.configuration.ingress.fqdn}'
output foundryEndpoint string = foundry.properties.endpoint
output projectName string = project.name
output projectEndpoint string = '${foundry.properties.endpoint}projects/${project.name}'
output acrLoginServer string = acr.properties.loginServer
output identityClientId string = identity.properties.clientId
