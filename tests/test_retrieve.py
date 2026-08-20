from pipeline.retrieve import retrieve_policy_fragments


class StubSearchClient:
    def __init__(self, hits: list[dict]):
        self._hits = hits
        self.last_call: dict | None = None

    def search(self, *, query_text: str, query_vector, top_k: int) -> list[dict]:
        self.last_call = {"query_text": query_text, "query_vector": query_vector, "top_k": top_k}
        return self._hits[:top_k]


class StubEmbeddingClient:
    def __init__(self, vector: list[float]):
        self._vector = vector
        self.calls = 0

    def embed(self, text: str, model: str) -> list[float]:
        self.calls += 1
        return self._vector


_SAMPLE_HITS = [
    {
        "policy_document_id": "ACME-POL-MRM-003",
        "policy_title": "Acme Bank Model Risk Management Standard",
        "section": "Section 5",
        "excerpt": "All Tier 1 and Tier 2 models are subject to annual revalidation...",
        "relevance_score": 0.91,
    },
    {
        "policy_document_id": "ACME-POL-AIGOV-002",
        "policy_title": "Acme Bank AI Governance Policy",
        "section": "Section 5",
        "excerpt": "Pre-Deployment Risk Assessment covering intended purpose and known limitations...",
        "relevance_score": 0.77,
    },
]


def test_retrieve_keyword_only_when_no_embedding_client():
    search_client = StubSearchClient(_SAMPLE_HITS)

    fragments = retrieve_policy_fragments(
        requirement_text="Providers must identify and analyze known risks.",
        search_client=search_client,
        top_k=2,
    )

    assert len(fragments) == 2
    assert fragments[0].policy_document_id == "ACME-POL-MRM-003"
    assert search_client.last_call["query_vector"] is None


def test_retrieve_hybrid_when_embedding_client_provided():
    search_client = StubSearchClient(_SAMPLE_HITS)
    embedding_client = StubEmbeddingClient(vector=[0.1, 0.2, 0.3])

    fragments = retrieve_policy_fragments(
        requirement_text="Providers must identify and analyze known risks.",
        search_client=search_client,
        embedding_client=embedding_client,
        top_k=1,
    )

    assert len(fragments) == 1
    assert embedding_client.calls == 1
    assert search_client.last_call["query_vector"] == [0.1, 0.2, 0.3]


def test_retrieve_falls_back_gracefully_on_embedding_failure():
    class FailingEmbeddingClient:
        def embed(self, text: str, model: str) -> list[float]:
            raise RuntimeError("embedding deployment unavailable")

    search_client = StubSearchClient(_SAMPLE_HITS)

    fragments = retrieve_policy_fragments(
        requirement_text="Providers must identify and analyze known risks.",
        search_client=search_client,
        embedding_client=FailingEmbeddingClient(),
        top_k=2,
    )

    # Should not raise — degrades to keyword-only search instead
    assert len(fragments) == 2
    assert search_client.last_call["query_vector"] is None
