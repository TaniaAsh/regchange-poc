"""
Requirement Extraction — single bounded LLM call, not an agent.

Given the full text of a regulatory document, extracts every atomic,
independently actionable obligation as a separate RegulatoryRequirement.
Deliberately does NOT summarize or merge obligations — a document with 14
distinct requirements should produce 14 records, not one.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from .models import RegulatoryRequirement

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a regulatory analysis assistant. Your only job is \
to extract atomic, independently actionable requirements from a regulatory \
document. You do not interpret, summarize, or judge compliance — that happens \
in a later, separate step.

Rules:
- Each requirement must be a single, independently actionable obligation. If a \
paragraph contains multiple distinct obligations (e.g. points (a), (b), (c)), \
extract each as its own requirement.
- Preserve the precise source reference for each requirement (e.g. \
"Article 9(2)(a)"), not just the article number.
- Do not invent requirements that are not explicitly stated in the text.
- Do not add commentary, opinions, or compliance judgments.

Respond with a JSON object of the form:
{"requirements": [
  {"source_article": "Article 9(2)(a)", "requirement_text": "...", "confidence": 0.0-1.0}
]}
confidence reflects how unambiguous the extraction was, not how important the \
requirement is."""


class ChatClient(Protocol):
    """Structural type for whatever client extract() is given — the real
    AzureOpenAI client satisfies this, and so does a bare mock in tests. No
    import of the openai package is required just to type-check this module."""

    def chat_completion_json(self, *, system: str, user: str, model: str) -> str: ...


def extract_requirements(
    document_text: str,
    document_id: str,
    jurisdiction: str,
    client: ChatClient,
    model_deployment: str,
    prompt_version: str = "v1",
) -> list[RegulatoryRequirement]:
    """Extract requirements from a single regulatory document.

    `client` only needs a `chat_completion_json` method — see
    `foundry_client.py` for the thin adapter used against the real Azure
    OpenAI SDK. Tests pass a stub with the same method instead.
    """
    raw = client.chat_completion_json(
        system=_SYSTEM_PROMPT,
        user=document_text,
        model=model_deployment,
    )

    try:
        parsed: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Extraction model returned non-JSON output: %s", raw[:500])
        raise ValueError("Requirement extraction failed: model did not return valid JSON") from exc

    items = parsed.get("requirements", [])
    requirements: list[RegulatoryRequirement] = []
    for idx, item in enumerate(items, start=1):
        requirements.append(
            RegulatoryRequirement(
                id=f"{document_id}-R{idx}",
                source_document_id=document_id,
                source_article=item["source_article"],
                requirement_text=item["requirement_text"],
                jurisdiction=jurisdiction,
                extraction_confidence=float(item.get("confidence", 0.5)),
                model_version=model_deployment,
                prompt_version=prompt_version,
            )
        )

    logger.info("Extracted %d requirement(s) from %s", len(requirements), document_id)
    return requirements
