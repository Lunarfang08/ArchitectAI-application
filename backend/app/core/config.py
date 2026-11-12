from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    frontend_origin: AnyHttpUrl = AnyHttpUrl("http://localhost:3000")

    model_provider: Literal["ollama", "azure_openai"] = "ollama"
    ollama_base_url: AnyHttpUrl = AnyHttpUrl("http://127.0.0.1:11434")
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_fallback_model: str = "qwen2.5:3b"
    ollama_request_timeout_seconds: float = Field(default=600, gt=0, le=3600)
    model_max_output_tokens: int = Field(default=1_000, ge=256, le=8_192)
    # Zero disables the overall deadline; slow, healthy streams can finish naturally.
    architecture_generation_timeout_seconds: float = Field(default=0, ge=0, le=86400)

    database_url: str = "sqlite+aiosqlite:///./data/architect_ai.db"
    generated_projects_dir: Path = Path("./generated_projects")
    knowledge_base_dir: Path = Path("./knowledge_base")
    knowledge_chunk_size: int = Field(default=1_200, ge=200, le=4_000)
    knowledge_chunk_overlap: int = Field(default=200, ge=0, le=1_000)
    knowledge_retrieval_results: int = Field(default=4, ge=1, le=12)
    knowledge_upload_max_bytes: int = Field(default=2_000_000, ge=1_000, le=20_000_000)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    azure_integrations_enabled: bool = False
    azure_openai_endpoint: str = ""
    azure_openai_api_key: SecretStr = SecretStr("")
    azure_openai_deployment: str = ""
    azure_ai_search_endpoint: str = ""
    azure_ai_search_api_key: SecretStr = SecretStr("")
    azure_ai_search_index: str = ""
    azure_ai_search_api_version: str = "2025-09-01"
    autogen_experimental_enabled: bool = True
    langgraph_orchestration_enabled: bool = True

    def ensure_local_directories(self) -> None:
        self.generated_projects_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_base_dir.mkdir(parents=True, exist_ok=True)
        Path("./data").mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()

