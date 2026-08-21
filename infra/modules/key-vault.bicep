@description('Globally unique Key Vault name')
param keyVaultName string

param location string = resourceGroup().location
param foundryEndpoint string
param searchEndpoint string

// This PoC uses Managed Identity for every service-to-service call (Storage,
// Search, Foundry) — there are no API keys to store. Key Vault's job here is
// narrower: it's the single place non-secret-but-still-centralized config
// (service endpoints) lives, pulled into the Function App via Key Vault
// references rather than hardcoded App Settings. It's provisioned mainly to
// have the pattern in place for the day something *does* need a real secret.
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    // Soft-delete cannot be disabled on current API versions, but purge
    // protection can be — deliberately off here. A PoC resource group gets
    // deployed and torn down repeatedly; with purge protection on, a
    // deleted vault blocks reuse of the same name for up to 90 days. Off is
    // the right call for a disposable PoC; a real production Key Vault
    // should have this on.
    enablePurgeProtection: true
  }
}

resource foundryEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'foundry-endpoint'
  properties: {
    value: foundryEndpoint
  }
}

resource searchEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'search-endpoint'
  properties: {
    value: searchEndpoint
  }
}

output keyVaultId string = keyVault.id
output keyVaultName string = keyVault.name
output foundryEndpointSecretUri string = foundryEndpointSecret.properties.secretUri
output searchEndpointSecretUri string = searchEndpointSecret.properties.secretUri
