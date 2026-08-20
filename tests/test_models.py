from pipeline.models import Citation, ImpactClassification, ImpactHypothesis, PolicyFragment


def test_requires_human_confirmation_cannot_be_set_false():
    """This is the one invariant this whole PoC exists to prove: no code path,
    not even a caller explicitly trying to, can produce a hypothesis that
    claims it doesn't need human confirmation."""
    hypothesis = ImpactHypothesis(
        requirement_id="DOC-R1",
        classification=ImpactClassification.POTENTIAL_IMPACT,
        reasoning="test",
        citations=Citation(external="Article 9(2)(a)", internal="Policy X, Section 4"),
        retrieved_fragments=[],
        confidence=0.9,
        model_version="gpt-4o",
        requires_human_confirmation=False,  # attempt to override
    )
    assert hypothesis.requires_human_confirmation is True


def test_no_impact_hypothesis_has_no_internal_citation():
    hypothesis = ImpactHypothesis(
        requirement_id="DOC-R2",
        classification=ImpactClassification.NO_IMPACT_PROPOSED,
        reasoning="No fragment addresses this requirement.",
        citations=Citation(external="Article 13(3)(a)", internal=None),
        retrieved_fragments=[],
        confidence=0.7,
        model_version="gpt-4o",
    )
    assert hypothesis.citations.internal is None
    assert hypothesis.requires_human_confirmation is True


def test_policy_fragment_roundtrip():
    fragment = PolicyFragment(
        policy_document_id="ACME-POL-MRM-003",
        policy_title="Acme Bank Model Risk Management Standard",
        section="Section 5",
        excerpt="All Tier 1 and Tier 2 models are subject to a formal revalidation exercise on an annual basis...",
        relevance_score=0.83,
    )
    assert fragment.model_dump()["relevance_score"] == 0.83
