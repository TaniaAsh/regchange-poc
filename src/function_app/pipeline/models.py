"""
Pydantic schemas for the regulatory change impact analysis pipeline.

These mirror the entity fields described in the platform's architecture
documents (Regulatory Requirement, Internal Policy, Impact Assessment) but are
scoped down to exactly what this PoC needs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RegulatoryRequirement(BaseModel):
    """One atomic, independently actionable obligation extracted from a
    regulatory document. Never merges multiple obligations into one record —
    that's the whole point of extracting at this granularity instead of
    treating the source document as a single unit."""

    id: str = Field(..., description="e.g. 'R1', unique within the source document")
    source_document_id: str
    source_article: str = Field(..., description="e.g. 'Article 9(2)(a)'")
    requirement_text: str
    jurisdiction: str
    effective_date: Optional[str] = None
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)
    model_version: str
    prompt_version: str = "v1"
    timestamp: str = Field(default_factory=_utcnow_iso)


class PolicyFragment(BaseModel):
    """A retrieved chunk of an internal policy document, with enough
    provenance to cite it precisely."""

    policy_document_id: str
    policy_title: str
    section: str
    excerpt: str
    relevance_score: float


class ImpactClassification(str, Enum):
    POTENTIAL_IMPACT = "potential_impact"
    NO_IMPACT_PROPOSED = "no_impact_proposed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class Citation(BaseModel):
    """Two-sided citation, per ADR-6. Both sides are required — a hypothesis
    with only one side populated is not considered valid output by this
    pipeline (see analyze.py)."""

    external: str = Field(..., description="Regulatory citation, e.g. 'EU AI Act, Article 9(2)(a)'")
    internal: Optional[str] = Field(
        None,
        description="Internal policy citation, e.g. 'Acme Model Risk Standard v3, Section 5'. "
        "None only when classification is NO_IMPACT_PROPOSED or INSUFFICIENT_EVIDENCE.",
    )


class ImpactHypothesis(BaseModel):
    """The pipeline's output for a single requirement. This is explicitly a
    HYPOTHESIS, never a confirmed business decision — requires_human_confirmation
    is always True, regardless of classification or confidence (ADR-7)."""

    requirement_id: str
    classification: ImpactClassification
    reasoning: str = Field(..., description="Human-readable explanation grounded in the retrieved fragments only")
    citations: Citation
    retrieved_fragments: list[PolicyFragment]
    confidence: float = Field(..., ge=0.0, le=1.0)
    model_version: str
    requires_human_confirmation: bool = True
    timestamp: str = Field(default_factory=_utcnow_iso)

    def model_post_init(self, __context) -> None:
        # Belt-and-braces: this must never be False, no matter what a caller
        # tries to construct. This is the one field this whole PoC exists to
        # prove is non-negotiable.
        object.__setattr__(self, "requires_human_confirmation", True)
