from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PRESETS = {
    "traffic": "Traffic increases 20 times during a product launch.",
    "database": "The primary database is unavailable for 30 minutes.",
    "security": "An application API key is accidentally exposed.",
    "dependency": "A critical dependency is compromised.",
    "regions": "The product must serve users across multiple regions.",
    "budget": "Infrastructure budget is reduced by 50 percent.",
    "privacy": "Users must be able to export and erase their personal data.",
    "team": "The original developer leaves with no handover.",
}


class SimulationCreate(BaseModel):
    scenario_type: str
    scenario_input: str = Field(default="", max_length=2000)

    @field_validator("scenario_type")
    @classmethod
    def known_type(cls, value: str) -> str:
        if value not in {*PRESETS, "custom"}:
            raise ValueError("Unknown scenario")
        return value

    @field_validator("scenario_input")
    @classmethod
    def clean_text(cls, value: str) -> str:
        if any(ord(c) < 32 and c not in "\n\t\r" for c in value):
            raise ValueError("Control characters are not supported")
        return value.strip()


class Scores(BaseModel):
    security: int = Field(ge=0, le=100)
    scalability: int = Field(ge=0, le=100)
    reliability: int = Field(ge=0, le=100)
    cost: int = Field(ge=0, le=100)
    maintainability: int = Field(ge=0, le=100)


class Component(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    cause: str
    mitigation: str
    files: list[str] = Field(default_factory=list, max_length=50)
    downstream: list[str] = Field(default_factory=list, max_length=20)


class TimelineEvent(BaseModel):
    time: str
    component_id: str
    state: Literal["stable", "warning", "failed"]
    description: str


class Repair(BaseModel):
    priority: Literal["high", "medium", "low"]
    title: str
    change: str
    files: list[str] = Field(default_factory=list)
    expected_improvement: str


class SimulationResult(BaseModel):
    summary: str = Field(min_length=1, max_length=4000)
    confidence: Literal["low", "medium", "high"]
    survival_score: int = Field(ge=0, le=100)
    scores: Scores
    components: list[Component] = Field(min_length=1, max_length=20)
    timeline: list[TimelineEvent] = Field(min_length=1, max_length=30)
    repairs: list[Repair] = Field(min_length=1, max_length=20)


class SimulationResponse(BaseModel):
    id: str
    project_id: str
    scenario_type: str
    scenario_input: str
    status: Literal["completed"] = "completed"
    result: SimulationResult
    model: str
    created_at: datetime
