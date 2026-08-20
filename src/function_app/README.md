# Function App — pipeline

Not yet built — this is stage 2 of the implementation plan.

Will contain an Event Grid–triggered Azure Function (Python v2 model) wrapping:

- `pipeline/models.py` — pydantic schemas: `RegulatoryRequirement`, `Citation`,
  `ImpactHypothesis`
- `pipeline/extract.py` — Requirement Extraction (Foundry, cheap model tier)
- `pipeline/retrieve.py` — RAG retrieval against Azure AI Search
- `pipeline/analyze.py` — citation-grounded Impact Hypothesis (Foundry, stronger
  model tier)
- `requirements.txt`

Local development will run against the Azurite storage emulator and real (but
cheap) Foundry calls — no need to deploy anything to Azure just to iterate on
pipeline logic.
