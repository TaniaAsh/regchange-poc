@description('Short base name used to derive all resource names, e.g. "regchangepoc"')
@minLength(3)
@maxLength(15)
param baseName string = 'regchangepoc'

param location string = 'uksouth'

@description('Full ARM resource ID of your existing Microsoft Foundry / Azure OpenAI resource')
param foundryResourceId string

@description('Name of the resource group the existing Foundry resource lives in')
param foundryResourceGroupName string

@description('Endpoint URL of your existing Foundry resource, e.g. https://<name>.openai.azure.com/')
param foundryEndpoint string

param foundryApiVersion string = '2024-10-21'
param foundryModelExtraction string = 'gpt-4o-mini'
param foundryModelAnalysis string = 'gpt-4o'
param searchIndexName string = 'policy-fragments-v1'

// uniqueString() keeps generated names deterministic-but-unique per resource
// group, so re-running this deployment against the same RG always produces
// the same names (idempotent), while a fresh RG gets fresh globally-unique
// names automatically — no manual name bookkeeping required.
var suffix = uniqueString(resourceGroup().id)
// Storage account names must be <= 24 chars, lowercase alphanumeric only —
// deliberately not derived from baseName (which can be up to 15 chars) to
// guarantee this stays safely under the limit no matter what baseName is set to.
var storageAccountName = toLower('regchgst${suffix}')
var searchServiceName = toLower('${baseName}-search-${suffix}')
var keyVaultName = toLower('${baseName}-kv-${suffix}')
var functionAppName = toLower('${baseName}-func-${suffix}')
var logAnalyticsName = '${baseName}-logs-${suffix}'
var appInsightsName = '${baseName}-ai-${suffix}'
var systemTopicName = '${baseName}-blobtopic-${suffix}'
var outputContainerName = 'impact-hypotheses'

// Extract just the account name from the Foundry resource ID for the RBAC
// module — the last path segment of a Cognitive Services resource ID.
var foundryAccountName = last(split(foundryResourceId, '/'))

module storage 'modules/storage.bicep' = {
  name: 'storage-deployment'
  params: {
    storageAccountName: storageAccountName
    location: location
  }
}

module logAnalytics 'modules/log-analytics.bicep' = {
  name: 'log-analytics-deployment'
  params: {
    workspaceName: logAnalyticsName
    location: location
  }
}

module appInsights 'modules/app-insights.bicep' = {
  name: 'app-insights-deployment'
  params: {
    appInsightsName: appInsightsName
    location: location
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
  }
}

module keyVault 'modules/key-vault.bicep' = {
  name: 'key-vault-deployment'
  params: {
    keyVaultName: keyVaultName
    location: location
    foundryEndpoint: foundryEndpoint
    searchEndpoint: 'https://${searchServiceName}.search.windows.net'
  }
}

module search 'modules/search.bicep' = {
  name: 'search-deployment'
  params: {
    searchServiceName: searchServiceName
    location: location
  }
}

module eventGridTopic 'modules/event-grid-topic.bicep' = {
  name: 'event-grid-topic-deployment'
  params: {
    systemTopicName: systemTopicName
    location: location
    storageAccountId: storage.outputs.storageAccountId
  }
}

module functionApp 'modules/function-app.bicep' = {
  name: 'function-app-deployment'
  params: {
    functionAppName: functionAppName
    location: location
    storageAccountName: storage.outputs.storageAccountName
    appInsightsConnectionString: appInsights.outputs.connectionString
    foundryEndpointSecretUri: keyVault.outputs.foundryEndpointSecretUri
    searchEndpointSecretUri: keyVault.outputs.searchEndpointSecretUri
    searchIndexName: searchIndexName
    foundryApiVersion: foundryApiVersion
    foundryModelExtraction: foundryModelExtraction
    foundryModelAnalysis: foundryModelAnalysis
    outputContainerName: outputContainerName
  }
}

// --- RBAC: grant the Function App's managed identity exactly what it needs,
// nothing more. Every role below maps to a concrete, named need in the
// pipeline code — see the comment on each.

var storageBlobDataOwnerRoleId = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
var storageQueueDataContributorRoleId = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
var storageTableDataContributorRoleId = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource existingStorage 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

resource existingSearch 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: searchServiceName
}

resource existingKeyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Blob/Queue/Table Data roles: required for the identity-based
// AzureWebJobsStorage connection (Functions runtime state) AND for the
// pipeline's own blob reads/writes to regulatory-documents /
// impact-hypotheses (see function_app.py).
resource storageBlobRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(existingStorage.id, functionAppName, storageBlobDataOwnerRoleId)
  scope: existingStorage
  properties: {
    principalId: functionApp.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataOwnerRoleId)
  }
}

resource storageQueueRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(existingStorage.id, functionAppName, storageQueueDataContributorRoleId)
  scope: existingStorage
  properties: {
    principalId: functionApp.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageQueueDataContributorRoleId)
  }
}

resource storageTableRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(existingStorage.id, functionAppName, storageTableDataContributorRoleId)
  scope: existingStorage
  properties: {
    principalId: functionApp.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageTableDataContributorRoleId)
  }
}

// Read-only — the pipeline queries the index, it never writes to it in this
// PoC (index population is a separate, not-yet-built step; see ARCHITECTURE.md).
resource searchRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(existingSearch.id, functionAppName, searchIndexDataReaderRoleId)
  scope: existingSearch
  properties: {
    principalId: functionApp.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataReaderRoleId)
  }
  dependsOn: [
    search
  ]
}

// Lets the Function App resolve the @Microsoft.KeyVault(...) references in
// its own App Settings.
resource keyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(existingKeyVault.id, functionAppName, keyVaultSecretsUserRoleId)
  scope: existingKeyVault
  properties: {
    principalId: functionApp.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
  }
}

// Cross-resource-group role assignment on the pre-existing Foundry
// resource — deployed with an explicit scope override since it lives
// outside this resource group.
module foundryRoleAssignment 'modules/foundry-role-assignment.bicep' = {
  name: 'foundry-role-assignment-deployment'
  scope: resourceGroup(foundryResourceGroupName)
  params: {
    foundryAccountName: foundryAccountName
    principalId: functionApp.outputs.principalId
    functionAppNameForGuidSeed: functionAppName
  }
}

output functionAppName string = functionApp.outputs.functionAppName
output functionAppPrincipalId string = functionApp.outputs.principalId
output storageAccountName string = storage.outputs.storageAccountName
output searchServiceName string = search.outputs.searchServiceName
output keyVaultName string = keyVault.outputs.keyVaultName
output eventGridSystemTopicName string = eventGridTopic.outputs.systemTopicName
