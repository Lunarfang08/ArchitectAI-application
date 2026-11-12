from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.generation import GenerationManifest


class ReviewFinding(BaseModel):
    severity: Literal["critical", "high", "medium", "low", "info"]
    path: str | None = Field(default=None, max_length=240)
    issue: str = Field(min_length=1, max_length=2_000)
    recommendation: str = Field(min_length=1, max_length=2_000)


class ReviewReport(BaseModel):
    summary: str = Field(min_length=1, max_length=4_000)
    findings: list[ReviewFinding] = Field(default_factory=list, max_length=50)


class GenerationReviewResponse(BaseModel):
    id: UUID
    generation_id: UUID
    status: Literal["staged", "approved"]
    report: ReviewReport
    test_manifest: GenerationManifest
    created_at: datetime
    updated_at: datetime
