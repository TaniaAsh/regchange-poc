"""
Thin adapter around the real Azure OpenAI (Foundry) SDK, satisfying the
ChatClient / EmbeddingClient protocols used by extract.py / retrieve.py /
analyze.py. This is the only file in the pipeline package that imports the
`openai` or `azure-identity` packages — everything else stays testable
without them.

Auth: Managed Identity via DefaultAzureCredential, no API keys anywhere.
Locally, DefaultAzureCredential falls back to your `az login` session.
"""
from __future__ import annotations

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def build_foundry_client(endpoint: str, api_version: str) -> AzureOpenAI:
    """Construct an AzureOpenAI client authenticated via Managed Identity /
    az login — never via an API key."""
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    return AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version=api_version,
    )


class FoundryChatClient:
    """Satisfies the ChatClient protocol expected by extract.py / analyze.py."""

    def __init__(self, client: AzureOpenAI) -> None:
        self._client = client

    def chat_completion_json(self, *, system: str, user: str, model: str) -> str:
        response = self._client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Foundry returned an empty response")
        return content


class FoundryEmbeddingClient:
    """Satisfies the EmbeddingClient protocol expected by retrieve.py."""

    def __init__(self, client: AzureOpenAI) -> None:
        self._client = client

    def embed(self, text: str, model: str) -> list[float]:
        response = self._client.embeddings.create(model=model, input=text)
        return response.data[0].embedding
