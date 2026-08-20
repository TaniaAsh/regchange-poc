@description('Globally unique Function App name')
param functionAppName string

param location string = resourceGroup().location
param storageAccountName string
param appInsightsConnectionString string
param foundryEndpointSecretUri string
param searchEndpointSecretUri string
param searchIndexName string
param foundryApiVersion string
param foundryModelExtraction string
param foundryModelAnalysis string
param outputContainerName string

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: '${functionAppName}-plan'
  location: location
  sku: {
    // Consumption plan — pay per execution, 1M free executions/month.
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true // required for Linux
  }
}

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      appSettings: [
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        // Identity-based storage connection — no connection string, no key.
        // Requires the role assignments granted in main.bicep (Storage Blob
        // Data Owner, Storage Queue/Table Data Contributor).
        {
          name: 'AzureWebJobsStorage__accountName'
          value: storageAccountName
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'FOUNDRY_ENDPOINT'
          value: '@Microsoft.KeyVault(SecretUri=${foundryEndpointSecretUri})'
        }
        {
          name: 'SEARCH_ENDPOINT'
          value: '@Microsoft.KeyVault(SecretUri=${searchEndpointSecretUri})'
        }
        {
          name: 'STORAGE_ACCOUNT_NAME'
          value: storageAccountName
        }
        {
          name: 'STORAGE_CONTAINER_OUTPUT'
          value: outputContainerName
        }
        {
          name: 'SEARCH_INDEX_NAME'
          value: searchIndexName
        }
        {
          name: 'FOUNDRY_API_VERSION'
          value: foundryApiVersion
        }
        {
          name: 'FOUNDRY_MODEL_EXTRACTION'
          value: foundryModelExtraction
        }
        {
          name: 'FOUNDRY_MODEL_ANALYSIS'
          value: foundryModelAnalysis
        }
      ]
    }
  }
}

output functionAppId string = functionApp.id
output functionAppName string = functionApp.name
output principalId string = functionApp.identity.principalId
output defaultHostName string = functionApp.properties.defaultHostName
