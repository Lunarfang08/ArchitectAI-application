import json

import httpx

from app.core.config import Settings
from app.services.azure_openai import AzureOpenAIProvider
from app.services.azure_search import AzureAISearchAdapter


def azure_settings() -> Settings:
    return Settings(
        azure_integrations_enabled=True,
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key="secret-value",
        azure_openai_deployment="architecture-model",
        azure_ai_search_endpoint="https://example.search.windows.net",
        azure_ai_search_api_key="search-secret",
        azure_ai_search_index="documents",
    )


async def test_azure_openai_adapter_streams_without_exposing_key() -> None:
    seen_headers: list[httpx.Headers] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": []})
        stream = (
            'data: {"choices":[{"delta":{"content":"Azure"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":" response"}}]}\n\n'
            "data: [DONE]\n\n"
        )
        return httpx.Response(200, content=stream)

    provider = AzureOpenAIProvider(azure_settings(), httpx.MockTransport(handler))
    status = await provider.status()
    content = "".join(
        [
            token
            async for token in provider.stream_chat(
                prompt="Design", model="architecture-model", system_prompt="Be concise"
            )
        ]
    )

    assert status.available is True
    assert content == "Azure response"
    assert all(headers["api-key"] == "secret-value" for headers in seen_headers)
    assert "secret-value" not in status.detail


async def test_azure_search_adapter_queries_existing_index() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"value": [{"title": "Architecture guide"}]})

    adapter = AzureAISearchAdapter(azure_settings(), httpx.MockTransport(handler))
    results = await adapter.search("event architecture", 3)

    assert results == [{"title": "Architecture guide"}]
    assert "/indexes/documents/docs/search" in str(captured["url"])
    assert captured["body"] == {"search": "event architecture", "top": 3}
