from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_azure_search_adapter
from app.core.config import get_settings
from app.schemas.azure import AzureSearchRequest, AzureSearchResponse, AzureStatus
from app.services.azure_search import AzureAISearchAdapter, AzureSearchError

router = APIRouter(tags=["azure"])


@router.get("/azure/status", response_model=AzureStatus)
async def azure_status() -> AzureStatus:
    settings = get_settings()
    openai_configured = bool(
        settings.azure_openai_endpoint
        and settings.azure_openai_api_key.get_secret_value()
        and settings.azure_openai_deployment
    )
    search_configured = bool(
        settings.azure_ai_search_endpoint
        and settings.azure_ai_search_api_key.get_secret_value()
        and settings.azure_ai_search_index
    )
    return AzureStatus(
        enabled=settings.azure_integrations_enabled,
        selected_provider=settings.model_provider,
        openai_configured=openai_configured,
        search_configured=search_configured,
    )


@router.post("/azure/search", response_model=AzureSearchResponse)
async def azure_search(
    payload: AzureSearchRequest,
    adapter: Annotated[AzureAISearchAdapter, Depends(get_azure_search_adapter)],
) -> AzureSearchResponse:
    try:
        results = await adapter.search(payload.query, payload.limit)
    except AzureSearchError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AzureSearchResponse(results=results)
