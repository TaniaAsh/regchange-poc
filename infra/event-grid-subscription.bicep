@description('Name of the already-deployed Event Grid System Topic (from main.bicep output)')
param systemTopicName string

@description('The full webhook URL including the Event Grid extension system key. See README.md in this folder for how to obtain it.')
@secure()
param functionWebhookUrl string

resource systemTopic 'Microsoft.EventGrid/systemTopics@2024-06-01-preview' existing = {
  name: systemTopicName
}

resource subscription 'Microsoft.EventGrid/systemTopics/eventSubscriptions@2024-06-01-preview' = {
  parent: systemTopic
  name: 'regulatory-document-created'
  properties: {
    destination: {
      endpointType: 'WebHook'
      properties: {
        endpointUrl: functionWebhookUrl
      }
    }
    filter: {
      includedEventTypes: [
        'Microsoft.Storage.BlobCreated'
      ]
      subjectBeginsWith: '/blobServices/default/containers/regulatory-documents/'
    }
    eventDeliverySchema: 'EventGridSchema'
    retryPolicy: {
      maxDeliveryAttempts: 5
      eventTimeToLiveInMinutes: 60
    }
  }
}
