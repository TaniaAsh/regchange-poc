# Architecture Decision Records

Architecture decisions for the Regulatory Change Impact Analysis Platform, organized in three tiers instead of one flat list.

- **Principles**: short, stated once, and deliberately not dressed up as a mechanism. They shape the platform but do not have real alternatives that were weighed against each other.
- **Core Architecture ADRs**: the decisions that define the platform's shape. Each one names the real options considered, the decision, why, the cost of that decision, a known failure mode, and what would make us revisit it.
- **Technical ADRs**: the same format, one level more concrete, usually naming a specific Azure service or mechanism.

Each Core and Technical ADR also carries a status:

- **PoC confirmed**: built and actually tested against live data.
- **Partial**: half built, with a real gap named honestly.
- **Target only**: a decision made on paper, not built yet.

---

## Principles

**Confidence is a hint, not a probability.** The model's confidence score tells you how sure it sounds, not how likely it is to be correct. These numbers are not calibrated, so nobody should set an auto-approve threshold based on them alone.

**Data classification and residency come before ingestion.** Before a new kind of document is allowed into the pipeline, someone has to classify it and approve it for use with AI, inside an approved part of the cloud. This is a precondition on the whole platform, not something the platform decides on its own.

**Observability is a target, not yet a number.** Each component should have its own health signal instead of one check for the whole platform. The actual latency, throughput and error budgets are not defined yet. Writing them down before they exist would be guessing, and a guessed number is worse than an honest blank.

---

## Core Architecture ADRs

### C1: Requirement as the unit of analysis

**Status:** PoC confirmed, with a known gap (see failure mode)

**Context:** A single regulatory article can bundle several distinct obligations together, a governance requirement, a data requirement, a monitoring requirement, each with a different owner and different systems affected.

**Options considered:**
- Treat the whole document as one unit and produce one summary of impact
- Treat each requirement inside the document as its own unit, with its own ID and its own lifecycle

**Decision:** Extract atomic requirements from each document, each with a stable ID, and analyze each one separately.

**Why:** A whole-document summary loses exactly the detail a compliance analyst needs, which specific obligation is affected, and who owns fixing it. Requirement-level granularity is what makes the platform useful for actual remediation work, not just a reading aid.

**Consequence:** One document can produce dozens of requirement records instead of one. More objects to track, more storage, more orchestration, in exchange for a real traceability chain from regulation down to owner.

**Failure mode:** Extraction is not fully deterministic. The same document produced 14 requirements on one run and 16 on another, from identical input. A requirement's ID needs to stay stable across a re-extraction for this whole model to hold up. Right now it does not.

**Revisit trigger:** Once extraction is made structurally stable (a fixed schema, numbering tied to source paragraph references, or a validation and deduplication pass), requirement IDs should become genuinely stable and this failure mode closes.

---

### C2: Deterministic workflow, with a bounded agent for ambiguous cases only

**Status:** PoC confirmed for the deterministic path. The agent path is target only.

**Context:** A fully autonomous agent could investigate a hard case using its own judgment about what to check next. That is flexible, but also unpredictable, expensive to run, and hard to explain to a regulator afterward.

**Options considered:**
- Let an agent run the whole pipeline, deciding its own steps
- Run a fixed, known workflow for everything, with no agent at all
- Run a fixed workflow by default, and hand a case to a bounded agent only when the deterministic path cannot resolve it

**Decision:** The deterministic workflow is the default path for every requirement. An agent is only invoked for the ambiguous or insufficient-evidence case, and even then it runs inside hard limits: a fixed allow-list of tools, a maximum number of tool calls, a token budget, and a timeout, enforced by the runtime, not requested through a prompt. If it exceeds any of those, it stops and hands the case to a human.

**Why:** Most requirements do not need investigation. They need extraction, retrieval, and comparison, which a fixed workflow does well and predictably. Reserving the agent for genuinely hard cases keeps the common path auditable and keeps the agent's blast radius small on the rare path where it runs at all.

**Consequence:** The agent may give up on a hard case and hand it to a human instead of resolving it alone. That is a safe outcome, not a failure. Widening what the agent is allowed to do later has to be based on evidence from cases it already resolved correctly, not granted by default over time.

