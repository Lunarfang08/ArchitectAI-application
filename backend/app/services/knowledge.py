import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import chromadb
from chromadb.api.types import IncludeEnum
from chromadb.config import Settings as ChromaSettings

from app.schemas.knowledge import KnowledgeDocument, KnowledgeMatch

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_./:-]+")
EMBEDDING_DIMENSIONS = 384


class KnowledgeBaseError(RuntimeError):
    """The local knowledge base could not fulfill a request."""


class KnowledgeBase:
    def __init__(self, directory: Path, *, chunk_size: int, chunk_overlap: int) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = min(chunk_overlap, chunk_size - 1)
        directory.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(directory / "chroma"),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="architect_ai_knowledge",
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _embed(text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for token in TOKEN_PATTERN.findall(text.lower()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            index = int.from_bytes(digest, "big") % EMBEDDING_DIMENSIONS
            vector[index] += 1.0
        magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / magnitude for value in vector]

    def _chunks(self, content: str) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(paragraph) > self._chunk_size:
                if current:
                    chunks.append(current)
                    current = ""
                step = self._chunk_size - self._chunk_overlap
                chunks.extend(
                    paragraph[start : start + self._chunk_size]
                    for start in range(0, len(paragraph), step)
                )
            elif not current:
                current = paragraph
            elif len(current) + len(paragraph) + 2 <= self._chunk_size:
                current = f"{current}\n\n{paragraph}"
            else:
                chunks.append(current)
                overlap = current[-self._chunk_overlap :] if self._chunk_overlap else ""
                current = f"{overlap}\n\n{paragraph}".strip()
        if current:
            chunks.append(current)
        return chunks

    def add_document(self, *, filename: str, content_type: str, content: str) -> KnowledgeDocument:
        clean_content = content.strip()
        if not clean_content:
            raise KnowledgeBaseError("The document is empty.")
        chunks = self._chunks(clean_content)
        document_id = str(uuid4())
        created_at = datetime.now(UTC)
        metadatas: list[Mapping[str, str | int | float | bool]] = [
            {
                "document_id": document_id,
                "filename": filename,
                "content_type": content_type,
                "chunk_index": index,
                "character_count": len(clean_content),
                "created_at": created_at.isoformat(),
            }
            for index in range(len(chunks))
        ]
        try:
            embeddings: list[Sequence[float]] = [self._embed(chunk) for chunk in chunks]
            self._collection.add(
                ids=[f"{document_id}:{index}" for index in range(len(chunks))],
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
            )
        except Exception as exc:
            raise KnowledgeBaseError("The document could not be indexed locally.") from exc
        return KnowledgeDocument(
            id=UUID(document_id),
            filename=filename,
            content_type=content_type,
            chunk_count=len(chunks),
            character_count=len(clean_content),
            created_at=created_at,
        )

    def list_documents(self) -> list[KnowledgeDocument]:
        result = self._collection.get(include=[IncludeEnum.metadatas])
        documents: dict[str, KnowledgeDocument] = {}
        for metadata in result.get("metadatas") or []:
            document_id = str(metadata["document_id"])
            if document_id in documents:
                documents[document_id].chunk_count += 1
                continue
            documents[document_id] = KnowledgeDocument(
                id=UUID(document_id),
                filename=str(metadata["filename"]),
                content_type=str(metadata["content_type"]),
                chunk_count=1,
                character_count=int(metadata["character_count"]),
                created_at=datetime.fromisoformat(str(metadata["created_at"])),
            )
        return sorted(documents.values(), key=lambda item: item.created_at, reverse=True)

    def search(self, query: str, limit: int) -> list[KnowledgeMatch]:
        if not query.strip() or self._collection.count() == 0:
            return []
        query_embeddings: list[Sequence[float]] = [self._embed(query)]
        result = self._collection.query(
            query_embeddings=query_embeddings,
            n_results=min(limit, self._collection.count()),
            include=[
                IncludeEnum.documents,
                IncludeEnum.metadatas,
                IncludeEnum.distances,
            ],
        )
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        matches = [
            KnowledgeMatch(
                document_id=UUID(str(metadata["document_id"])),
                filename=str(metadata["filename"]),
                chunk_index=int(metadata["chunk_index"]),
                content=document,
                distance=float(distance),
            )
            for document, metadata, distance in zip(
                documents, metadatas, distances, strict=True
            )
        ]
        return [match for match in matches if match.distance < 0.95]

    def delete_document(self, document_id: str) -> bool:
        result = self._collection.get(where={"document_id": document_id}, include=[])
        ids = result.get("ids") or []
        if not ids:
            return False
        self._collection.delete(ids=ids)
        return True
