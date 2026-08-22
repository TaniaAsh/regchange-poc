# Architecture Decision Records

20 architecture decisions for the Regulatory Change Impact Analysis Platform.

Each one has a status:

- **PoC confirmed**: built and actually tested against live data.
- **Partial**: half built, with a real gap named honestly.
- **Target only**: a decision we made on paper, not built yet.

## I. Domain Model

### ADR-01: A requirement is the unit of work, not the whole document

- **Status:** PoC confirmed
- **Decision:** We treat each regulatory requirement as its own unit of analysis, not the document it came from.
- **Why:** One article can contain several different obligations at once (governance, data, controls, monitoring), and each one can have a different owner and affect different systems. Treating the whole document as one blob would lose that detail.
- **Trade-off:** More objects to track. One document turns into many requirement records instead of one summary. In exchange, we get real traceability: you can follow a line from the regulation all the way down to who owns the fix.

## II. Workflow and Autonomy

### ADR-02: A deterministic workflow, not an autonomous agent

- **Status:** PoC confirmed
- **Decision:** The platform runs as a fixed, known workflow. An AI agent is never in charge of the whole process.
- **Why:** An agent that freely decides what to check next sounds powerful, but it is hard to predict, hard to audit, and hard to explain to a regulator. A fixed workflow means every step is known in advance and can be reviewed on its own.
- **Trade-off:** Less flexibility. The system cannot go explore on its own when something unusual comes up.

### ADR-03: An agent only for ambiguous cases, with hard limits

- **Status:** Target only
- **Decision:** When an agent is used, only for cases the deterministic path cannot resolve, it gets a fixed list of allowed tools and a hard limit on steps and tokens.
- **Why:** An unbounded agent could spend unlimited time and money chasing one hard case, or reach into systems it should never touch.
- **Trade-off:** The agent might give up and hand the case to a human instead of fully resolving it. That is the safe outcome, not a failure.

### ADR-04: New autonomy has to be earned, not assumed

- **Status:** Target only
- **Decision:** If the agent is ever allowed to do more on its own, that expansion has to be justified by real evidence from cases humans already confirmed. It does not grow automatically over time.
- **Why:** Otherwise the system quietly drifts away from "deterministic by default" without anyone deciding that on purpose.
- **Trade-off:** Slower to expand what the system is allowed to do. That is the point.

## III. AI Reasoning and Grounding

### ADR-05: Retrieval and reasoning are two separate steps

- **Status:** PoC confirmed
- **Decision:** Finding the evidence (search) and making sense of it (the LLM) are two different steps, not one combined call.
- **Why:** If a result turns out wrong, we want to know which part failed: a bad search, or a bad reading of good evidence. Keeping them separate means we can fix one without touching the other.
- **Trade-off:** More moving parts (an index, embeddings, a retrieval step) instead of one call that does everything.

### ADR-06: Every hypothesis needs two citations, checked in code

- **Status:** PoC confirmed, and this check has already caught real cases
- **Decision:** Every AI hypothesis must point to both the regulation it comes from and the internal policy it is compared against. If the model claims a match but cannot name a specific policy section, the code downgrades that answer instead of trusting it.
- **Why:** Telling a model "always cite your source" in a prompt is not a guarantee. Models do not always follow instructions perfectly. A check in code is a real safety net, not a polite request.
- **Trade-off:** Sometimes the honest answer is "not enough evidence" instead of a confident guess. That is a good trade.

### ADR-07: A cheap model for extraction, a stronger model for judgment

- **Status:** Target only (the PoC currently uses one model for both steps)
- **Decision:** Use a fast, cheap model to pull requirements out of a document. Save the stronger, more expensive model for the step that actually judges whether something is a real match.
- **Why:** Not every step needs the same amount of thinking power, and cost adds up quickly if every call uses the expensive model.
- **Trade-off:** Two models to manage instead of one, and ongoing work to confirm the cheap one is still good enough for its job.

### ADR-08: Confidence is a hint, not a probability

- **Status:** PoC confirmed, and stated plainly in the compliance report
- **Decision:** When the model reports a confidence number, we treat it as "how sure the model sounds," not as a real statistical probability of being correct.
- **Why:** These numbers are not calibrated. A model saying 0.9 does not mean it is right 90% of the time.
- **Trade-off:** You cannot just set a threshold and auto-approve everything above it. Someone still has to look.

## IV. Human and AI Decision Boundary

### ADR-09: The AI proposes, humans and GRC decide

- **Status:** PoC confirmed, enforced in code so it cannot be turned off by accident
- **Decision:** The AI never outputs a final compliance decision. It only outputs a hypothesis: potential impact, no impact proposed, or not enough evidence. A human, backed by the GRC system, makes the actual call.
- **Why:** The AI cannot see everything that might matter, like a legal exception, a compensating control, or something the bank already agreed with the regulator. Only a human has that full picture.
- **Trade-off:** Slower than letting the AI decide on its own. Worth it given what is at stake.

### ADR-10: "No impact" still needs a human to confirm it

- **Status:** PoC confirmed and tested live
- **Decision:** Even when the AI proposes "no impact," a human still has to confirm that before it is closed.
- **Why:** The two kinds of mistakes are not equally costly. If the AI wrongly flags something as a potential impact, an analyst loses a bit of time checking it. If the AI wrongly says "no impact" and that is missed, that is a real regulatory problem. We protect harder against the worse mistake.
- **Trade-off:** More things for humans to review, even the ones the AI already thinks are fine.

