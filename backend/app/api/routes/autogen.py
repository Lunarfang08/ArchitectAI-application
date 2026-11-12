from importlib.metadata import version

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.autogen import AutoGenStatus

router = APIRouter(tags=["experimental"])


@router.get("/autogen/status", response_model=AutoGenStatus)
async def autogen_status() -> AutoGenStatus:
    settings = get_settings()
    return AutoGenStatus(
        enabled=settings.autogen_experimental_enabled,
        framework="Microsoft AutoGen AgentChat",
        version=version("autogen-agentchat"),
        model=settings.ollama_model,
    )

