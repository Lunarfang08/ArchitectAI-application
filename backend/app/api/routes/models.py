import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import anyio
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_agent_runtime, get_knowledge_base, get_model_provider
from app.core.config import get_settings
from app.database.session import get_db_session
from app.models import Conversation, Message, Project
from app.schemas.models import ChatRequest, ModelsResponse
from app.services.knowledge import KnowledgeBase
from app.services.langgraph_runtime import AgentRuntime
from app.services.model_provider import ModelProvider, ModelProviderError
from app.services.streaming import with_heartbeats
from app.services.workspace import touch_workspace

router = APIRouter(tags=["models"])
active_streams: dict[str, asyncio.Task] = {}


@router.post("/chat/streams/{request_id}/cancel")
async def cancel_stream(request_id: UUID) -> dict[str, bool]:
    task = active_streams.get(str(request_id))
    if task is not None:
        task.cancel()
    return {"cancelled": task is not None}
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]
DEFAULT_SYSTEM_PROMPT = (
    "Respond using clear GitHub-Flavored Markdown. Never wrap the entire response in a "
    "markdown or md code fence. Use fenced code blocks only for actual source code."
)


def _sse(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@router.get("/models", response_model=ModelsResponse)
async def list_models(
    provider: Annotated[ModelProvider, Depends(get_model_provider)],
) -> ModelsResponse:
    try:
        models = await provider.list_models()
    except ModelProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return ModelsResponse(provider=get_settings().model_provider, models=models)


@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    provider: Annotated[ModelProvider, Depends(get_model_provider)],
    agent_runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
    knowledge: Annotated[KnowledgeBase, Depends(get_knowledge_base)],
    session: SessionDependency,
) -> StreamingResponse:
    try:
        model = await provider.resolve_model(request.model)
    except ModelProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    title = next(
        (line.strip() for line in request.prompt.splitlines() if line.strip()),
        "New project",
    )
    title = title[:157] + "..." if len(title) > 160 else title

    if request.conversation_id is None:
        project = Project(title=title, description=request.prompt[:10_000])
        session.add(project)
        await session.flush()
        conversation = Conversation(project_id=project.id, title=title, model=model)
        session.add(conversation)
        await session.flush()
    else:
        saved_conversation = await session.get(Conversation, str(request.conversation_id))
        if saved_conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
            )
        saved_project = await session.get(Project, saved_conversation.project_id)
        if saved_project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        conversation = saved_conversation
        project = saved_project

    now = datetime.now(UTC)
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.prompt,
        status="completed",
    )
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content="",
        model=model,
        status="streaming",
    )
    touch_workspace(project, conversation, now)
    session.add_all([user_message, assistant_message])
    await session.commit()

    async def finish_message(content: str, message_status: str) -> None:
        assistant_message.content = content
        assistant_message.status = message_status
        timestamp = datetime.now(UTC)
        touch_workspace(project, conversation, timestamp)
        await session.commit()

    async def event_stream() -> AsyncIterator[str]:
        settings = get_settings()
        matches = (
            await run_in_threadpool(
                knowledge.search,
                request.prompt,
                settings.knowledge_retrieval_results,
            )
            if request.use_knowledge_base
            else []
        )
        sources = sorted({match.filename for match in matches})
        if settings.langgraph_orchestration_enabled:
            framework = (
                (
                    "langgraph+autogen+azure"
                    if settings.model_provider == "azure_openai"
                    else "langgraph+autogen"
                )
                if settings.autogen_experimental_enabled
                else "langgraph+azure"
            )
        elif settings.autogen_experimental_enabled:
            framework = "autogen"
        else:
            framework = "direct"
        metadata: dict[str, object] = {
            "provider": settings.model_provider,
            "model": model,
            "framework": framework,
            "project_id": project.id,
            "conversation_id": conversation.id,
            "message_id": assistant_message.id,
            "sources": sources,
        }
        yield _sse("metadata", metadata)
        chunks: list[str] = []
        try:
            system_prompt = request.system_prompt or DEFAULT_SYSTEM_PROMPT
            runtime_prompt = request.prompt
            if matches:
                context = "\n\n".join(
                    f"[Source: {match.filename}, chunk {match.chunk_index + 1}]\n{match.content}"
                    for match in matches
                )
                runtime_prompt = (
                    f"{request.prompt}\n\nRetrieved local knowledge:\n{context}\n\n"
                    "Use retrieved content when relevant, cite sources by filename, and do not "
                    "invent facts that are absent from the sources."
                )
            token_stream = (
                agent_runtime.stream(
                    prompt=runtime_prompt,
                    model=model,
                    system_prompt=system_prompt,
                )
                if (
                    settings.langgraph_orchestration_enabled
                    or settings.autogen_experimental_enabled
                )
                else provider.stream_chat(
                    prompt=runtime_prompt,
                    model=model,
                    system_prompt=system_prompt,
                )
            )
            try:
                deadline = settings.architecture_generation_timeout_seconds or None
                async with asyncio.timeout(deadline):
                    async for token in with_heartbeats(token_stream):
                        if token is None:
                            yield ": generation in progress\n\n"
                            continue
                        chunks.append(token)
                        yield _sse("token", {"content": token})
            except TimeoutError:
                await finish_message("".join(chunks), "failed")
                yield _sse(
                    "error",
                    {
                        "message": (
                            "The configured generation deadline was reached. Partial output "
                            "has been saved. Set ARCHITECTURE_GENERATION_TIMEOUT_SECONDS=0 "
                            "to allow generation to finish without an overall deadline."
                        ),
                        **metadata,
                    },
                )
                return
            await finish_message("".join(chunks), "completed")
            yield _sse("done", metadata)
        except asyncio.CancelledError:
            with anyio.CancelScope(shield=True):
                await finish_message("".join(chunks), "cancelled")
            raise
        except ModelProviderError as exc:
            await finish_message("".join(chunks), "failed")
            yield _sse("error", {"message": str(exc), **metadata})
        except Exception:
            await finish_message("".join(chunks), "failed")
            yield _sse(
                "error",
                {"message": "The local model stream failed unexpectedly.", **metadata},
            )

    async def tracked_stream() -> AsyncIterator[str]:
        task = asyncio.current_task()
        if request.request_id is not None and task is not None:
            active_streams[str(request.request_id)] = task
        try:
            async for event in event_stream():
                yield event
        finally:
            if request.request_id is not None:
                active_streams.pop(str(request.request_id), None)

    return StreamingResponse(
        tracked_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

