# CI/CD

Not yet built — stage 5. Will contain:

- `deploy-infra.yml` — Bicep `what-if` on every PR touching `infra/**`, deploy on
  merge to `main`. Authenticates to Azure via OIDC federated credential
  (`azure/login@v2` with `client-id` / `tenant-id` / `subscription-id` — no
  `client-secret`, nothing stored in GitHub Secrets beyond those three
  non-sensitive IDs).
- `deploy-function.yml` — zip-deploys the function app on push to
  `src/function_app/**`.
