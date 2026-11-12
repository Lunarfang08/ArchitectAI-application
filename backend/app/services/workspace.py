from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Conversation, Message, Project
from app.schemas.workspace import (
    ConversationCreate,
    ConversationSummary,
    ProjectCreate,
    ProjectDetail,
    ProjectSummary,
)


async def create_project(session: AsyncSession, payload: ProjectCreate) -> Project:
    project = Project(title=payload.title.strip(), description=payload.description.strip())
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def list_projects(session: AsyncSession, limit: int = 20) -> list[ProjectSummary]:
    statement = (
        select(Project, func.count(Conversation.id))
        .outerjoin(Conversation)
        .group_by(Project.id)
        .order_by(Project.updated_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(statement)).all()
    return [
        ProjectSummary(
            id=UUID(project.id),
            title=project.title,
            description=project.description,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
            conversation_count=count,
        )
        for project, count in rows
    ]


async def get_project_detail(session: AsyncSession, project_id: str) -> ProjectDetail | None:
    statement = (
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.conversations))
    )
    project = (await session.execute(statement)).scalar_one_or_none()
    if project is None:
        return None
    conversations = sorted(project.conversations, key=lambda item: item.updated_at, reverse=True)
    return ProjectDetail(
        id=UUID(project.id),
        title=project.title,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        conversation_count=len(conversations),
        conversations=[
            ConversationSummary.model_validate(conversation)
            for conversation in conversations
        ],
    )


async def create_conversation(
    session: AsyncSession,
    project: Project,
    payload: ConversationCreate,
    default_model: str,
) -> Conversation:
    conversation = Conversation(
        project_id=project.id,
        title=payload.title.strip(),
        model=payload.model or default_model,
    )
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def list_messages(session: AsyncSession, conversation_id: str) -> list[Message] | None:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        return None
    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )
    return list((await session.scalars(statement)).all())


def touch_workspace(project: Project, conversation: Conversation, timestamp: datetime) -> None:
    project.updated_at = timestamp
    conversation.updated_at = timestamp