## V. System of Record and Data

### ADR-11: GRC owns the truth, the Knowledge Graph does not

- **Status:** Target only, not built in this PoC
- **Decision:** GRC is the only system allowed to hold the official, confirmed record of impacts and remediation. The Knowledge Graph only stores relationships between things, like which policy connects to which control connects to which system. It is never treated as a second source of truth.
- **Why:** A bank already has a real GRC system with a real audit history. Building a second "truth" somewhere else creates confusion about which one to trust, and that gets expensive to untangle later.
- **Trade-off:** We have to integrate with the existing GRC system instead of building something simpler on our own. Slower, but it avoids a much worse problem down the line.

### ADR-12: Keep the full history, not just the final answer

- **Status:** Partial (the PoC records model and prompt version on extracted requirements, but not yet on every analysis step)
- **Decision:** Store the full trail behind every decision: which version of the source text, which evidence was used, which model and prompt made the call, and what the human eventually decided.
- **Why:** Policies change over time. Months later, someone may ask why a certain call was made back then. Without the full trail, that question cannot be answered.
- **Trade-off:** More to design and store. Worth it for something a regulator might ask about years later.

### ADR-13: A new embedding model means a new index, never an overwrite

- **Status:** Target only (the PoC only ever had one index version)
- **Decision:** When switching to a new embedding model, build a brand new search index rather than updating the old one in place.
- **Why:** A destructive update could quietly break search results with no way back. A new version can be tested and rolled back safely.
- **Trade-off:** Running two indexes for a while costs more. Much cheaper than an outage with no way to undo it.

## VI. Security and Identity

### ADR-14: Filter by permission before the model ever sees the content

- **Status:** Target only (this PoC has a single user, so there is no real permission boundary to test yet)
- **Decision:** Access control is applied at the search step, before anything reaches the model. We do not rely on telling the model to simply ignore restricted content.
- **Why:** An instruction inside a prompt is not a real security boundary. A model can be tricked, or can just make a mistake. Filtering at the data layer means restricted content is never even in the room.
- **Trade-off:** More complexity in how search is set up, since it needs to understand permissions, not just meaning.

### ADR-15: No secrets, only identities, and each one gets only what it needs

- **Status:** PoC confirmed and actually built
- **Decision:** Every service talks to every other service using Managed Identity, never a stored password or key. The identity running the pipeline day to day is not the same identity allowed to update the search index or deploy new code.
- **Why:** If there is no secret to steal, that whole category of risk disappears. And if the identity reading documents is ever compromised, it still cannot rewrite what the search index knows.
- **Trade-off:** More identities and roles to design and keep track of.

### ADR-16: Know what data is allowed in before it goes near the model

- **Status:** Target only (not tested here, since the PoC only uses synthetic and public data)
- **Decision:** Before any new kind of document enters the pipeline, it should pass a data classification and approval step. AI services live inside an approved part of the cloud, not bolted on wherever convenient.
- **Why:** A bank cannot let sensitive or regulated data reach an AI model just because someone found it convenient to upload. That decision needs to be made on purpose, in advance.
- **Trade-off:** Slower to add a new regulatory source. That is the right kind of slow.

## VII. Reliability and Operations

### ADR-17: React to events, but plan for the same event twice

- **Status:** Partial (the trigger itself works well, the safety net for duplicates is not built yet)
- **Decision:** The pipeline reacts as soon as a new file lands in storage, instead of checking on a schedule. At the same time, we treat it as normal that the same event might fire more than once.
- **Why:** Reacting immediately is faster and cheaper than constantly polling for something new. But event systems are honest about their own limits: they promise "at least once," not "exactly once."
- **Trade-off:** More to think through, like retries and making sure processing the same document twice does not create duplicate or conflicting results.

### ADR-18: Simple now, built to scale later

- **Status:** PoC confirmed as is, production version is a known next step
- **Decision:** Right now, one function processes a document's requirements in a simple loop, one after another. In production, with far more documents, this should become a real workflow that can fan out and handle many requirements at once.
- **Why:** Building the more complex version now, before we even know if the simple one has problems, means solving a problem we do not have yet.
- **Trade-off:** The current version will not scale to hundreds of requirements. It was never meant to yet.

### ADR-19: Watch each part on its own, not just "is the app up"

- **Status:** Target only (the PoC has logging, but no formal per-part health checks yet)
- **Decision:** Each component (search, the model call, storage) should have its own health signal, instead of one single check for the whole platform.
- **Why:** If something breaks, you want to know exactly what broke, not just that something did.
- **Trade-off:** More dashboards and alerts to set up and maintain.

### ADR-20: If GRC is down, wait and retry, never guess

- **Status:** Target only (there is no real GRC to test this against yet)
- **Decision:** If GRC cannot be reached, the platform holds the update in a clearly marked pending state and keeps retrying. It never pretends the write happened, and never drops it silently.
- **Why:** Losing a confirmed compliance record because a system happened to be down for five minutes is not acceptable.
- **Trade-off:** Some things sit visibly unfinished during an outage. Much better than losing them quietly.
