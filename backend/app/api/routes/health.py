from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_model_provider
from app.core.config import get_settings
from app.database.session import get_db_session
from app.models import Project
from app.schemas.health import HealthResponse, ServiceStatus
from app.services.model_provider import ModelProvider

router = APIRouter(tags=["system"])


@router.get("/ready")
async def ready(session: Annotated[AsyncSession, Depends(get_db_session)]) -> dict[str, str]:
    """Check database/schema readiness without contacting the model provider."""
    try:
        await session.execute(select(Project.id).limit(1))
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Database is not ready. Apply migrations first.") from exc
    return {"status": "ready"}


@router.get("/health", response_model=HealthResponse)
async def health(
    provider: Annotated[ModelProvider, Depends(get_model_provider)],
) -> HealthResponse:
    settings = get_settings()
    model_status = await provider.status()
    azure_openai_configured = bool(
        settings.azure_openai_endpoint
        and settings.azure_openai_api_key.get_secret_value()
        and settings.azure_openai_deployment
    )
    azure_search_configured = bool(
        settings.azure_ai_search_endpoint
        and settings.azure_ai_search_api_key.get_secret_value()
        and settings.azure_ai_search_index
    )
    return HealthResponse(
        status="ok" if model_status.available else "degraded",
        environment=settings.app_env,
        services={
            "api": ServiceStatus(status="ok"),
            "model_provider": ServiceStatus(
                status="ok" if model_status.available else "unavailable",
                detail=model_status.detail,
            ),
            "azure": ServiceStatus(
                status="disabled" if not settings.azure_integrations_enabled else "configured",
                detail=(
                    f"OpenAI: {'configured' if azure_openai_configured else 'missing config'}; "
                    f"AI Search: {'configured' if azure_search_configured else 'missing config'}"
                ),
            ),
            "autogen": ServiceStatus(
                status=(
                    "configured" if settings.autogen_experimental_enabled else "disabled"
                ),
                detail=f"Active agent runtime over {settings.model_provider}",
            ),
            "langgraph": ServiceStatus(
                status="configured" if settings.langgraph_orchestration_enabled else "disabled",
                detail="Planner, Research, and Architect orchestration over AutoGen",
            ),
            "knowledge_base": ServiceStatus(
                status="configured",
                detail="Local ChromaDB with deterministic offline embeddings",
            ),
        },
    )

