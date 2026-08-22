---
document_id: EU-AI-ACT-2024-1689-ART15
source: Regulation (EU) 2024/1689 (Artificial Intelligence Act)
article: 15
title: Accuracy, robustness and cybersecurity
official_source: https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-15
publication_date: 2024-07-12
jurisdiction: EU
effective_date: 2026-08-02
ingestion_timestamp: 2026-08-22T09:00:00Z
---

# Article 15: Accuracy, robustness and cybersecurity

1. High-risk AI systems shall be designed and developed in such a way that they
achieve an appropriate level of accuracy, robustness, and cybersecurity, and
that they perform consistently in those respects throughout their lifecycle.

2. To address the technical aspects of how to measure the appropriate levels
of accuracy and robustness set out in paragraph 1 and any other relevant
performance metrics, the Commission shall, in cooperation with relevant
stakeholders and organisations such as metrology and benchmarking
authorities, encourage, as appropriate, the development of benchmarks and
measurement methodologies.

3. The levels of accuracy and the relevant accuracy metrics of high-risk AI
systems shall be declared in the accompanying instructions of use.

4. High-risk AI systems shall be as resilient as possible regarding errors,
faults or inconsistencies that may occur within the system or the
environment in which the system operates, in particular due to their
interaction with natural persons or other systems. Technical and
organisational measures shall be taken in this regard.

The robustness of high-risk AI systems may be achieved through technical
redundancy solutions, which may include backup or fail-safe plans. High-risk
AI systems that continue to learn after being placed on the market or put
into service shall be developed in such a way as to eliminate or reduce as
far as possible the risk of possibly biased outputs influencing input for
future operations (feedback loops), and as to ensure that any such feedback
loops are duly addressed with appropriate mitigation measures.

5. High-risk AI systems shall be resilient against attempts by unauthorised
third parties to alter their use, outputs or performance by exploiting
system vulnerabilities. The technical solutions aiming to ensure the
cybersecurity of high-risk AI systems shall be appropriate to the relevant
circumstances and the risks, and shall include, where appropriate, measures
to prevent, detect, respond to, resolve and control for attacks trying to
manipulate the training data set (data poisoning), inputs designed to cause
the model to make a mistake (adversarial examples), or model flaws.

---
*Excerpt for PoC purposes, official source above. Not legal advice.
Included specifically because it addresses technical accuracy/robustness/
cybersecurity controls — a domain none of the three ACME policies in
data/policies/ cover (they address governance process, model risk
validation cadence, and customer communications, not technical security
controls), unlike Articles 9 and 13 which overlap more with what those
policies already say. This is a deliberate test for whether the pipeline
can also produce no_impact_proposed / insufficient_evidence, not just
potential_impact.*