**Failure mode:** If the tool allow-list, budget, or timeout only exist as instructions inside a prompt, they are not real limits. A prompt is not a security boundary.

**Revisit trigger:** Once there is enough confirmed history of ambiguous cases the agent resolved correctly, its scope can be widened, deliberately, based on that evidence.

---

### C3: Retrieval separated from reasoning, both measured on their own

**Status:** PoC confirmed for the split itself. Evaluation methodology is target only.

**Context:** If a final answer is wrong, we need to know whether search returned the wrong evidence, or whether the model misread good evidence. One combined call would make that impossible to tell apart.

**Options considered:**
- One combined call: give the model the whole policy corpus and the requirement, let it find and reason in one step
- Two separate steps: a search step returns candidate evidence, a reasoning step judges it

**Decision:** Retrieval and reasoning are two separate steps. Retrieval uses hybrid search, keyword plus vector, because regulatory and policy text mixes exact identifiers (article numbers, policy IDs, named controls) with general semantic meaning, and neither keyword nor vector search alone handles both well. How many candidates come back (top-K) is a tuning parameter measured against real data, not a number picked in advance. A reranker is added only if evaluation shows it actually helps.

**Why:** Separating the steps means a bad result can be traced to its real cause, and each half can be improved without touching the other.

**Consequence:** More infrastructure than one call, an index, embeddings, a retrieval step, and an evaluation practice to go with it. Retrieval quality is measured with Recall@K, Precision@K, and something like nDCG. Reasoning quality is measured separately: classification accuracy, whether citations are actually correct, how often the model makes an unsupported claim. End to end, the number that matters most is the missed-impact rate, how often a real obligation was never flagged at all.

**Failure mode:** If the correct evidence exists but is ranked outside the top-K, that is a retrieval failure, not a reasoning failure. The fix is a bigger K, better chunking, or metadata filters, not a different reasoning prompt.

**Revisit trigger:** Top-K, the reranker choice, and the chunking strategy should all be tuned once there is a labelled set of requirement-to-policy pairs to measure Recall@K against, rather than left as an initial guess.

---

### C4: External citation is mandatory, internal is a citation or an explicit absence of evidence

**Status:** PoC confirmed and tested against live data

**Context:** An earlier version of this decision said every hypothesis needs a citation on both sides. That is wrong as written. A correct "no impact" or "not enough evidence" result should never be forced to invent a fake internal citation just to satisfy the rule.

**Options considered:**
- Require both citations always, and treat their absence as an error
- Require the external citation always, and require the internal side to be either a real citation, or an explicit, structured statement that no matching evidence was found

**Decision:** The external citation, which regulation, which article, is always mandatory. The internal side is either a specific policy citation, or an explicit "no internal evidence found" result. Both are valid, checked outcomes. Silence is not.

**Why:** A hypothesis that quietly has no internal citation and no explanation looks like a bug. A hypothesis that clearly says "we checked, and nothing in our policies covers this" is exactly the finding a compliance analyst needs to see.

**Consequence:** The code, not just the prompt, enforces this. If the model claims a match but does not name a specific policy and section, that claim is downgraded rather than trusted as is.

**Failure mode:** If this check only lived in the prompt, a model that ignores instructions could still produce an unsupported claim that looks confident. This has already happened once in testing, and the code-level check downgraded it correctly instead of passing it through.

**Revisit trigger:** If the platform ever needs more than one internal citation per hypothesis, this becomes a list, without changing the mandatory-external, explicit-absence-allowed rule underneath it.

---

### C5: AI produces a hypothesis, a human and GRC produce the decision

**Status:** PoC confirmed and tested, including live no-impact cases

**Context:** The AI cannot see everything that might matter to a real compliance decision, a legal exception, a compensating control, something the bank already agreed with the regulator. Only a human has that full picture.

**Options considered:**
- Let the AI's classification become the final record directly
- Require human review only for cases the AI flags as uncertain
- Require human confirmation for every hypothesis, including ones the AI itself considers a clear "no impact"

**Decision:** Every hypothesis moves through the same review states: proposed, then confirmed, rejected, modified, or sent for further investigation. None of those states are reached without a human action. The AI's classification is a hypothesis field, never a final decision field.

