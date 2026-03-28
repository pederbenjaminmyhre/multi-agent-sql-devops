@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Base name for all resources')
param baseName string = 'sqldevops'

@description('Container image (set after first ACR push)')
param containerImage string = ''

// ── Container Registry ──────────────────────────────────────
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'acr${baseName}'
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: true }
}

// ── Log Analytics Workspace ─────────────────────────────────
resource logWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-${baseName}'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ── Application Insights ────────────────────────────────────
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${baseName}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logWorkspace.id
  }
}

// ── Key Vault ───────────────────────────────────────────────
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${baseName}'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
  }
}

// ── Cosmos DB (Serverless) ──────────────────────────────────
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-02-15-preview' = {
  name: 'cosmos-${baseName}'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    capabilities: [{ name: 'EnableServerless' }]
    locations: [{ locationName: location, failoverPriority: 0 }]
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-02-15-preview' = {
  parent: cosmosAccount
  name: 'sql-review-db'
  properties: {
    resource: { id: 'sql-review-db' }
  }
}

resource cosmosContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-02-15-preview' = {
  parent: cosmosDb
  name: 'review-state'
  properties: {
    resource: {
      id: 'review-state'
      partitionKey: { paths: ['/session_id'], kind: 'Hash' }
    }
  }
}

// ── Container Apps Environment ──────────────────────────────
resource caeEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${baseName}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logWorkspace.properties.customerId
        sharedKey: logWorkspace.listKeys().primarySharedKey
      }
    }
  }
}

// ── Container App ───────────────────────────────────────────
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-sql-review'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: caeEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        { name: 'acr-password', value: acr.listCredentials().passwords[0].value }
      ]
    }
    template: {
      containers: [
        {
          name: 'sql-review-agent'
          image: containerImage != '' ? containerImage : '${acr.properties.loginServer}/sql-review-agent:latest'
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'APPINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
            { name: 'COSMOS_ENDPOINT', value: cosmosAccount.properties.documentEndpoint }
            { name: 'COSMOS_DATABASE', value: 'sql-review-db' }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 2
        rules: [
          {
            name: 'http-scaling'
            http: { metadata: { concurrentRequests: '10' } }
          }
        ]
      }
    }
  }
}

// ── Outputs ─────────────────────────────────────────────────
output acrLoginServer string = acr.properties.loginServer
output appUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output cosmosEndpoint string = cosmosAccount.properties.documentEndpoint
output keyVaultUri string = keyVault.properties.vaultUri
