@description('Name of the User-Assigned Managed Identity used by GitHub Actions for OIDC login')
param identityName string = 'regchange-poc-github-deploy'

param location string = resourceGroup().location

@description('GitHub org/user and repo, e.g. TaniaAsh/regchange-poc')
param githubRepo string = 'TaniaAsh/regchange-poc'

@description('Branch this identity is trusted for — matches deploy-function.yml\'s push trigger')
param githubBranch string = 'main'

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

// Standard GitHub Actions OIDC subject format for "this workflow was
// triggered by a push to this branch". Matches deploy-function.yml's
// `on: push: branches: [main]` trigger.
resource federatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: identity
  name: 'github-actions-${githubBranch}'
  properties: {
    issuer: 'https://token.actions.githubusercontent.com'
    subject: 'repo:${githubRepo}:ref:refs/heads/${githubBranch}'
    audiences: [
      'api://AzureADTokenExchange'
    ]
  }
}

output identityId string = identity.id
output identityPrincipalId string = identity.properties.principalId
output identityClientId string = identity.properties.clientId
