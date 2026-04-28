// Solution B — Copilot Studio
// Azure-side resources only: APIM (fronting the FastAPI backend) + the
// Container Apps Environment that hosts the backend itself. Everything
// agent-shaped (topics, flows, Dataverse tables) lives in the Power Platform
// solution under `solution/` and is deployed by `pac solution import`.

targetScope = 'resourceGroup'

@description('Short prefix for resource names.')
param namePrefix string = 'hrcps'

@description('Azure region.')
param location string = resourceGroup().location

@description('Email used as APIM publisher contact.')
param apimPublisherEmail string

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

resource backend 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-api-${uniq}'
  location: location
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      ingress: { external: true, targetPort: 8000, transport: 'http' }
    }
    template: {
      containers: [
        { name: 'api', image: '${acr.properties.loginServer}/hr-backend-cps:latest' }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

resource apim 'Microsoft.ApiManagement/service@2024-05-01' = {
  name: '${namePrefix}-apim-${uniq}'
  location: location
  sku: { name: 'Consumption', capacity: 0 }
  properties: {
    publisherEmail: apimPublisherEmail
    publisherName: 'Contoso HR'
  }
}

resource api 'Microsoft.ApiManagement/service/apis@2024-05-01' = {
  parent: apim
  name: 'hr-api'
  properties: {
    displayName: 'HR API'
    path: 'hr'
    protocols: [ 'https' ]
    serviceUrl: 'https://${backend.properties.configuration.ingress.fqdn}'
    subscriptionRequired: true
  }
}

output backendUrl string = 'https://${backend.properties.configuration.ingress.fqdn}'
output apimGatewayUrl string = apim.properties.gatewayUrl
output acrLoginServer string = acr.properties.loginServer
