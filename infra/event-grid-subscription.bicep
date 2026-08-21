// SUPERSEDED — kept for reference only, not part of the deploy path anymore.
//
// The Event Grid subscription now lives directly in main.bicep, using the
// native `AzureFunction` destination type (resourceId reference) instead of
// this file's `WebHook` destination (manually-retrieved system key). The
// AzureFunction type doesn't validate a live endpoint at creation time the
// way WebHook does, so the two-phase deployment this file was built for
// (function must exist and be running code first) is no longer necessary.
//
// This file is left in place only in case a WebHook-style destination is
// ever needed again (e.g. targeting a non-Function endpoint).

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
