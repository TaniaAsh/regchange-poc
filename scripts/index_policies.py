"""
scripts/index_policies.py

Builds (or updates) the `policy-fragments-v1` Azure AI Search index and
populates it from the synthetic ACME Bank policy documents in
data/policies/.

Chunking is deliberately simple: one fragment per markdown `## ` heading.
No token-based splitting, no overlap windows. The policy documents were
written with clean section structure specifically so this works well, and
it gives natural, citable section names for free (ADR-6: every retrieved
fragment needs to be citable back to a specific policy section).

Reuses the same frontmatter parser and Foundry client adapter the runtime
pipeline uses (src/function_app/pipeline/), rather than duplicating that
logic here — one implementation of "how we talk to Foundry", not two.

Auth: Managed Identity / az login via DefaultAzureCredential, same as the
runtime pipeline. No API keys anywhere. Locally this picks up your `az
login` session; in GitHub Actions it picks up the OIDC-federated
regchange-poc-github-deploy identity (see .github/workflows/
index-policies.yml).

Usage:
    python scripts/index_policies.py
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Reuse the pipeline package's frontmatter parser and Foundry client adapter
# instead of duplicating them here.
REPO_ROOT = Path(__file__).resolve().parent.parent
FUNCTION_APP_ROOT = REPO_ROOT / "src" / "function_app"
sys.path.insert(0, str(FUNCTION_APP_ROOT))

from pipeline.foundry_client import FoundryEmbeddingClient, build_foundry_client  # noqa: E402
from pipeline.frontmatter import parse_frontmatter  # noqa: E402

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

POLICIES_DIR = REPO_ROOT / "data" / "policies"

SEARCH_ENDPOINT = os.environ["SEARCH_ENDPOINT"]
INDEX_NAME = os.environ.get("SEARCH_INDEX_NAME", "policy-fragments-v1")
FOUNDRY_ENDPOINT = os.environ["FOUNDRY_ENDPOINT"]
FOUNDRY_API_VERSION = os.environ.get("FOUNDRY_API_VERSION", "2024-10-21")
EMBEDDING_MODEL = os.environ.get("FOUNDRY_MODEL_EMBEDDING", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = 1536  # must match the embedding model above

_SECTION_HEADING_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)


@dataclass
class PolicyFragment:
    fragment_id: str
    policy_document_id: str
    policy_title: str
    section: str
    content: str


def _extract_title(body: str) -> str:
    """Falls back to the document's first '# ' heading if frontmatter has
    no explicit title."""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return "Untitled Policy"


def chunk_policy(document_id: str, title: str, body: str) -> list[PolicyFragment]:
    """One fragment per '## ' heading. Content before the first heading
    (just the '# Title' line and any short intro) is intentionally not
    indexed — every fragment needs a real section name to be citable."""
    matches = list(_SECTION_HEADING_RE.finditer(body))
    fragments: list[PolicyFragment] = []

    for i, match in enumerate(matches):
        section_name = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[start:end].strip()

        if not content:
            continue

        fragment_id = hashlib.sha1(f"{document_id}:{section_name}".encode("utf-8")).hexdigest()
        fragments.append(
            PolicyFragment(
                fragment_id=fragment_id,
                policy_document_id=document_id,
                policy_title=title,
                section=section_name,
                content=content,
            )
        )

    logger.info("Chunked %s into %d section(s)", document_id, len(fragments))
    return fragments


def load_all_fragments() -> list[PolicyFragment]:
    all_fragments: list[PolicyFragment] = []
    policy_files = sorted(POLICIES_DIR.glob("*.md"))

    if not policy_files:
        raise RuntimeError(f"No policy documents found in {POLICIES_DIR}")

    for path in policy_files:
        raw_text = path.read_text(encoding="utf-8")
        metadata, body = parse_frontmatter(raw_text)
        document_id = metadata.get("document_id", path.stem)
        title = metadata.get("title") or _extract_title(body)
        all_fragments.extend(chunk_policy(document_id, title, body))

    return all_fragments


def ensure_index(index_client: SearchIndexClient) -> None:
    """Creates the index if it doesn't exist, or updates it in place if the
    schema changed. Idempotent — safe to run repeatedly."""
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="policy_document_id", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="policy_title", type=SearchFieldDataType.String),
        SearchableField(name="section", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="default-vector-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="default-hnsw",
                parameters=HnswParameters(metric="cosine"),
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="default-vector-profile",
                algorithm_configuration_name="default-hnsw",
            )
        ],
    )

    index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search)
    index_client.create_or_update_index(index)
    logger.info("Index '%s' created/updated", INDEX_NAME)


def index_fragments(
    search_client: SearchClient,
    embedding_client: FoundryEmbeddingClient,
    fragments: list[PolicyFragment],
) -> None:
    documents = []
    for fragment in fragments:
        vector = embedding_client.embed(fragment.content, model=EMBEDDING_MODEL)
        documents.append(
            {
                "id": fragment.fragment_id,
                "policy_document_id": fragment.policy_document_id,
                "policy_title": fragment.policy_title,
                "section": fragment.section,
                "content": fragment.content,
                "content_vector": vector,
            }
        )
        logger.info("Embedded: %s / %s", fragment.policy_document_id, fragment.section)

    results = search_client.merge_or_upload_documents(documents=documents)
    failed = [r for r in results if not r.succeeded]
    if failed:
        raise RuntimeError(f"{len(failed)} document(s) failed to index: {failed}")

    logger.info("Indexed %d fragment(s) into '%s'", len(documents), INDEX_NAME)


def main() -> None:
    credential = DefaultAzureCredential()

    index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential)
    ensure_index(index_client)

    search_client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)
    foundry = build_foundry_client(FOUNDRY_ENDPOINT, FOUNDRY_API_VERSION)
    embedding_client = FoundryEmbeddingClient(foundry)

    fragments = load_all_fragments()
    index_fragments(search_client, embedding_client, fragments)


if __name__ == "__main__":
    main()
