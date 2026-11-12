from collections.abc import AsyncIterator
from typing import Protocol

from app.schemas.models import ModelInfo, ModelStatus


class ModelProviderError(RuntimeError):
    """A model provider could not fulfill a request."""


class ModelProvider(Protocol):
    async def status(self) -> ModelStatus: ...

    async def list_models(self) -> list[ModelInfo]: ...

    async def resolve_model(self, requested_model: str | None = None) -> str: ...

    def stream_chat(
        self,
        *,
        prompt: str,
        model: str,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]: ...

