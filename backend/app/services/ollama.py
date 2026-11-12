import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import Settings
from app.schemas.models import ModelInfo, ModelStatus
from app.services.model_provider import ModelProviderError


class OllamaProvider:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=str(self._settings.ollama_base_url).rstrip("/"),
            timeout=httpx.Timeout(self._settings.ollama_request_timeout_seconds, connect=10),
            transport=self._transport,
        )

    async def status(self) -> ModelStatus:
        try:
            models = await self.list_models()
        except ModelProviderError as exc:
            return ModelStatus(available=False, provider="ollama", detail=str(exc))

        names = {model.name for model in models}
        selected = await self._select_from_names(names)
        detail = f"Using {selected}" if selected else "No configured model is installed"
        return ModelStatus(
            available=selected is not None,
            provider="ollama",
            selected_model=selected,
            detail=detail,
        )

    async def list_models(self) -> list[ModelInfo]:
        try:
            async with self._client() as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ModelProviderError(
                "Ollama is unavailable. Start Ollama and confirm its local URL."
            ) from exc

        payload: dict[str, Any] = response.json()
        return [
            ModelInfo(
                name=str(item["name"]),
                size_bytes=int(item.get("size", 0)),
                modified_at=item.get("modified_at"),
            )
            for item in payload.get("models", [])
            if item.get("name")
        ]

    async def _select_from_names(self, names: set[str]) -> str | None:
        if self._settings.ollama_model in names:
            return self._settings.ollama_model
        if self._settings.ollama_fallback_model in names:
            return self._settings.ollama_fallback_model
        return None

    async def resolve_model(self, requested_model: str | None = None) -> str:
        models = await self.list_models()
        names = {model.name for model in models}
        if requested_model:
            if requested_model not in names:
                raise ModelProviderError(f"Requested model '{requested_model}' is not installed.")
            return requested_model

        selected = await self._select_from_names(names)
        if selected is None:
            raise ModelProviderError(
                "Neither the primary nor fallback Ollama model is installed."
            )
        return selected

    async def stream_chat(
        self,
        *,
        prompt: str,
        model: str,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with self._client() as client:
                async with client.stream(
                    "POST",
                    "/api/chat",
                    json={"model": model, "messages": messages, "stream": True},
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        chunk: dict[str, Any] = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield str(content)
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise ModelProviderError("Ollama stopped or returned an invalid stream.") from exc

