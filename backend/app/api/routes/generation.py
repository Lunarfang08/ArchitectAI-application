from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_generation_runtime
from app.api.operation import OperationTrace, stream_headers
from app.core.config import get_settings
from app.database.session import get_db_session
from app.models import Conversation, Message, Project, ProjectGeneration
from app.schemas.generation import GenerationCreate, GenerationResponse
from app.services.generation import (
    GenerationError,
    generation_prompt,
    manifest_from_json,
    manifest_json,
    parse_manifest,
    write_manifest,
)
from app.services.langgraph_runtime import AgentRuntime
from app.services.model_provider import ModelProviderError

router = APIRouter(tags=["generation"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]
GenerationRuntimeDependency = Annotated[AgentRuntime, Depends(get_generation_runtime)]


def generation_response(generation: ProjectGeneration) -> GenerationResponse:
    return GenerationResponse(
        id=UUID(generation.id),
        project_id=UUID(generation.project_id),
        name=generation.name,
        status=generation.status,  # type: ignore[arg-type]
        manifest=manifest_from_json(generation.manifest),
        output_path=generation.output_path,
        created_at=generation.created_at,
        updated_at=generation.updated_at,
    )


@router.post(
    "/projects/{project_id}/generations",
    response_model=GenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def stage_generation(
    project_id: UUID,
    payload: GenerationCreate,
    session: SessionDependency,
    runtime: GenerationRuntimeDependency,
) -> GenerationResponse:
    project = await session.get(Project, str(project_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    statement = (
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.project_id == project.id,
            Message.role == "assistant",
            Message.status == "completed",
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    architecture = (await session.execute(statement)).scalar_one_or_none()
    if architecture is None:
        raise HTTPException(
            status_code=409,
            detail="Generate and complete an architecture response before staging files.",
        )
    prompt = generation_prompt(
        title=project.title,
        requirement=project.description,
        architecture=architecture.content,
    )
    try:
        chunks = [
            token
            async for token in runtime.stream(
                prompt=prompt,
                model=architecture.model or get_settings().ollama_model,
                system_prompt=(
                    "You are a project-generation agent. Return only the requested JSON manifest. "
                    "Never use absolute paths, parent traversal, secrets, or binary content."
                ),
            )
        ]
        manifest = parse_manifest("".join(chunks))
    except (GenerationError, ModelProviderError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    generation = ProjectGeneration(
        project_id=project.id,
        name=payload.name.strip(),
        status="staged",
        manifest=manifest_json(manifest),
    )
    session.add(generation)
    await session.commit()
    await session.refresh(generation)
    return generation_response(generation)


@router.post("/projects/{project_id}/generations/stream")
async def stream_stage_generation(
    project_id: UUID,
    payload: GenerationCreate,
    session: SessionDependency,
    runtime: GenerationRuntimeDependency,
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        trace = OperationTrace("generation")
        yield trace.event("started", "load", "active", "Loading approved architecture")
        try:
            project = await session.get(Project, str(project_id))
            if project is None:
                raise GenerationError("Project not found.")
            statement = (
                select(Message)
                .join(Conversation, Message.conversation_id == Conversation.id)
                .where(
                    Conversation.project_id == project.id,
                    Message.role == "assistant",
                    Message.status == "completed",
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            architecture = (await session.execute(statement)).scalar_one_or_none()
            if architecture is None:
                raise GenerationError("Complete an architecture response before staging files.")
            yield trace.event("step", "prompt", "complete", "Architecture context assembled")
            prompt = generation_prompt(
                title=project.title,
                requirement=project.description,
                architecture=architecture.content,
            )
            yield trace.event("step", "model", "active", "Generating the project blueprint")
            chunks: list[str] = []
            token_count = 0
            async for token in runtime.stream(
                prompt=prompt,
                model=architecture.model or get_settings().ollama_model,
                system_prompt=(
                    "You are a project-generation agent. Return only the requested JSON manifest. "
                    "Never use absolute paths, parent traversal, secrets, or binary content."
                ),
            ):
                chunks.append(token)
                token_count += 1
                if token_count % 40 == 0:
                    yield trace.event(
                        "detail",
                        "model",
                        "active",
                        "Blueprint generation is active",
                        detail=f"{token_count} streamed model chunks received",
                    )
            yield trace.event("step", "validate", "active", "Validating generated files")
            manifest = parse_manifest("".join(chunks))
            yield trace.event(
                "step",
                "persist",
                "active",
                "Saving the staged manifest",
                detail=f"{len(manifest.files)} safe paths validated",
            )
            generation = ProjectGeneration(
                project_id=project.id,
                name=payload.name.strip(),
                status="staged",
                manifest=manifest_json(manifest),
            )
            session.add(generation)
            await session.commit()
            await session.refresh(generation)
            result = generation_response(generation).model_dump(mode="json")
            yield trace.event(
                "completed",
                "ready",
                "complete",
                "Project blueprint ready for approval",
                result=result,
            )
        except (GenerationError, ModelProviderError) as exc:
            yield trace.event("failed", "failed", "failed", str(exc), detail=type(exc).__name__)

    return StreamingResponse(events(), media_type="text/event-stream", headers=stream_headers())


@router.get("/projects/{project_id}/generations", response_model=list[GenerationResponse])
async def list_generations(
    project_id: UUID, session: SessionDependency
) -> list[GenerationResponse]:
    project = await session.get(Project, str(project_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    statement = (
        select(ProjectGeneration)
        .where(ProjectGeneration.project_id == str(project_id))
        .order_by(ProjectGeneration.created_at.desc())
    )
    generations = list((await session.scalars(statement)).all())
    return [generation_response(generation) for generation in generations]


@router.post(
    "/projects/{project_id}/generations/{generation_id}/approve",
    response_model=GenerationResponse,
)
async def approve_generation(
    project_id: UUID, generation_id: UUID, session: SessionDependency
) -> GenerationResponse:
    generation = await session.get(ProjectGeneration, str(generation_id))
    if generation is None or generation.project_id != str(project_id):
        raise HTTPException(status_code=404, detail="Staged generation not found.")
    if generation.status != "staged":
        raise HTTPException(status_code=409, detail="Only staged generations can be approved.")
    settings = get_settings()
    try:
        output_path = await run_in_threadpool(
            write_manifest,
            manifest=manifest_from_json(generation.manifest),
            root=settings.generated_projects_dir,
            project_id=generation.project_id,
            generation_id=generation.id,
            name=generation.name,
        )
    except (GenerationError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    generation.status = "approved"
    generation.output_path = str(output_path)
    await session.commit()
    await session.refresh(generation)
    return generation_response(generation)


@router.post("/projects/{project_id}/generations/{generation_id}/approve/stream")
async def stream_approve_generation(
    project_id: UUID, generation_id: UUID, session: SessionDependency
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        trace = OperationTrace("file-approval")
        yield trace.event("started", "validate", "active", "Validating the staged project")
        try:
            generation = await session.get(ProjectGeneration, str(generation_id))
            if generation is None or generation.project_id != str(project_id):
                raise GenerationError("Staged generation not found.")
            if generation.status != "staged":
                raise GenerationError("Only staged generations can be approved.")
            manifest = manifest_from_json(generation.manifest)
            for index, generated_file in enumerate(manifest.files, 1):
                yield trace.event(
                    "step",
                    "write",
                    "active",
                    f"Preparing {generated_file.path}",
                    detail=f"File {index} of {len(manifest.files)} passed path validation",
                )
            yield trace.event("step", "commit", "active", "Writing the verified project atomically")
            settings = get_settings()
            output_path = await run_in_threadpool(
                write_manifest,
                manifest=manifest,
                root=settings.generated_projects_dir,
                project_id=generation.project_id,
                generation_id=generation.id,
                name=generation.name,
            )
            generation.status = "approved"
            generation.output_path = str(output_path)
            await session.commit()
            await session.refresh(generation)
            yield trace.event(
                "completed",
                "verified",
                "complete",
                "Project written and verified locally",
                detail=str(output_path),
                result=generation_response(generation).model_dump(mode="json"),
            )
        except (GenerationError, OSError) as exc:
            yield trace.event("failed", "failed", "failed", str(exc), detail=type(exc).__name__)

    return StreamingResponse(events(), media_type="text/event-stream", headers=stream_headers())
