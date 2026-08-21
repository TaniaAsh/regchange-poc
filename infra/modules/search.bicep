@description('Globally unique search service name')
param searchServiceName string

param location string = resourceGroup().location

// Free tier: single-tenant-shared infra, no SLA, one per subscription, no
// semantic ranker. That last point matters — see search_client.py, which
// deliberately does NOT request semantic ranking so this stays compatible
// with the Free tier. Upgrading to Basic later only requires changing this
// one 'sku.name' value, not touching application code.

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchServiceName
  location: location

  sku: {
    name: 'free'
  }

  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'

    // Keep API keys enabled for the PoC, but also allow Microsoft Entra ID
    // authentication so the Function App can access Search via Managed Identity.
    disableLocalAuth: false

    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

output searchServiceName string = searchService.name
output searchServiceId string = searchService.id
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
