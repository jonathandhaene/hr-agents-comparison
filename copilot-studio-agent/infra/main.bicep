// Solution B — Copilot Studio (Azure-side resources)
// What we provision in Azure:
//   - Log Analytics + Application Insights
//   - Container Registry (managed-identity pull only — admin user disabled)
//   - Container Apps Environment + 1 app (FastAPI backend) wired to a UAMI
//   - APIM Consumption tier fronting the backend
//   - Microsoft Foundry account (CognitiveServices kind=AIServices) + project
//     for fine-tuning jobs (UC6 triage classifier, UC7 narrative) and offline
//     safety evaluations. The Copilot Studio generative-answers node calls the
//     fine-tuned deployment registered here.
//   - Diagnostic settings forwarding all logs to Log Analytics
//   - Tags on every resource
//
// Voice / IVR: nothing to provision in Azure. Copilot Studio's built-in
// voice channel (Channels → Telephony) ships STT/TTS and a phone number;
// it is also voice-enabled inside Microsoft Teams and Microsoft 365
// Copilot. See README § "Voice / IVR".
//
// What lives outside this template:
//   - Topics, Power Fx flows, custom connector, Dataverse tables — deployed
//     by `pac solution import` from `solution/`.
//   - The Copilot Studio agent itself — provisioned in Power Platform.
//
// Cost note (illustrative, US East prices, May 2025):
//   APIM Consumption is pay-per-call (~US$3.50 / 1M calls), Container Apps
//   scales to one always-on replica (~US$15/month for the demo SKU). Tear
//   down the resource group when not in use.

targetScope = 'resourceGroup'

// ────────────────────────────── Parameters ──────────────────────────────

@description('Short prefix for resource names (3-8 chars, lowercase alphanumeric).')
@minLength(3)
@maxLength(8)
param namePrefix string = 'hrcps'

@description('Azure region.')
param location string = resourceGroup().location

@description('Email used as the APIM publisher contact.')
param apimPublisherEmail string

@description('Tags applied to every resource.')
param tags object = {
  workload: 'hr-concierge'
  solution: 'copilot-studio'
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
    publicNetworkAccess: 'Enabled' // demo only — set to 'Disabled' + private endpoint for prod.
  }
}

// AcrPull lets the UAMI pull images without admin keys.
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
          image: '${acr.properties.loginServer}/hr-backend-cps:latest'
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

// ─────────────────────────────── APIM ───────────────────────────────────

resource apim 'Microsoft.ApiManagement/service@2024-05-01' = {
  name: '${namePrefix}-apim-${uniq}'
  location: location
  tags: tags
  sku: { name: 'Consumption', capacity: 0 }
  identity: { type: 'SystemAssigned' }
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

resource apimDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: apim
  properties: {
    workspaceId: law.id
    logs: [ { categoryGroup: 'allLogs', enabled: true } ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

// ──────────── Microsoft Foundry account + project (evals / fine-tuning) ─────────────
// The Copilot Studio agent uses Power Platform for its conversational surface, but
// fine-tuning jobs (UC6 triage classifier, UC7 performance narrative) and safety
// evaluations must run in a Microsoft Foundry project. Once a fine-tuned deployment
// is registered here, update the Foundry resource selector in Copilot Studio's
// Generative Answers node to point at this endpoint.

resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${namePrefix}-fdy-${uniq}'
  location: location
  tags: tags
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: '${namePrefix}-fdy-${uniq}'
    allowProjectManagement: true
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled' // demo only.
  }
}

// Foundry project — fine-tuning jobs and evaluation datasets live here.
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: foundry
  name: 'hr-concierge'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    description: 'Foundry project for Solution B (Copilot Studio) — hosts fine-tuning jobs and safety evaluations.'
    displayName: 'HR Concierge – Copilot Studio'
  }
}

// Base model deployment for fine-tuning source and evaluation prompts.
resource gpt 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: foundry
  name: 'gpt-4o'
  sku: { name: 'GlobalStandard', capacity: 10 }
  properties: { model: { format: 'OpenAI', name: 'gpt-4o', version: '2024-08-06' } }
}

// Backend UAMI → Foundry (Cognitive Services OpenAI User) so the backend can
// call the fine-tuned classifier deployment from the Functions/Container Apps tier.
var foundryUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
resource foundryUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, identity.id, foundryUserRoleId)
  scope: foundry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleId)
  }
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

// ───────────────────────────── Outputs ────────────────────────────────

output backendUrl string = 'https://${backend.properties.configuration.ingress.fqdn}'
output apimGatewayUrl string = apim.properties.gatewayUrl
output acrLoginServer string = acr.properties.loginServer
output identityClientId string = identity.properties.clientId
output foundryEndpoint string = foundry.properties.endpoint
output projectEndpoint string = '${foundry.properties.endpoint}projects/${project.name}'
