from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class GeneratedFile(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=100_000)


class GenerationManifest(BaseModel):
    summary: str = Field(min_length=1, max_length=2_000)
    files: list[GeneratedFile] = Field(min_length=1, max_length=50)


class GenerationCreate(BaseModel):
    name: str = Field(default="generated-app", min_length=1, max_length=100)


class GenerationResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    status: Literal["staged", "approved", "failed"]
    manifest: GenerationManifest
    output_path: str | None
    created_at: datetime
    updated_at: datetime
