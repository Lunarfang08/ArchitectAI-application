from typing import Any

import httpx

from app.core.config import Settings


class AzureSearchError(RuntimeError):
    """The optional Azure AI Search adapter could not fulfill a request."""


class AzureAISearchAdapter:
    """Optional text-search adapter for an existing Azure AI Search index."""

    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._settings = settings
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(
            self._settings.azure_integrations_enabled
            and self._settings.azure_ai_search_endpoint
            and self._settings.azure_ai_search_api_key.get_secret_value()
            and self._settings.azure_ai_search_index
        )

    async def search(self, query: str, limit: int = 4) -> list[dict[str, Any]]:
        if not self.configured:
            raise AzureSearchError("Azure AI Search is not configured.")
        endpoint = self._settings.azure_ai_search_endpoint.rstrip("/")
        if not endpoint.startswith("https://"):
            raise AzureSearchError("Azure AI Search endpoint must use HTTPS.")
        index = self._settings.azure_ai_search_index
        url = (
            f"{endpoint}/indexes/{index}/docs/search"
            f"?api-version={self._settings.azure_ai_search_api_version}"
        )
        try:
            async with httpx.AsyncClient(
                headers={"api-key": self._settings.azure_ai_search_api_key.get_secret_value()},
                timeout=self._settings.ollama_request_timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(url, json={"search": query, "top": limit})
                response.raise_for_status()
                values = response.json().get("value", [])
            return [dict(item) for item in values]
        except (httpx.HTTPError, ValueError) as exc:
            raise AzureSearchError("Azure AI Search request failed.") from exc
