# Regulatory Change Impact Analysis — PoC

A minimal, low-cost proof of concept for the deterministic-workflow-with-bounded-AI
architecture described in `docs/ARCHITECTURE.md`.

## What this proves

Given a real regulatory document (an excerpt of the EU AI Act) and a handful of
synthetic internal policies, the pipeline:

1. **Extracts** atomic regulatory requirements from the source document (LLM, bounded
   single-call — not an agent).
2. **Retrieves** the internal policy fragments most relevant to each requirement
   (Azure AI Search, hybrid search).
3. **Produces a citation-grounded impact hypothesis** — every hypothesis carries both
   an external (regulatory) and an internal (policy) citation, and is explicitly marked
   as requiring human confirmation before it becomes anything more than a hypothesis.

This is the "reasoning process" slice of the platform, not the whole platform. See
`docs/ARCHITECTURE.md` for what was deliberately left out of the PoC and why.

## Repo layout

```
infra/                  Bicep — infrastructure as code (Storage, AI Search, Function
                         App, Event Grid, Key Vault, App Insights)
src/function_app/        Python Azure Function (Event Grid–triggered pipeline)
  pipeline/               extract.py / retrieve.py / analyze.py / models.py
data/source/              Real regulatory text (EU AI Act excerpts)
data/policies/             Synthetic internal policy documents (Acme Bank, fictional)
tests/                    Unit tests, LLM and Search calls mocked — logic is verified
                          without any live Azure call
.github/workflows/         CI/CD — Bicep deploy (OIDC, no stored secrets) + function
                          code deploy
docs/ARCHITECTURE.md       How this PoC maps to the full platform architecture
```

## Cost

Designed to cost close to $0 to run and demo:

| Resource | Tier | Cost |
|---|---|---|
| Azure AI Search | Free | $0/mo (50MB, 3 indexes — enough for this PoC's policy set) |
| Function App | Consumption (Y1) | $0 within the 1M free executions/month grant |
| Storage, Key Vault, App Insights, Event Grid | Standard | $0 at this volume |
| Azure OpenAI / Foundry | Pay-as-you-go, no free tier | The only real cost — a few cents to low single dollars per full run, using a cheap model (e.g. gpt-4o-mini) for extraction and a stronger model (e.g. gpt-4o) only for the citation-grounded hypothesis step |

Infra is fully torn down between sessions with `az group delete` — no idle cost.

## Prerequisites

- Azure subscription with Microsoft Foundry access
- Azure CLI (`az`), Azure Functions Core Tools, Bicep CLI
- Python 3.11+
- VS Code with the Azure Functions extension (recommended, not required)

## Getting started

See `infra/README.md` for deployment and `src/function_app/README.md` for running
the pipeline locally against the Azurite emulator before deploying anything.
