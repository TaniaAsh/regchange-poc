"""
Function entry point. Triggered by an Event Grid BlobCreated event when a new
document lands in the `regulatory-documents` container (see infra/modules/
event-grid.bicep for the subscription that wires this up — not the legacy
polling blob trigger, see the architecture discussion in docs/ for why).

Wires the pipeline steps together end to end:
  blob -> extract_requirements -> [retrieve_policy_fragments -> analyze_impact]* -> output blob(s)

Every step's dependencies (Foundry client, Search client) are injected via the
adapters in foundry_client.py / search_client.py, which are the only files
here that touch real Azure SDKs — this file and the pipeline/*.py modules it
calls stay unit-testable without any live Azure call.
"""
from __future__ import annotations

import json
import logging
import os

import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

from pipeline.analyze import analyze_impact
from pipeline.extract import extract_requirements
from pipeline.foundry_client import FoundryChatClient, FoundryEmbeddingClient, build_foundry_client
from pipeline.frontmatter import parse_frontmatter
from pipeline.retrieve import retrieve_policy_fragments
from pipeline.search_client import AISearchClient, build_search_client

logger = logging.getLogger(__name__)

app = func.FunctionApp()

STORAGE_ACCOUNT_NAME = os.environ.get("STORAGE_ACCOUNT_NAME", "")
OUTPUT_CONTAINER = os.environ.get("STORAGE_CONTAINER_OUTPUT", "impact-hypotheses")
FOUNDRY_ENDPOINT = os.environ.get("FOUNDRY_ENDPOINT", "")
FOUNDRY_API_VERSION = os.environ.get("FOUNDRY_API_VERSION", "2024-10-21")
MODEL_EXTRACTION = os.environ.get("FOUNDRY_MODEL_EXTRACTION", "gpt-4o-mini")
MODEL_ANALYSIS = os.environ.get("FOUNDRY_MODEL_ANALYSIS", "gpt-4o")
SEARCH_ENDPOINT = os.environ.get("SEARCH_ENDPOINT", "")
SEARCH_INDEX_NAME = os.environ.get("SEARCH_INDEX_NAME", "policy-fragments-v1")


@app.event_grid_trigger(arg_name="event")
def process_new_document(event: func.EventGridEvent) -> None:
    event_data = event.get_json()
    blob_url: str = event_data.get("url", "")

    if "/regulatory-documents/" not in blob_url:
        logger.info("Ignoring blob event outside regulatory-documents container: %s", blob_url)
        return

    logger.info("New regulatory document detected: %s", blob_url)

    blob_service = BlobServiceClient(
        account_url=f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
        credential=DefaultAzureCredential(),
    )

    # blob_url looks like https://<account>.blob.core.windows.net/regulatory-documents/<blob_name>
    blob_name = blob_url.split("/regulatory-documents/", 1)[1]
    source_blob = blob_service.get_blob_client(container="regulatory-documents", blob=blob_name)
    raw_text = source_blob.download_blob().readall().decode("utf-8")

    metadata, body = parse_frontmatter(raw_text)
    document_id = metadata.get("document_id", blob_name)
    jurisdiction = metadata.get("jurisdiction", "unknown")

    foundry = build_foundry_client(FOUNDRY_ENDPOINT, FOUNDRY_API_VERSION)
    chat_client = FoundryChatClient(foundry)
    embedding_client = FoundryEmbeddingClient(foundry)
    search_client = AISearchClient(build_search_client(SEARCH_ENDPOINT, SEARCH_INDEX_NAME))

    requirements = extract_requirements(
        document_text=body,
        document_id=document_id,
        jurisdiction=jurisdiction,
        client=chat_client,
        model_deployment=MODEL_EXTRACTION,
    )

    output_container_client = blob_service.get_container_client(OUTPUT_CONTAINER)

    for requirement in requirements:
        fragments = retrieve_policy_fragments(
            requirement_text=requirement.requirement_text,
            search_client=search_client,
            embedding_client=embedding_client,
        )
        hypothesis = analyze_impact(
            requirement=requirement,
            fragments=fragments,
            client=chat_client,
            model_deployment=MODEL_ANALYSIS,
        )

        output_blob_name = f"{requirement.id}.json"
        output_container_client.upload_blob(
            name=output_blob_name,
            data=hypothesis.model_dump_json(indent=2),
            overwrite=True,
        )
        logger.info("Wrote hypothesis for %s -> %s", requirement.id, output_blob_name)

    logger.info("Finished processing %s: %d requirement(s)", document_id, len(requirements))
