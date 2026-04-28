// Solution A — M365 Agents SDK
// Resources: Container Registry, Container Apps Environment + 2 apps (agent + backend),
// Azure Bot, Azure OpenAI, Azure AI Search, Cosmos DB, App Insights, Key Vault,
// User-assigned managed identity for the agent.
//
// All resources for this solution live in a SINGLE resource group so it can be
// torn down independently of the other two solutions.

targetScope = 'resourceGroup'

@description('Short prefix for resource names (3-8 chars).')
param namePrefix string = 'hrm365'

@description('Azure region.')
param location string = resourceGroup().location

@description('Microsoft Entra app id used for the bot registration.')
param botAppId string

@description('Azure OpenAI deployment to call from the agent.')
param openAiDeployment string = 'gpt-4o'

var uniq = uniqueString(resourceGroup().id, namePrefix)

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-law-${uniq}'
  location: location
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30 }
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
  properties: { adminUserEnabled: false }
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

resource search 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: '${namePrefix}-srch-${uniq}'
  location: location
  sku: { name: 'basic' }
  properties: { authOptions: { aadOrApiKey: { aadAuthFailureMode: 'http401WithBearerChallenge' } } }
}

resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${namePrefix}-aoai-${uniq}'
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: { customSubDomainName: '${namePrefix}-aoai-${uniq}' }
}

resource gpt 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: aoai
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
        {
          name: 'api'
          image: '${acr.properties.loginServer}/hr-backend:latest'
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
}

resource agent 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-agent-${uniq}'
  location: location
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
            { name: 'COSMOS_CONN', value: cosmos.listConnectionStrings().connectionStrings[0].connectionString }
            { name: 'SEARCH_ENDPOINT', value: 'https://${search.name}.search.windows.net' }
            { name: 'SEARCH_INDEX', value: 'hr-policies' }
            { name: 'AOAI_ENDPOINT', value: aoai.properties.endpoint }
            { name: 'AOAI_DEPLOYMENT', value: openAiDeployment }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
            { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 5 }
    }
  }
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
}

resource bot 'Microsoft.BotService/botServices@2022-09-15' = {
  name: '${namePrefix}-bot-${uniq}'
  location: 'global'
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

output backendUrl string = 'https://${backend.properties.configuration.ingress.fqdn}'
output agentUrl string = 'https://${agent.properties.configuration.ingress.fqdn}'
output botName string = bot.name
output acrLoginServer string = acr.properties.loginServer
output identityClientId string = identity.properties.clientId
