# How this PoC relates to the full platform architecture

This repo is a deliberately minimal slice of a larger architecture: a Regulatory
Change Impact Analysis Platform built around the principle of **deterministic
workflow with bounded AI components** (see the Two Loops diagram and ADR-1).

Full design materials (C4 diagrams, Azure deployment view, RAG architecture,
governance map, ADRs, technology decisions) live outside this repo. This document
is the bridge between the two.

## What the PoC proves

The riskiest, most differentiating part of the architecture is not the workflow
orchestration — it's whether the AI component can produce a **citation-grounded**
impact hypothesis (ADR-6: every hypothesis carries both an external regulatory
citation and an internal policy citation) without hallucinating a match that isn't
really there. That's what this PoC tests, end to end, against real regulatory text.

## What the PoC deliberately leaves out, and why

| Left out | Why | Where it lives in the full design |
|---|---|---|
| Bounded Agent (Foundry Agent Service) | It's explicitly an *exception path* (ADR-1) — proving the deterministic path first is the priority; there's no accumulated ambiguous-case volume yet to justify or evaluate an agent | Analysis Loop diagram, ADR-1, ADR-9 |
| Knowledge Graph (Cosmos DB Gremlin) | Belongs to secondary impact analysis in the Remediation Loop, one stage past what "reasoning process" needs to demonstrate | Remediation Loop diagram, ADR-4 |
| VNet + Private Endpoints | Real cost and deployment complexity with no PoC-scale demonstration value | Azure Deployment View, Technology Decisions |
| GRC integration | No real external system to integrate with in a PoC | Governance map, ADR-3 |
| Durable Functions fan-out orchestration | A handful of requirements doesn't need a fan-out orchestrator to prove the point; a direct loop over requirements is enough at this scale | Analysis Loop diagram |

## Mapping PoC components to the architecture

| PoC component | Architecture equivalent | ADR / diagram |
|---|---|---|
| `pipeline/extract.py` | Requirement Extraction | Analysis Loop, step 3 |
| `pipeline/retrieve.py` + Azure AI Search | RAG Retrieval | RAG Architecture (Query-Time Retrieval) |
| `pipeline/analyze.py` | LLM Impact Analysis | Analysis Loop, step 7; ADR-6 |
| Event Grid blob trigger | Change Event | RAG Architecture (Indexing Pipeline, step 1) |
| `requires_human_confirmation: true` on every output | Human-in-the-loop confirmation gate | Two Loops (Compliance Decision); ADR-7 |
| Managed Identity, no keys in code | Security boundary | ADR-5 |
| Bicep, deployed via GitHub Actions OIDC | Infrastructure as Code decision | Technology Decisions |

## What a "pass" looks like

For each synthetic requirement extracted from the EU AI Act excerpts, the pipeline
should produce one of:

- A hypothesis with **both** citations populated and a defensible reasoning trace
  — even if the match is partial (the synthetic policies were written with
  deliberate gaps, so partial matches are the expected, correct outcome for some
  requirements, not a bug)
- An explicit **no-impact** result with the evidence that was checked, per the
  same "no impact still requires human confirmation" principle as the full
  architecture (ADR-7)

A result that confidently claims a full match against a policy that doesn't
actually cover the requirement is the one outcome that would indicate the
citation-grounding approach isn't working.

## Known issues found during testing

Kept here deliberately rather than quietly fixed and forgotten — these are
genuine findings about the architecture's weak points, and "AI is not the
system of record" (the platform's core thesis) is easier to defend in an
interview with real examples than in the abstract.

- **Extraction is not fully deterministic.** The same Article 9 text
  produced 14 requirements on one run and 16 on another, at
  `temperature=0`. Reasoning-model extraction apparently isn't perfectly
  reproducible even with temperature pinned to zero. Not yet fixed —
  candidate fixes are a structured output schema with explicit numbering,
  stable requirement IDs anchored to source paragraph/point references,
  and a validation/deduplication pass. Direct, concrete evidence for why
  extracted requirements are treated as a hypothesis needing downstream
  validation, not ground truth.

- **`requirement_id` collided across separately-uploaded regulatory
  documents that shared the same `document_id`.** Articles 9, 13, and 15
  were all given `document_id: EU-AI-ACT-2024-1689` (the regulation
  number) in their frontmatter, since they're all part of the same
  regulation — but `extract.py` builds each requirement's ID as
  `{document_id}-R{n}`, so uploading a second article overwrote the first
  article's `impact-hypotheses/*.json` blobs under the same names (R1,
  R2, ...). Fixed by making `document_id` unique per source document
  (`EU-AI-ACT-2024-1689-ART9`, `-ART13`, `-ART15`), not just per
  regulation. If this is ever generalized beyond a fixed set of manually
  curated source files, `document_id` should be derived automatically
  (e.g. from the blob name plus an ingestion timestamp) rather than
  relying on whoever writes the frontmatter to remember uniqueness.

