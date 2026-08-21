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

// Key Vault names must be <= 24 chars too — same fix as storageAccountName above.
var keyVaultName = toLower('rcp-kv-${suffix}')

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

// Formalizes an identity that was previously created manually in Azure for
// GitHub Actions OIDC login (see .github/workflows/deploy-function.yml).
// Managed Identity creation is idempotent by name, so this brings the
// existing identity under IaC management without disrupting it or changing
// its principalId/clientId — GitHub Actions keeps working unmodified.
module githubOidc 'modules/github-oidc.bicep' = {
  name: 'github-oidc-deployment'
  params: {
    location: location
  }
}

// Azure AI Search service is NOT deployed via a module here — the Free tier
// allows only 1 per subscription, this PoC's search service already exists
// (created in an earlier run before Key Vault failed and blocked the rest),
// and re-declaring it as a fresh resource hits a known preflight-validation
// bug where the Free-tier quota check fires even for an already-owned,
// identical resource. Referencing it as `existing` (below, in the RBAC
// section) sidesteps this entirely — same pattern as the pre-existing
// Foundry resource.

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
    // uksouth and eastus both reported 0 compute quota on this subscription
    // (root cause turned out to be an unregistered Microsoft.Compute
    // resource provider, since fixed) — ukwest already had working quota
    // when this was deployed, so it stayed here rather than reverting.
    location: 'ukwest'
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

// Must match the Python function's decorator name in function_app.py exactly.
var targetFunctionName = 'process_new_document'

resource existingSystemTopic 'Microsoft.EventGrid/systemTopics@2024-06-01-preview' existing = {
  name: systemTopicName
}

// Native `AzureFunction` destination (resourceId reference) instead of a
// `WebHook` destination with a manually-retrieved system key. WebHook
// destinations validate the live endpoint at subscription-creation time,
// which would have meant the function had to already exist and be running
// code first — a two-phase deployment. AzureFunction destinations reference
// the function by resource ID rather than calling it, so that constraint
// doesn't apply. This reconciles into IaC an Event Grid subscription that,
// until now, only existed as a manual change made directly in Azure.
resource eventGridSubscription 'Microsoft.EventGrid/systemTopics/eventSubscriptions@2024-06-01-preview' = {
  parent: existingSystemTopic
  name: 'regulatory-document-created'
  properties: {
    destination: {
      endpointType: 'AzureFunction'
      properties: {
        resourceId: '${functionApp.outputs.functionAppId}/functions/${targetFunctionName}'
        maxEventsPerBatch: 1
        preferredBatchSizeInKilobytes: 64
      }
    }
    filter: {
      includedEventTypes: [
        'Microsoft.Storage.BlobCreated'
      ]
      subjectBeginsWith: '/blobServices/default/containers/regulatory-documents/blobs/'
    }
    eventDeliverySchema: 'EventGridSchema'
    retryPolicy: {
      // Matches the values already tuned and running in Azure (surfaced by
      // `what-if` as a diff against this file's original, tighter defaults):
      // generous enough for active PoC debugging, where a while can pass
      // between an upload and noticing/fixing an issue.
      maxDeliveryAttempts: 30
      eventTimeToLiveInMinutes: 1440
    }
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

// --- Roles below are for the GitHub Actions deployment identity, not the
// Function App's own identity. Double-check these four GUIDs with
// `az role definition list --name "<role name>"` before relying on them —
// unlike the roles above (already deployed and confirmed working), these
// are new and only verified against documentation, not a live deployment.
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var websiteContributorRoleId = 'de139f84-1756-47ae-9be6-808fbbe84772'
var searchServiceContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'

resource existingStorage 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

resource existingSearch 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: searchServiceName
}

resource existingKeyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// For the Website Contributor role assignment below — the GitHub Actions
// workflow calls `az functionapp config appsettings set` and `az functionapp
// restart`, which need this scope specifically, not just Storage.
resource existingFunctionAppSite 'Microsoft.Web/sites@2023-01-01' existing = {
  name: functionAppName
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

// --- RBAC for the GitHub Actions deployment identity. Least-privilege
// per concrete need in deploy-function.yml / the future indexing workflow —
// same principle as the Function App's own roles above, just a different
// principal and a fixed guid seed (githubOidc's own resource name is fine
// here since, unlike principalId, the module name is deterministic).

resource githubStorageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(existingStorage.id, 'github-deploy', storageBlobDataContributorRoleId)
  scope: existingStorage
  properties: {
    principalId: githubOidc.outputs.identityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
  }
}

// Needed for `az functionapp config appsettings set` / `az functionapp
// restart` / syncfunctiontriggers in deploy-function.yml.
resource githubWebsiteRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(existingFunctionAppSite.id, 'github-deploy', websiteContributorRoleId)
  scope: existingFunctionAppSite
  properties: {
    principalId: githubOidc.outputs.identityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', websiteContributorRoleId)
  }
}

// For the not-yet-built indexing workflow (scripts/index_policies.py run via
// GitHub Actions) to create/update the search index and upload documents.
resource githubSearchServiceRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(existingSearch.id, 'github-deploy', searchServiceContributorRoleId)
  scope: existingSearch
  properties: {
    principalId: githubOidc.outputs.identityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
  }
}

resource githubSearchIndexRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(existingSearch.id, 'github-deploy', searchIndexDataContributorRoleId)
  scope: existingSearch
  properties: {
    principalId: githubOidc.outputs.identityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleId)
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

// Same role, different principal: the future indexing script (run via
// GitHub Actions) needs to call Foundry's embedding deployment directly,
// same as the Function App runtime does.
module githubFoundryRoleAssignment 'modules/foundry-role-assignment.bicep' = {
  name: 'github-foundry-role-assignment-deployment'
  scope: resourceGroup(foundryResourceGroupName)
  params: {
    foundryAccountName: foundryAccountName
    principalId: githubOidc.outputs.identityPrincipalId
    functionAppNameForGuidSeed: 'github-deploy'
  }
}

output functionAppName string = functionApp.outputs.functionAppName
output functionAppPrincipalId string = functionApp.outputs.principalId
output storageAccountName string = storage.outputs.storageAccountName
output searchServiceName string = searchServiceName
output keyVaultName string = keyVault.outputs.keyVaultName
output eventGridSystemTopicName string = eventGridTopic.outputs.systemTopicName
output githubIdentityClientId string = githubOidc.outputs.identityClientId
output githubIdentityPrincipalId string = githubOidc.outputs.identityPrincipalId
