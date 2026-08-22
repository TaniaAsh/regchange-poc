# CI/CD

All workflows authenticate to Azure via OIDC federated credential
(`azure/login@v2` with `client-id` / `tenant-id` / `subscription-id` from
repo variables — no `client-secret`, nothing stored as a GitHub Secret).
See `infra/modules/github-oidc.bicep` for the identity itself.

- **`deploy-function.yml`** — builds and deploys the Function App on push to
  `src/function_app/**`, via `WEBSITE_RUN_FROM_PACKAGE` (uploads a zip to the
  `function-releases` blob container, points the app at it, restarts, syncs
  triggers).
- **`index-policies.yml`** — builds/updates the `policy-fragments-v1` search
  index and (re-)embeds the synthetic ACME policy documents, on push to
  `data/policies/**` or `scripts/index_policies.py`, or manually via
  `workflow_dispatch`.

`deploy-infra.yml` (Bicep `what-if`/deploy on changes to `infra/**`) is not
yet built — infra changes are currently applied by running `az deployment
group create` directly, not through CI. A reasonable next addition, not
urgent for a PoC.