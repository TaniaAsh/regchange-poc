import json

import pytest

from pipeline.extract import extract_requirements


class StubChatClient:
    """Satisfies extract.py's ChatClient protocol without touching any real
    Azure SDK or network."""

    def __init__(self, response_json: str):
        self._response_json = response_json
        self.last_call: dict | None = None

    def chat_completion_json(self, *, system: str, user: str, model: str) -> str:
        self.last_call = {"system": system, "user": user, "model": model}
        return self._response_json


def test_extract_requirements_parses_multiple_atomic_requirements():
    canned_response = json.dumps(
        {
            "requirements": [
                {
                    "source_article": "Article 9(2)(a)",
                    "requirement_text": "Identify and analyze known and reasonably foreseeable risks.",
                    "confidence": 0.95,
                },
                {
                    "source_article": "Article 9(2)(d)",
                    "requirement_text": "Adopt appropriate and targeted risk management measures.",
                    "confidence": 0.88,
                },
            ]
        }
    )
    client = StubChatClient(canned_response)

    requirements = extract_requirements(
        document_text="Article 9 full text...",
        document_id="EU-AI-ACT-2024-1689-ART9",
        jurisdiction="EU",
        client=client,
        model_deployment="gpt-4o-mini",
    )

    assert len(requirements) == 2
    assert requirements[0].id == "EU-AI-ACT-2024-1689-ART9-R1"
    assert requirements[1].id == "EU-AI-ACT-2024-1689-ART9-R2"
    assert requirements[0].source_article == "Article 9(2)(a)"
    assert requirements[0].extraction_confidence == 0.95
    assert requirements[0].jurisdiction == "EU"
    assert requirements[0].model_version == "gpt-4o-mini"
    # Confirms the document text actually reached the model
    assert client.last_call is not None
    assert "Article 9 full text" in client.last_call["user"]


def test_extract_requirements_raises_on_malformed_json():
    client = StubChatClient("this is not json")

    with pytest.raises(ValueError, match="did not return valid JSON"):
        extract_requirements(
            document_text="...",
            document_id="DOC-1",
            jurisdiction="EU",
            client=client,
            model_deployment="gpt-4o-mini",
        )


def test_extract_requirements_empty_document_returns_empty_list():
    client = StubChatClient(json.dumps({"requirements": []}))

    requirements = extract_requirements(
        document_text="No obligations here.",
        document_id="DOC-2",
        jurisdiction="EU",
        client=client,
        model_deployment="gpt-4o-mini",
    )

    assert requirements == []
