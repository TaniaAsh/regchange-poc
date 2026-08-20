"""
Thin adapter around the real azure-search-documents SDK, satisfying the
SearchClient protocol used by retrieve.py. Managed Identity auth, no admin
key stored anywhere.
"""
from __future__ import annotations

from typing import Any, Optional

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient as AzureSearchClient
from azure.search.documents.models import VectorizedQuery


def build_search_client(endpoint: str, index_name: str) -> AzureSearchClient:
    return AzureSearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=DefaultAzureCredential(),
    )


class AISearchClient:
    """Satisfies the SearchClient protocol expected by retrieve.py."""

    def __init__(self, client: AzureSearchClient) -> None:
        self._client = client

    def search(
        self,
        *,
        query_text: str,
        query_vector: Optional[list[float]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        vector_queries = None
        if query_vector is not None:
            vector_queries = [
                VectorizedQuery(vector=query_vector, k_nearest_neighbors=top_k, fields="content_vector")
            ]

        results = self._client.search(
            search_text=query_text,
            vector_queries=vector_queries,
            query_type="semantic" if vector_queries is None else "simple",
            top=top_k,
        )

        hits: list[dict[str, Any]] = []
        for r in results:
            hits.append(
                {
                    "policy_document_id": r["policy_document_id"],
                    "policy_title": r["policy_title"],
                    "section": r["section"],
                    "excerpt": r["content"],
                    "relevance_score": r.get("@search.score", 0.0),
                }
            )
        return hits
