import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import Settings
from app.schemas.models import ModelInfo, ModelStatus
from app.services.model_provider import ModelProviderError


class AzureOpenAIProvider:
    """Optional Azure OpenAI v1 chat-completions adapter."""

    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._settings = settings
        self._transport = transport

    def _configuration(self) -> tuple[str, str, str]:
        endpoint = self._settings.azure_openai_endpoint.rstrip("/")
        api_key = self._settings.azure_openai_api_key.get_secret_value()
        deployment = self._settings.azure_openai_deployment.strip()
        if not self._settings.azure_integrations_enabled:
            raise ModelProviderError("Azure integrations are disabled.")
        if not endpoint or not api_key or not deployment:
            raise ModelProviderError(
                "Azure OpenAI requires endpoint, API key, and deployment configuration."
            )
        if not endpoint.startswith("https://"):
            raise ModelProviderError("Azure OpenAI endpoint must use HTTPS.")
        return endpoint, api_key, deployment

    def _client(self) -> httpx.AsyncClient:
        _, api_key, _ = self._configuration()
        return httpx.AsyncClient(
            headers={"api-key": api_key, "Content-Type": "application/json"},
            timeout=self._settings.ollama_request_timeout_seconds,
            transport=self._transport,
        )

    async def status(self) -> ModelStatus:
        try:
            endpoint, _, deployment = self._configuration()
            async with self._client() as client:
                response = await client.get(f"{endpoint}/openai/v1/models")
                response.raise_for_status()
            return ModelStatus(
                available=True,
                provider="azure_openai",
                selected_model=deployment,
                detail=f"Using Azure deployment {deployment}",
            )
        except (ModelProviderError, httpx.HTTPError) as exc:
            return ModelStatus(
                available=False,
                provider="azure_openai",
                selected_model=None,
                detail=(
                    str(exc)
                    if isinstance(exc, ModelProviderError)
                    else "Azure OpenAI unavailable."
                ),
            )

    async def list_models(self) -> list[ModelInfo]:
        _, _, deployment = self._configuration()
        return [ModelInfo(name=deployment)]

    async def resolve_model(self, requested_model: str | None = None) -> str:
        _, _, deployment = self._configuration()
        if requested_model and requested_model != deployment:
            raise ModelProviderError(
                f"Azure deployment '{requested_model}' is not configured for this application."
            )
        return deployment

    async def stream_chat(
        self,
        *,
        prompt: str,
        model: str,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        endpoint, _, deployment = self._configuration()
        if model != deployment:
            raise ModelProviderError("The requested Azure deployment is not configured.")
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            async with self._client() as client:
                async with client.stream(
                    "POST",
                    f"{endpoint}/openai/v1/chat/completions",
                    json={"model": deployment, "messages": messages, "stream": True},
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        payload = line.removeprefix("data:").strip()
                        if payload == "[DONE]":
                            break
                        data = json.loads(payload)
                        content = data.get("choices", [{}])[0].get("delta", {}).get("content")
                        if content:
                            yield str(content)
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError) as exc:
            raise ModelProviderError("The Azure OpenAI stream failed.") from exc
