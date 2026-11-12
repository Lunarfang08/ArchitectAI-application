from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeDocument(BaseModel):
    id: UUID
    filename: str
    content_type: str
    chunk_count: int
    character_count: int
    created_at: datetime


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    limit: int = Field(default=4, ge=1, le=12)


class KnowledgeMatch(BaseModel):
    document_id: UUID
    filename: str
    chunk_index: int
    content: str
    distance: float


class KnowledgeSearchResponse(BaseModel):
    matches: list[KnowledgeMatch]
