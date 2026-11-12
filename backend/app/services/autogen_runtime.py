from collections.abc import AsyncIterator
from typing import Protocol

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import ModelClientStreamingChunkEvent
from autogen_core import CancellationToken
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient

from app.core.config import Settings
from app.services.model_provider import ModelProviderError


class AgentRuntime(Protocol):
    def stream(
        self, *, prompt: str, model: str, system_prompt: str
    ) -> AsyncIterator[str]: ...


class AutoGenRuntime:
    """Archived AutoGen bridge isolated behind ArchitectAI's runtime protocol."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def stream(
        self, *, prompt: str, model: str, system_prompt: str
    ) -> AsyncIterator[str]:
        client = OllamaChatCompletionClient(
            model=model,
            host=str(self._settings.ollama_base_url).rstrip("/"),
            options={"num_predict": self._settings.model_max_output_tokens},
        )
        agent = AssistantAgent(
            name="architect_ai_local_agent",
            description="A local software architecture assistant.",
            model_client=client,
            model_client_stream=True,
            system_message=system_prompt,
            tools=[],
            max_tool_iterations=1,
        )
        cancellation = CancellationToken()
        try:
            async for event in agent.run_stream(task=prompt, cancellation_token=cancellation):
                if isinstance(event, ModelClientStreamingChunkEvent) and event.content:
                    yield event.content
        except Exception as exc:
            raise ModelProviderError("The experimental AutoGen runtime failed.") from exc
        finally:
            cancellation.cancel()
            await client.close()


class AzureAutoGenRuntime:
    """AutoGen AssistantAgent backed by the optional Azure OpenAI v1 endpoint."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def stream(
        self, *, prompt: str, model: str, system_prompt: str
    ) -> AsyncIterator[str]:
        endpoint = self._settings.azure_openai_endpoint.rstrip("/")
        api_key = self._settings.azure_openai_api_key.get_secret_value()
        if not self._settings.azure_integrations_enabled or not endpoint or not api_key:
            raise ModelProviderError("Azure OpenAI is not fully configured.")
        client = OpenAIChatCompletionClient(
            model=model,
            base_url=f"{endpoint}/openai/v1/",
            api_key=api_key,
            default_headers={"api-key": api_key},
            model_info={
                "vision": False,
                "function_calling": True,
                "json_output": True,
                "family": "unknown",
                "structured_output": True,
            },
            max_tokens=self._settings.model_max_output_tokens,
        )
        agent = AssistantAgent(
            name="architect_ai_azure_agent",
            description="An optional Azure-backed software architecture assistant.",
            model_client=client,
            model_client_stream=True,
            system_message=system_prompt,
            tools=[],
            max_tool_iterations=1,
        )
        cancellation = CancellationToken()
        try:
            async for event in agent.run_stream(task=prompt, cancellation_token=cancellation):
                if isinstance(event, ModelClientStreamingChunkEvent) and event.content:
                    yield event.content
        except Exception as exc:
            raise ModelProviderError("The Azure-backed AutoGen runtime failed.") from exc
        finally:
            cancellation.cancel()
            await client.close()