**Why:** The two possible mistakes are not equally expensive. A false "potential impact" costs an analyst a few minutes. A false "no impact" that goes unnoticed is a real regulatory gap. The system is built to make the second mistake harder to make silently.

**Consequence:** More manual review overall, including review of cases the AI is confident are fine. That is the intended cost, not an inefficiency to remove later.

**Failure mode:** If this were enforced only by convention, a future change could accidentally treat "no impact proposed" as good enough to close without review. This is why the field itself is hardcoded to always require confirmation, not left as a default a caller could override.

**Revisit trigger:** This does not change because the model's confidence improves. It changes, if ever, based on a deliberate decision by compliance about which narrow categories of case are safe to auto-close, not a decision made by engineering.

---

### C6: GRC is the system of record, the Knowledge Graph is a relationship layer

**Status:** Target only, not built in this PoC

**Context:** A bank already has a real GRC platform holding the audit trail for confirmed impacts, issues, and remediation. A Knowledge Graph could tempt a team into treating it as a second, richer source of truth.

**Options considered:**
- Build the Knowledge Graph as the platform's own authoritative record of impact status
- Keep GRC as the sole authoritative record, use the Knowledge Graph only for relationships

**Decision:** GRC is the only place a confirmed impact or remediation status is authoritative. The Knowledge Graph stores relationships, which policy connects to which control connects to which system, and supports multi-hop questions, but never overrides or duplicates what GRC says about status.

**Why:** A second source of truth is organizationally expensive to unwind later, and creates exactly the confusion regulators ask about: which system do we actually trust.

**Consequence:** Confirmed impact status has to be written to GRC through a real integration, asynchronous and durable, a queued write with retry and reconciliation, not a single synchronous call that either fully succeeds or is silently lost.

**Failure mode:** If the write to GRC fails and the platform has already marked the case closed locally, the two systems disagree, and nobody notices until an audit asks GRC a question and gets the wrong answer.

**Revisit trigger:** Once a real GRC integration exists, the actual consistency model, how quickly a local confirmation appears in GRC, and what happens during a GRC outage, needs to be validated against GRC's real API, not assumed.

---

### C7: Security trimming filters by the requester's entitlements, not the service's identity

**Status:** Target only, not exercised in this PoC

**Context:** The pipeline's own identity can read everything in the search index. Filtering access based on that identity filters nothing, because the service is not the one whose permissions should matter.

**Options considered:**
- Trust the model to only mention content it should, based on a prompt instruction
- Filter after the model has already generated an answer
- Filter before retrieval, using the actual requesting user's entitlements, not the service identity

**Decision:** Every document carries access-control metadata, which groups or entitlements can see it. A search query carries the actual requester's entitlement, and the search filter checks that before anything is retrieved. The service-to-service identity used to call Search is separate from, and irrelevant to, this filter.

**Why:** A prompt telling a model not to repeat restricted content is a request, not a boundary. Filtering at the data layer means restricted content is never retrieved into context in the first place.

**Consequence:** Documents need real entitlement metadata at indexing time, and the calling application needs a way to know and pass along the requester's actual entitlements, not just its own service identity. Real design work, not a checkbox.

**Failure mode:** This PoC has exactly one user and no real multi-tenant boundary, so this has never actually been exercised. It is a documented target, not a tested one.

**Revisit trigger:** The first time a second distinct user role is introduced, for example a business-unit-scoped analyst who should not see another unit's policies, this needs to move from documented target to tested reality before that second role goes live.

---

### C8: No static secrets for data-plane calls, and workload identities are scoped by function

**Status:** Partially confirmed. Managed Identity and no-secrets are built and tested. Storage separation is a named gap.

**Context:** Every service authenticates using Managed Identity rather than a stored key. But a Managed Identity is not automatically narrow. This PoC's runtime Function currently has broad access across the entire storage account, because the same account hosts both the Functions runtime's own operational data and the platform's actual business data.

**Options considered:**
- One shared storage account and one identity for both the runtime's own operational needs and the business data
- Separate the Functions host storage from the business-data storage, and scope each identity to only what it needs

