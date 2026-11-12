from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_model_provider
from app.database.session import get_db_session
from app.models import Project
from app.schemas.workspace import (
    ConversationCreate,
    ConversationSummary,
    MessageResponse,
    ProjectCreate,
    ProjectDetail,
    ProjectSummary,
)
from app.services.model_provider import ModelProvider, ModelProviderError
from app.services.workspace import (
    create_conversation,
    create_project,
    get_project_detail,
    list_messages,
    list_projects,
)

router = APIRouter(tags=["workspace"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]
ProviderDependency = Annotated[ModelProvider, Depends(get_model_provider)]


@router.post("/projects", response_model=ProjectSummary, status_code=status.HTTP_201_CREATED)
async def post_project(payload: ProjectCreate, session: SessionDependency) -> ProjectSummary:
    project = await create_project(session, payload)
    return ProjectSummary.model_validate(project)


@router.get("/projects", response_model=list[ProjectSummary])
async def get_projects(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ProjectSummary]:
    return await list_projects(session, limit)


@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: UUID, session: SessionDependency) -> ProjectDetail:
    project = await get_project_detail(session, str(project_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return project


@router.post(
    "/projects/{project_id}/conversations",
    response_model=ConversationSummary,
    status_code=status.HTTP_201_CREATED,
)
async def post_conversation(
    project_id: UUID,
    payload: ConversationCreate,
    session: SessionDependency,
    provider: ProviderDependency,
) -> ConversationSummary:
    project = await session.get(Project, str(project_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    try:
        model = await provider.resolve_model(payload.model)
    except ModelProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    conversation = await create_conversation(session, project, payload, model)
    return ConversationSummary.model_validate(conversation)


@router.get(
    "/conversations/{conversation_id}/messages", response_model=list[MessageResponse]
)
async def get_conversation_messages(
    conversation_id: UUID, session: SessionDependency
) -> list[MessageResponse]:
    messages = await list_messages(session, str(conversation_id))
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
        )
    return [MessageResponse.model_validate(message) for message in messages]

