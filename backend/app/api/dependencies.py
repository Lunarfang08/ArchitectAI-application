from functools import lru_cache

from app.core.config import get_settings
from app.services.autogen_runtime import AutoGenRuntime, AzureAutoGenRuntime
from app.services.azure_openai import AzureOpenAIProvider
from app.services.azure_search import AzureAISearchAdapter
from app.services.knowledge import KnowledgeBase
from app.services.langgraph_runtime import AgentRuntime, LangGraphRuntime
from app.services.model_provider import ModelProvider
from app.services.ollama import OllamaProvider
from app.services.provider_runtime import ProviderRuntime


@lru_cache
def get_model_provider() -> ModelProvider:
    settings = get_settings()
    if settings.model_provider == "azure_openai":
        return AzureOpenAIProvider(settings)
    return OllamaProvider(settings)


def _model_runtime() -> AgentRuntime:
    settings = get_settings()
    if settings.autogen_experimental_enabled:
        if settings.model_provider == "azure_openai":
            return AzureAutoGenRuntime(settings)
        return AutoGenRuntime(settings)
    return ProviderRuntime(get_model_provider())


@lru_cache
def get_agent_runtime() -> AgentRuntime:
    settings = get_settings()
    model_runtime = _model_runtime()
    if settings.langgraph_orchestration_enabled:
        return LangGraphRuntime(model_runtime)
    return model_runtime


@lru_cache
def get_generation_runtime() -> AgentRuntime:
    return _model_runtime()


@lru_cache
def get_review_runtime() -> AgentRuntime:
    return _model_runtime()


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    settings = get_settings()
    return KnowledgeBase(
        settings.knowledge_base_dir,
        chunk_size=settings.knowledge_chunk_size,
        chunk_overlap=settings.knowledge_chunk_overlap,
    )


@lru_cache
def get_azure_search_adapter() -> AzureAISearchAdapter:
    return AzureAISearchAdapter(get_settings())

