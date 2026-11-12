from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=10_000)


class ConversationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    model: str | None = Field(default=None, max_length=200)


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    title: str
    model: str
    created_at: datetime
    updated_at: datetime


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    conversation_count: int = 0


class ProjectDetail(ProjectSummary):
    conversations: list[ConversationSummary]


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant", "system"]
    content: str
    model: str | None
    status: Literal["completed", "streaming", "cancelled", "failed"]
    created_at: datetime
    updated_at: datetime

