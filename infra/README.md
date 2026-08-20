# Infrastructure (Bicep)

Not yet built — this is stage 3 of the implementation plan.

Will contain:
- `main.bicep` (resource-group scoped)
- `modules/storage.bicep`
- `modules/search.bicep` (Free tier)
- `modules/function-app.bicep` (Consumption plan)
- `modules/event-grid.bicep` (System Topic + Subscription, blob-created events)
- `modules/key-vault.bicep`
- `modules/app-insights.bicep`
- `main.bicepparam`

Deployment will use `az deployment group what-if` before every `create`, and the
whole resource group is designed to be disposable: `az group delete --name
rg-regchange-poc --yes` tears everything down with zero idle cost afterward.
