from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_knowledge_base
from app.api.operation import OperationTrace, stream_headers
from app.core.config import get_settings
from app.schemas.knowledge import (
    KnowledgeDocument,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services.knowledge import KnowledgeBase, KnowledgeBaseError

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
KnowledgeDependency = Annotated[KnowledgeBase, Depends(get_knowledge_base)]
ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".yaml", ".yml", ".csv"}


@router.post("/documents", response_model=KnowledgeDocument, status_code=status.HTTP_201_CREATED)
async def upload_document(
    knowledge: KnowledgeDependency,
    file: Annotated[UploadFile, File(description="UTF-8 text or Markdown document")],
) -> KnowledgeDocument:
    settings = get_settings()
    filename = (file.filename or "document.txt").split("/")[-1].split("\\")[-1]
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported files: TXT, Markdown, JSON, YAML, and CSV.",
        )
    payload = await file.read(settings.knowledge_upload_max_bytes + 1)
    if len(payload) > settings.knowledge_upload_max_bytes:
        raise HTTPException(status_code=413, detail="The document exceeds the upload limit.")
    try:
        content = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="The document must be UTF-8 text.") from exc
    try:
        return await run_in_threadpool(
            knowledge.add_document,
            filename=filename,
            content_type=file.content_type or "text/plain",
            content=content,
        )
    except KnowledgeBaseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/documents/stream")
async def stream_upload_document(
    knowledge: KnowledgeDependency,
    file: Annotated[UploadFile, File(description="UTF-8 text or Markdown document")],
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        trace = OperationTrace("knowledge")
        settings = get_settings()
        filename = (file.filename or "document.txt").split("/")[-1].split("\\")[-1]
        yield trace.event("started", "receive", "active", f"Receiving {filename}")
        try:
            extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if extension not in ALLOWED_EXTENSIONS:
                raise KnowledgeBaseError("Supported files: TXT, Markdown, JSON, YAML, and CSV.")
            payload = await file.read(settings.knowledge_upload_max_bytes + 1)
            if len(payload) > settings.knowledge_upload_max_bytes:
                raise KnowledgeBaseError("The document exceeds the upload limit.")
            yield trace.event(
                "step",
                "decode",
                "active",
                "Decoding and validating UTF-8 content",
                detail=f"{len(payload):,} bytes received",
            )
            try:
                content = payload.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise KnowledgeBaseError("The document must be UTF-8 text.") from exc
            yield trace.event(
                "step", "index", "active", "Chunking and embedding the document locally"
            )
            document = await run_in_threadpool(
                knowledge.add_document,
                filename=filename,
                content_type=file.content_type or "text/plain",
                content=content,
            )
            yield trace.event(
                "completed",
                "ready",
                "complete",
                "Document indexed and ready for retrieval",
                detail=f"{document.chunk_count} chunks · {document.character_count:,} characters",
                result=document.model_dump(mode="json"),
            )
        except KnowledgeBaseError as exc:
            yield trace.event("failed", "failed", "failed", str(exc), detail=type(exc).__name__)

    return StreamingResponse(events(), media_type="text/event-stream", headers=stream_headers())


@router.get("/documents", response_model=list[KnowledgeDocument])
async def list_documents(knowledge: KnowledgeDependency) -> list[KnowledgeDocument]:
    return await run_in_threadpool(knowledge.list_documents)


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_documents(
    payload: KnowledgeSearchRequest, knowledge: KnowledgeDependency
) -> KnowledgeSearchResponse:
    matches = await run_in_threadpool(knowledge.search, payload.query, payload.limit)
    return KnowledgeSearchResponse(matches=matches)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: UUID, knowledge: KnowledgeDependency) -> None:
    deleted = await run_in_threadpool(knowledge.delete_document, str(document_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge document not found.")