**Decision:** No component authenticates with a static secret for a data-plane call, full stop. Beyond that, the target design separates the storage account the Functions runtime uses for itself from the storage account holding regulatory documents and hypotheses, so the runtime identity can be scoped to specific containers instead of the whole account. The identity that runs the pipeline day to day is already separate from the identity permitted to update the search index or deploy new code. That part is built and tested.

**Why:** "No secrets" removes an entire category of risk, a leaked key, but it is not the same claim as least privilege. Narrow, container-level, purpose-specific access is what actually limits what a compromised identity could do.

**Consequence:** More identities and role assignments to design and maintain, and in the target design, a second storage account to manage.

**Failure mode:** Right now, if the runtime identity were ever compromised, it could read or write anything in the storage account, not just the two containers it actually needs. That is a real, named gap between the current PoC and the target design.

**Revisit trigger:** This should be fixed before any production rollout. It is a well understood, mechanical change, a second storage account plus narrower role assignments, not a research question.

---

### C9: A real operational database for workflow state, object storage only for immutable evidence

**Status:** Target only. The PoC stores everything as blob JSON with no queryable state.

**Context:** Real use of this platform needs to answer questions like "show all open hypotheses," "find every requirement tied to Article 9," or "lock this case while an analyst edits it." A standalone JSON file per hypothesis answers none of those without listing and parsing every file.

**Options considered:**
- Keep using blob storage as the only place hypothesis and requirement data lives
- Cosmos DB, a queryable, flexible-schema operational store
- Azure SQL, a queryable, relationally-structured operational store
- Treat GRC as the only place any of this is queryable, once an impact is confirmed

**Decision:** Blob storage keeps its role as the immutable archive, the original source text and the evidence fragments actually used at decision time. A real operational database, most likely Cosmos DB to match the rest of the platform's document-shaped data, holds requirements, hypotheses, and workflow state as genuinely queryable records. GRC remains the only authoritative record once something is confirmed. The Knowledge Graph holds relationships, as already decided separately.

**Why:** Object storage is good at "give me this exact file by name." It is bad at "give me every open case for this article" or "lock this record." Those are database questions, and pretending otherwise just means writing a slow, fragile database on top of blob listings.

**Consequence:** A new stateful service to run and back up, and a real schema to design and migrate, instead of files with no schema at all.

**Failure mode:** There is currently no way to answer "show me everything pending review" without downloading and parsing every file in the container.

**Revisit trigger:** This should move from blob-only to a real operational store before the platform handles enough concurrent cases that listing and parsing every file becomes noticeably slow, which for a real bank's document volume happens quickly.

---

### C10: A new embedding model version gets a new index version, switched over deliberately

**Status:** Target only. The PoC has only ever had one index version.

**Context:** Updating an existing search index in place, when the embedding model changes, risks silently breaking search quality with no way back if something goes wrong.

**Options considered:**
- Update the existing index in place when the embedding model changes
- Build a new index version alongside the old one, switch over once validated

**Decision:** A new embedding model gets a new, separate index. Traffic switches to the new index through an alias, only after the new index has been validated against a known set of queries. The old index stays available for a defined rollback window before retirement.

**Why:** A destructive in-place update cannot be undone if the new embeddings turn out worse. A separate version can be tested first and rolled back cheaply if needed.

**Consequence:** Running two index versions for a period costs more in storage and re-embedding compute, and needs a defined validation step before cutover.

**Failure mode:** The cutover process itself, the alias mechanism, and the rollback path have not actually been exercised yet, since there has only ever been one index version.

**Revisit trigger:** The first real embedding model upgrade is the point this needs to be tested for real, not just documented.

---

## Technical ADRs

### T1: Event Grid direct to Function, with idempotent processing

**Status:** PoC confirmed for the trigger itself. Idempotency handling is a named gap.

**Context:** Regulatory documents arrive unpredictably, not on a schedule, and downstream processing can be slow relative to how fast new documents might arrive.

**Options considered:**
- Poll storage on a schedule for new files
- Event Grid delivering directly to the Function
- Event Grid delivering to a Service Bus queue, with the Function consuming from the queue

