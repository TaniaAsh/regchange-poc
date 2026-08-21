# Infrastructure (Bicep)

## Why deployment is two phases, not one

`main.bicep` deploys everything except the Event Grid **subscription**: Storage,
AI Search (Free tier), Function App (Consumption), Key Vault, App Insights, the
Event Grid **System Topic**, and all RBAC role assignments.

The Event Grid subscription is deliberately a separate, later step
(`event-grid-subscription.bicep`). This isn't an oversight — Event Grid
validates the destination endpoint (your Function App) *at subscription
creation time*, so the function has to already exist and be running code
before the subscription can be created. Trying to do it in one pass is a
well-known source of "works sometimes, fails on a clean deploy" bugs.

## Phase 1 — everything except the subscription

```bash
az group create --name rg-regchange-poc --location uksouth

# Fill in your Foundry resource details in main.bicepparam first, then:
az deployment group what-if \
  --resource-group rg-regchange-poc \
  --template-file main.bicep \
  --parameters main.bicepparam

az deployment group create \
  --resource-group rg-regchange-poc \
  --template-file main.bicep \
  --parameters main.bicepparam
```

## Deploy the function code

Before phase 2, the function app needs actual code running (from
`src/function_app/`), not just an empty shell — see the top-level repo
README / `.github/workflows/deploy-function.yml` (stage 5) once that exists,
or for now:

```bash
cd ../src/function_app
func azure functionapp publish <functionAppName-from-phase-1-output>
```

## Phase 2 — the Event Grid subscription

Get the webhook URL (includes the Event Grid extension system key):

```bash
az rest --method post \
  --uri "https://management.azure.com/subscriptions/<sub-id>/resourceGroups/rg-regchange-poc/providers/Microsoft.Web/sites/<functionAppName>/host/default/listkeys?api-version=2023-01-01" \
  --query "systemKeys.eventgrid_extension" -o tsv
```

Then the webhook URL is:
```
https://<functionAppName>.azurewebsites.net/runtime/webhooks/eventgrid?functionName=process_new_document&code=<the-key-above>
```

**Simpler alternative**: create this subscription once through the Azure
Portal instead (System Topic → + Event Subscription → Endpoint type "Azure
Function" → pick `process_new_document` from the dropdown). The portal
resolves the system key for you — no manual key retrieval needed. This is
genuinely the lower-risk option for a one-time bootstrap step; automate it
with the Bicep file below only once you've confirmed the exact webhook URL
format works for your deployment.

```bash
az deployment group create \
  --resource-group rg-regchange-poc \
  --template-file event-grid-subscription.bicep \
  --parameters systemTopicName=<from-phase-1-output> functionWebhookUrl='<url-from-above>'
```

## Teardown

```bash
az group delete --name rg-regchange-poc --yes --no-wait
```

Everything in this resource group is disposable by design. One caveat: this
Azure tenant enforces Key Vault purge protection via policy (common
enterprise baseline), so a deleted vault stays soft-deleted for the retention
period and blocks recreating a vault with the same name during that window.
If you hit this after a teardown, delete and recreate the resource group
itself under a new name — the vault name is derived from
`uniqueString(resourceGroup().id)`, so a new resource group name gives every
resource a fresh name automatically.