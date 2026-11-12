from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    name: str
    size_bytes: int = 0
    modified_at: datetime | None = None


class ModelStatus(BaseModel):
    available: bool
    provider: str
    selected_model: str | None = None
    detail: str


class ModelsResponse(BaseModel):
    provider: str
    models: list[ModelInfo]


class ChatRequest(BaseModel):
    request_id: UUID | None = None
    prompt: str = Field(min_length=1, max_length=20_000)
    model: str | None = Field(default=None, max_length=200)
    system_prompt: str | None = Field(default=None, max_length=4_000)
    conversation_id: UUID | None = None
    use_knowledge_base: bool = True

