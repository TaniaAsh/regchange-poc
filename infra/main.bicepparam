using 'main.bicep'

param baseName = 'regchangepoc'
param location = 'uksouth'

// Replace with your existing Foundry resource's details.
// Get these with:
//   az cognitiveservices account show --name <your-foundry-name> \
//     --resource-group <your-foundry-rg> --query id -o tsv
param foundryResourceId = '/subscriptions/<sub-id>/resourceGroups/<foundry-rg>/providers/Microsoft.CognitiveServices/accounts/<foundry-name>'
param foundryResourceGroupName = '<foundry-rg>'
param foundryEndpoint = 'https://<your-foundry-name>.openai.azure.com/'

param foundryApiVersion = '2024-10-21'
param foundryModelExtraction = 'gpt-4o-mini'
param foundryModelAnalysis = 'gpt-4o'
