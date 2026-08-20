param workspaceName string
param location string = resourceGroup().location

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    // Shortest allowed retention keeps this at (or very near) $0 for PoC-scale
    // log volume, and avoids accumulating a paid retention tail after teardown.
    retentionInDays: 30
  }
}

output workspaceId string = logAnalytics.id