**Decision:** At this scale, Event Grid delivers directly to the Function. Event Grid's own delivery guarantee is at-least-once, not exactly-once, so processing has to be idempotent on its own: a stable business key is checked before writing a new hypothesis, so reprocessing the same event does not produce a duplicate or conflicting record.

**Why:** Event Grid is a strong fit for "notify me when something changes," and the simplest option that still gives an event-driven design rather than a polling one. It does not provide buffering or backpressure on its own, which matters more at higher volume than this PoC has tested.

**Consequence:** If document arrival ever bursts, or the model or search service starts throttling under load, there is nothing between Event Grid and the Function to absorb that.

**Failure mode:** A duplicate event delivery is expected, not exceptional. If idempotency is not correctly implemented, a duplicate delivery produces a duplicate or conflicting hypothesis silently.

**Revisit trigger:** If real document volume starts to burst, or throttling becomes a regular occurrence, add a Service Bus queue between Event Grid and processing, for durable buffering, dead-lettering, and controlled concurrency. Event Grid stays for event detection either way, Service Bus would be the durable work queue added on top, not a replacement.

---

### T2: Single function loop for the PoC, bounded fan-out orchestration for production

**Status:** PoC confirmed as is. Production direction decided, not built.

**Context:** A single regulatory document can produce dozens to hundreds of requirements. A simple sequential loop, as this PoC uses, works fine at PoC scale and will not work at production scale.

**Options considered:**
- Keep a simple sequential loop inside one function
- Durable Functions, for explicit workflow state, fan-out and fan-in, and built-in retry per step
- Service Bus with independent competing-consumer workers, for looser coupling and direct control over backpressure

**Decision:** The PoC keeps the simple sequential loop on purpose, since building fan-out orchestration before there is a real volume problem would be solving a problem that does not exist yet. The production direction is bounded fan-out and fan-in orchestration, most likely Durable Functions, given the need for per-requirement retry and a natural way to aggregate a document's requirements back into one review package once they finish.

**Why:** Durable Functions gives explicit, resumable workflow state and fan-out and fan-in as first-class features, a good fit for "process N requirements independently, then assemble one result." Service Bus with independent workers gives better backpressure and looser coupling, but pushes aggregation and end-to-end visibility onto the team to build by hand.

**Consequence:** Production needs real orchestration infrastructure the PoC does not have. The current design will not scale to hundreds of requirements per document without hitting timeouts and losing per-requirement retry granularity.

**Failure mode:** One long-running function processing many requirements sequentially has one shared timeout and one shared failure boundary. One bad requirement can currently affect the whole batch instead of failing on its own.

**Revisit trigger:** Revisit as soon as real document volumes are known, based on actual throughput and latency testing, not assumed in advance. If backpressure and independent scaling matter more than workflow-state visibility, Service Bus workers are the better fit instead.

---

### T3: GRC writes go through a durable outbox and a reconciliation job

**Status:** Target only, no real GRC to test against yet

**Context:** GRC being temporarily unreachable should never mean a confirmed impact is silently lost, and should never mean the platform pretends a write succeeded when it did not.

**Options considered:**
- A synchronous call to GRC at confirmation time, retried a fixed number of times before giving up
- A durable outbox: the confirmation is written locally first, a background process attempts the GRC write with retry, and a reconciliation job periodically checks that every locally-confirmed record actually exists in GRC

**Decision:** Confirmed impacts go through a durable outbox pattern. The local confirmation triggers a queued write to GRC, it is not the GRC write itself. A reconciliation job checks periodically that every local confirmation has a matching GRC record, and flags any that do not.

**Why:** A purely synchronous call that fails after a fixed number of retries either blocks the user or silently drops the write. Neither is acceptable for a regulatory record. A queued write with reconciliation makes "pending" a visible, honest state instead of a hidden failure.

**Consequence:** A confirmed impact can sit visibly pending for a while during a GRC outage, instead of appearing to complete instantly.

**Failure mode:** Without the reconciliation job specifically, a write that silently failed after retries were exhausted would look identical to one that succeeded, from the platform's own point of view.

**Revisit trigger:** Worth testing directly against GRC's actual API once a real integration exists, since GRC's own retry and idempotency behavior on the receiving end shapes exactly how this should be implemented.
