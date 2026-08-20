"""
RAG Retrieval against Azure AI Search.

Hybrid search (keyword + vector) when an embedding client is supplied, keyword
-only otherwise — the pipeline degrades gracefully rather than failing if
vector search isn't configured yet. Security trimming (filtering by the
caller's access groups) is intentionally NOT implemented here: in the full
architecture it happens via Azure AI Search's native security-trimming
filters (ADR-5), applied before results ever reach this function. For this
single-user PoC there's no multi-tenant permission boundary to trim against.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Protocol

from .models import PolicyFragment

logger = logging.getLogger(__name__)


class SearchClient(Protocol):
    def search(
        self,
        *,
        query_text: str,
        query_vector: Optional[list[float]],
        top_k: int,
    ) -> list[dict[str, Any]]: ...


class EmbeddingClient(Protocol):
    def embed(self, text: str, model: str) -> list[float]: ...


def retrieve_policy_fragments(
    requirement_text: str,
    search_client: SearchClient,
    top_k: int = 3,
    embedding_client: Optional[EmbeddingClient] = None,
    embedding_model: str = "text-embedding-3-small",
) -> list[PolicyFragment]:
    """Retrieve the top_k most relevant internal policy fragments for a
    single requirement's text."""

    query_vector: Optional[list[float]] = None
    if embedding_client is not None:
        try:
            query_vector = embedding_client.embed(requirement_text, model=embedding_model)
        except Exception:
            logger.warning("Embedding call failed; falling back to keyword-only search", exc_info=True)
            query_vector = None

    hits = search_client.search(
        query_text=requirement_text,
        query_vector=query_vector,
        top_k=top_k,
    )

    fragments = [
        PolicyFragment(
            policy_document_id=hit["policy_document_id"],
            policy_title=hit["policy_title"],
            section=hit["section"],
            excerpt=hit["excerpt"],
            relevance_score=float(hit.get("relevance_score", 0.0)),
        )
        for hit in hits
    ]

    logger.info("Retrieved %d policy fragment(s) for requirement", len(fragments))
    return fragments
