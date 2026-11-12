from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_model_provider, get_review_runtime
from app.api.operation import OperationTrace, stream_headers
from app.core.config import get_settings
from app.database.session import get_db_session
from app.models import GenerationReview, ProjectGeneration
from app.schemas.review import GenerationReviewResponse
from app.services.generation import manifest_from_json
from app.services.langgraph_runtime import AgentRuntime
from app.services.model_provider import ModelProvider, ModelProviderError
from app.services.review import (
    ReviewError,
    parse_review,
    parse_test_manifest,
    report_from_json,
    review_json,
    review_prompt,
    test_prompt,
    tests_from_json,
    tests_json,
    write_test_manifest,
)

router = APIRouter(tags=["review"])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]
ReviewRuntimeDependency = Annotated[AgentRuntime, Depends(get_review_runtime)]
ProviderDependency = Annotated[ModelProvider, Depends(get_model_provider)]


def review_response(review: GenerationReview) -> GenerationReviewResponse:
    return GenerationReviewResponse(
        id=UUID(review.id),
        generation_id=UUID(review.generation_id),
        status=cast(Literal["staged", "approved"], review.status),
        report=report_from_json(review.report),
        test_manifest=tests_from_json(review.test_manifest),
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


async def _complete(
    runtime: AgentRuntime, *, prompt: str, system_prompt: str, model: str
) -> str:
    chunks = [
        token
        async for token in runtime.stream(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
        )
    ]
    return "".join(chunks)


async def _generation(
    session: AsyncSession, project_id: UUID, generation_id: UUID
) -> ProjectGeneration:
    generation = await session.get(ProjectGeneration, str(generation_id))
    if generation is None or generation.project_id != str(project_id):
        raise HTTPException(status_code=404, detail="Generated project not found.")
    return generation


@router.post(
    "/projects/{project_id}/generations/{generation_id}/reviews",
    response_model=GenerationReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def stage_review(
    project_id: UUID,
    generation_id: UUID,
    session: SessionDependency,
    runtime: ReviewRuntimeDependency,
    provider: ProviderDependency,
) -> GenerationReviewResponse:
    generation = await _generation(session, project_id, generation_id)
    manifest = manifest_from_json(generation.manifest)
    try:
        model = await provider.resolve_model()
        report = parse_review(
            await _complete(
                runtime,
                prompt=review_prompt(manifest),
                system_prompt=(
                    "You are the Code Reviewer agent. Analyze source text only, never execute it, "
                    "and return only the requested JSON report."
                ),
                model=model,
            )
        )
        test_manifest = parse_test_manifest(
            await _complete(
                runtime,
                prompt=test_prompt(manifest, report),
                system_prompt=(
                    "You are the Test Designer agent. Produce test source only, never execute it, "
                    "and return only the requested JSON manifest."
                ),
                model=model,
            )
        )
    except (ReviewError, ModelProviderError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    review = GenerationReview(
        generation_id=generation.id,
        status="staged",
        report=review_json(report),
        test_manifest=tests_json(test_manifest),
    )
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review_response(review)


@router.post("/projects/{project_id}/generations/{generation_id}/reviews/stream")
async def stream_stage_review(
    project_id: UUID,
    generation_id: UUID,
    session: SessionDependency,
    runtime: ReviewRuntimeDependency,
    provider: ProviderDependency,
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        trace = OperationTrace("review")
        yield trace.event("started", "load", "active", "Loading the staged source manifest")
        try:
            generation = await _generation(session, project_id, generation_id)
            manifest = manifest_from_json(generation.manifest)
            model = await provider.resolve_model()
            yield trace.event(
                "step",
                "reviewer",
                "active",
                "Reviewer is inspecting architecture, security, and correctness",
                detail=f"{len(manifest.files)} staged files supplied as source text",
            )
            review_chunks: list[str] = []
            review_tokens = 0
            async for token in runtime.stream(
                prompt=review_prompt(manifest),
                system_prompt=(
                    "You are the Code Reviewer agent. Analyze source text only, never execute it, "
                    "and return only the requested JSON report."
                ),
                model=model,
            ):
                review_chunks.append(token)
                review_tokens += 1
                if review_tokens % 40 == 0:
                    yield trace.event(
                        "detail",
                        "reviewer",
                        "active",
                        "Review analysis is active",
                        detail=f"{review_tokens} streamed model chunks received",
                    )
            report = parse_review("".join(review_chunks))
            yield trace.event(
                "step",
                "tests",
                "active",
                "Test Designer is turning findings into focused tests",
                detail=f"{len(report.findings)} review findings parsed",
            )
            test_chunks: list[str] = []
            test_tokens = 0
            async for token in runtime.stream(
                prompt=test_prompt(manifest, report),
                system_prompt=(
                    "You are the Test Designer agent. Produce test source only, never execute it, "
                    "and return only the requested JSON manifest."
                ),
                model=model,
            ):
                test_chunks.append(token)
                test_tokens += 1
                if test_tokens % 40 == 0:
                    yield trace.event(
                        "detail",
                        "tests",
                        "active",
                        "Test design is active",
                        detail=f"{test_tokens} streamed model chunks received",
                    )
            yield trace.event("step", "validate", "active", "Validating test locations and content")
            test_manifest = parse_test_manifest("".join(test_chunks))
            review = GenerationReview(
                generation_id=generation.id,
                status="staged",
                report=review_json(report),
                test_manifest=tests_json(test_manifest),
            )
            session.add(review)
            await session.commit()
            await session.refresh(review)
            yield trace.event(
                "completed",
                "ready",
                "complete",
                "Review and test proposal ready",
                detail=f"{len(report.findings)} findings · {len(test_manifest.files)} test files",
                result=review_response(review).model_dump(mode="json"),
            )
        except (ReviewError, ModelProviderError, HTTPException) as exc:
            message = exc.detail if isinstance(exc, HTTPException) else str(exc)
            yield trace.event("failed", "failed", "failed", str(message), detail=type(exc).__name__)

    return StreamingResponse(events(), media_type="text/event-stream", headers=stream_headers())


@router.get(
    "/projects/{project_id}/generations/{generation_id}/reviews",
    response_model=list[GenerationReviewResponse],
)
async def list_reviews(
    project_id: UUID, generation_id: UUID, session: SessionDependency
) -> list[GenerationReviewResponse]:
    await _generation(session, project_id, generation_id)
    statement = (
        select(GenerationReview)
        .where(GenerationReview.generation_id == str(generation_id))
        .order_by(GenerationReview.created_at.desc())
    )
    reviews = list((await session.scalars(statement)).all())
    return [review_response(review) for review in reviews]


@router.post(
    "/projects/{project_id}/generations/{generation_id}/reviews/{review_id}/approve",
    response_model=GenerationReviewResponse,
)
async def approve_review_tests(
    project_id: UUID,
    generation_id: UUID,
    review_id: UUID,
    session: SessionDependency,
) -> GenerationReviewResponse:
    generation = await _generation(session, project_id, generation_id)
    review = await session.get(GenerationReview, str(review_id))
    if review is None or review.generation_id != generation.id:
        raise HTTPException(status_code=404, detail="Staged review not found.")
    if generation.status != "approved" or generation.output_path is None:
        raise HTTPException(status_code=409, detail="Approve the generated project first.")
    if review.status != "staged":
        raise HTTPException(status_code=409, detail="Only staged test files can be approved.")
    try:
        await run_in_threadpool(
            write_test_manifest,
            tests_from_json(review.test_manifest),
            Path(generation.output_path),
            review_id,
            get_settings().generated_projects_dir,
        )
    except (ReviewError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    review.status = "approved"
    await session.commit()
    await session.refresh(review)
    return review_response(review)


@router.post(
    "/projects/{project_id}/generations/{generation_id}/reviews/{review_id}/approve/stream"
)
async def stream_approve_review_tests(
    project_id: UUID,
    generation_id: UUID,
    review_id: UUID,
    session: SessionDependency,
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        trace = OperationTrace("test-approval")
        yield trace.event("started", "validate", "active", "Verifying the approved project")
        try:
            generation = await _generation(session, project_id, generation_id)
            review = await session.get(GenerationReview, str(review_id))
            if review is None or review.generation_id != generation.id:
                raise ReviewError("Staged review not found.")
            if generation.status != "approved" or generation.output_path is None:
                raise ReviewError("Approve the generated project first.")
            if review.status != "staged":
                raise ReviewError("Only staged test files can be approved.")
            tests = tests_from_json(review.test_manifest)
            for index, test_file in enumerate(tests.files, 1):
                yield trace.event(
                    "step",
                    "write",
                    "active",
                    f"Preparing {test_file.path}",
                    detail=f"Test file {index} of {len(tests.files)} validated",
                )
            yield trace.event("step", "commit", "active", "Writing tests into restricted storage")
            await run_in_threadpool(
                write_test_manifest,
                tests,
                Path(generation.output_path),
                review_id,
                get_settings().generated_projects_dir,
            )
            review.status = "approved"
            await session.commit()
            await session.refresh(review)
            yield trace.event(
                "completed",
                "verified",
                "complete",
                "Test files written and verified",
                result=review_response(review).model_dump(mode="json"),
            )
        except (ReviewError, OSError, HTTPException) as exc:
            message = exc.detail if isinstance(exc, HTTPException) else str(exc)
            yield trace.event("failed", "failed", "failed", str(message), detail=type(exc).__name__)

    return StreamingResponse(events(), media_type="text/event-stream", headers=stream_headers())
