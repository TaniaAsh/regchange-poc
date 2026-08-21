# Infrastructure (Bicep)

## What this deploys

`main.bicep` deploys everything in one pass: Storage, AI Search (Free tier —
`authOptions.aadOrApiKey` is set in the module so Managed Identity works
against it), Function App (Consumption), Key Vault, App Insights, Event Grid
(System Topic + Subscription, using the native `AzureFunction` destination
type), and all RBAC role assignments.

An earlier version of this deploy required a manual two-phase process for
the Event Grid subscription specifically, because a `WebHook` destination
validates the live endpoint at creation time — the function had to already
exist and be running code first. Switching to the `AzureFunction` native
destination type (which references the function by resource ID rather than
calling it) removed that constraint, and the subscription is now a normal
resource in `main.bicep` (`eventGridSubscription`) rather than a separate
deployment. `event-grid-subscription.bicep` is kept in the repo for
reference but is no longer part of the deploy path.

## Deploying

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

The function app needs actual code running (from `src/function_app/`), not
just an empty shell — see `.github/workflows/deploy-function.yml`, or run
locally:

```bash
cd ../src/function_app
func azure functionapp publish <functionAppName-from-output>
```

## Known limitation: Azure AI Search Free-tier redeploys

If this PoC's search service already exists (it does, in this repo's default
state — see the comment in `main.bicep`), re-enabling the search module for
a fresh `deployment group create` can hit a known preflight-validation bug
where the Free-tier quota check fires even for an already-owned, identical
resource. It's referenced as `existing` instead specifically to avoid this.
This only matters if you ever need to change a Search property in Bicep for
an already-existing service — in that case, a direct `az search service
update` for that one property is the pragmatic fallback, same as how
`authOptions` was originally applied here before being backfilled into the
module as documentation of the correct state.

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