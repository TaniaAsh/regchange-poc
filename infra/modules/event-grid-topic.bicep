@description('Event Grid System Topic name')
param systemTopicName string

param location string = resourceGroup().location
param storageAccountId string

// The System Topic itself has no endpoint to validate, so it's safe to
// deploy in the same pass as everything else. The Subscription (which DOES
// point at an endpoint — the Function App) is deliberately a separate,
// later deployment. See infra/event-grid-subscription.bicep and its
// accompanying comment for why.
resource systemTopic 'Microsoft.EventGrid/systemTopics@2024-06-01-preview' = {
  name: systemTopicName
  location: location
  properties: {
    source: storageAccountId
    topicType: 'Microsoft.Storage.StorageAccounts'
  }
}

output systemTopicName string = systemTopic.name
output systemTopicId string = systemTopic.id
