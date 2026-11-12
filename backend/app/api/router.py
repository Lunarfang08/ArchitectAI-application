from fastapi import APIRouter

from app.api.routes.autogen import router as autogen_router
from app.api.routes.azure import router as azure_router
from app.api.routes.future import router as future_router
from app.api.routes.generation import router as generation_router
from app.api.routes.health import router as health_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.models import router as models_router
from app.api.routes.review import router as review_router
from app.api.routes.workspace import router as workspace_router

api_router = APIRouter()
api_router.include_router(future_router)
api_router.include_router(autogen_router)
api_router.include_router(azure_router)
api_router.include_router(generation_router)
api_router.include_router(health_router)
api_router.include_router(knowledge_router)
api_router.include_router(models_router)
api_router.include_router(review_router)
api_router.include_router(workspace_router)
