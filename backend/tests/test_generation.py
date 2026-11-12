from pathlib import Path

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_agent_runtime,
    get_generation_runtime,
    get_model_provider,
)
from app.main import app
from tests.fakes import FakeAgentRuntime, FakeGenerationRuntime, FakeModelProvider


def test_generation_requires_preview_then_explicit_approval() -> None:
    app.dependency_overrides[get_model_provider] = FakeModelProvider
    app.dependency_overrides[get_agent_runtime] = FakeAgentRuntime
    app.dependency_overrides[get_generation_runtime] = FakeGenerationRuntime
    try:
        with TestClient(app) as client:
            chat = client.post(
                "/api/v1/chat/stream",
                json={"prompt": "Build a FastAPI service"},
            )
            project_id = next(
                __import__("json").loads(line.removeprefix("data: "))["project_id"]
                for line in chat.text.splitlines()
                if line.startswith('data: {"provider"')
            )
            staged = client.post(
                f"/api/v1/projects/{project_id}/generations",
                json={"name": "inventory-api"},
            )
            generation_id = staged.json()["id"]
            approved = client.post(
                f"/api/v1/projects/{project_id}/generations/{generation_id}/approve"
            )
            duplicate = client.post(
                f"/api/v1/projects/{project_id}/generations/{generation_id}/approve"
            )
    finally:
        app.dependency_overrides.pop(get_generation_runtime, None)

    assert staged.status_code == 201
    assert staged.json()["status"] == "staged"
    assert staged.json()["output_path"] is None
    assert [item["path"] for item in staged.json()["manifest"]["files"]] == [
        "README.md",
        "app/main.py",
    ]
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    output = Path(approved.json()["output_path"])
    assert output.joinpath("README.md").read_text() == "# Generated app\n"
    assert duplicate.status_code == 409


def test_generation_rejects_unsafe_model_paths() -> None:
    from app.schemas.generation import GeneratedFile, GenerationManifest
    from app.services.generation import GenerationError, validate_manifest

    manifest = GenerationManifest(
        summary="unsafe",
        files=[GeneratedFile(path="../escape.txt", content="no")],
    )

    try:
        validate_manifest(manifest)
    except GenerationError as exc:
        assert "Unsafe generated path" in str(exc)
    else:
        raise AssertionError("Unsafe path was accepted")
