@description('Name of the existing Microsoft Foundry / Azure OpenAI resource')
param foundryAccountName string
param principalId string

@description('Deterministic name used only to seed guid() — keeps the what-if preview fully calculable, since principalId is a runtime-only value')
param functionAppNameForGuidSeed string

// This module is invoked from main.bicep with an explicit module-level
// `scope: resourceGroup(foundryResourceGroupName)` because the Foundry
// resource already exists in a different resource group from the rest of
// this PoC's resources — role assignments must be declared in the scope of
// the resource they apply to.
resource foundryAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: foundryAccountName
}

var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource foundryRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryAccount.id, functionAppNameForGuidSeed, cognitiveServicesOpenAIUserRoleId)
  scope: foundryAccount
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
  }
}
