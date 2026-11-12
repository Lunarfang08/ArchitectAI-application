from pydantic import BaseModel, Field


class AzureStatus(BaseModel):
    enabled: bool
    selected_provider: str
    openai_configured: bool
    search_configured: bool
    credentials_exposed: bool = False


class AzureSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    limit: int = Field(default=4, ge=1, le=50)


class AzureSearchResponse(BaseModel):
    results: list[dict[str, object]]
