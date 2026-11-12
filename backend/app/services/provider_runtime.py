from collections.abc import AsyncIterator

from app.services.model_provider import ModelProvider


class ProviderRuntime:
    """Expose a configured model provider through the agent-runtime protocol."""

    def __init__(self, provider: ModelProvider) -> None:
        self._provider = provider

    def stream(
        self, *, prompt: str, model: str, system_prompt: str
    ) -> AsyncIterator[str]:
        return self._provider.stream_chat(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
        )
