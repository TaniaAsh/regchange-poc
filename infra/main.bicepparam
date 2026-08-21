using 'main.bicep'

param baseName = 'regchangepoc'
param location = 'uksouth'

param foundryResourceId = '/subscriptions/cd8237a1-a303-489a-82f0-47d248785661/resourceGroups/rg-foundry-test-us/providers/Microsoft.CognitiveServices/accounts/tania-foundry-rag-us-01'
param foundryResourceGroupName = 'rg-foundry-test-us'
param foundryEndpoint = 'https://tania-foundry-rag-us-01.cognitiveservices.azure.com/'

param foundryApiVersion = '2024-10-21'
// gpt-4o not deployed on this resource yet — using gpt-5-mini for both steps
// to prove the end-to-end pipeline first. Swap foundryModelAnalysis to a
// stronger deployment later with zero infra changes (it's just a string).
param foundryModelExtraction = 'gpt-5-mini'
param foundryModelAnalysis = 'gpt-5-mini'