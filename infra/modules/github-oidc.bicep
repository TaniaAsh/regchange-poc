@description('Name of the User-Assigned Managed Identity used by GitHub Actions for OIDC login')
param identityName string = 'regchange-poc-github-deploy'

param location string = resourceGroup().location

@description('The exact subject claim GitHub issues for this repo. This tenant has GitHub\'s "use repository ID" (immutable identifiers) option enabled, so the subject includes numeric account/repo IDs, not just names — found by inspecting the already-existing federated credential with `az identity federated-credential list`, not guessable generically. Corresponds to TaniaAsh/regchange-poc, branch main.')
param githubSubject string = 'repo:TaniaAsh@10188197/regchange-poc@1341169360:ref:refs/heads/main'

// User-Assigned Managed Identity creation is idempotent by name: if
// `regchange-poc-github-deploy` already exists in this resource group (it
// does — it was created manually before this module existed), this is a
// no-op that returns the same principalId/clientId, not a fresh identity.
// Safe to bring under IaC management without disrupting the GitHub Actions
// setup that already trusts it.
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

// Named and valued to match the already-existing credential exactly (see
// githubSubject above) — this manages the real one in place rather than
// creating a second, non-functional credential alongside it.
resource federatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: identity
  name: 'github-main'
  properties: {
    issuer: 'https://token.actions.githubusercontent.com'
    subject: githubSubject
    audiences: [
      'api://AzureADTokenExchange'
    ]
  }
}

output identityId string = identity.id
output identityPrincipalId string = identity.properties.principalId
output identityClientId string = identity.properties.clientId
