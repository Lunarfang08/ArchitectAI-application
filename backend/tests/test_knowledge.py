from fastapi.testclient import TestClient

from app.main import app


def test_document_ingestion_search_and_deletion() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/knowledge/documents",
            files={
                "file": (
                    "architecture.md",
                    b"# Payments\n\nUse an outbox pattern for reliable payment events.",
                    "text/markdown",
                )
            },
        )
        listed = client.get("/api/v1/knowledge/documents")
        searched = client.post(
            "/api/v1/knowledge/search",
            json={"query": "reliable payment event pattern", "limit": 4},
        )
        deleted = client.delete(
            f"/api/v1/knowledge/documents/{created.json()['id']}"
        )
        empty = client.get("/api/v1/knowledge/documents")

    assert created.status_code == 201
    assert created.json()["filename"] == "architecture.md"
    assert len(listed.json()) == 1
    assert searched.json()["matches"][0]["filename"] == "architecture.md"
    assert deleted.status_code == 204
    assert empty.json() == []


def test_rejects_binary_and_unsupported_documents() -> None:
    with TestClient(app) as client:
        unsupported = client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("manual.pdf", b"pdf", "application/pdf")},
        )
        binary = client.post(
            "/api/v1/knowledge/documents",
            files={"file": ("manual.txt", b"\xff\xfe", "text/plain")},
        )

    assert unsupported.status_code == 415
    assert binary.status_code == 422
