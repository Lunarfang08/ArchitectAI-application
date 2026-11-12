import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_agent_runtime,
    get_generation_runtime,
    get_model_provider,
    get_review_runtime,
)
from app.main import app
from tests.fakes import (
    FakeAgentRuntime,
    FakeGenerationRuntime,
    FakeModelProvider,
    FakeReviewRuntime,
)


def test_review_and_test_generation_require_separate_approval() -> None:
    app.dependency_overrides[get_model_provider] = FakeModelProvider
    app.dependency_overrides[get_agent_runtime] = FakeAgentRuntime
    app.dependency_overrides[get_generation_runtime] = FakeGenerationRuntime
    app.dependency_overrides[get_review_runtime] = FakeReviewRuntime
    try:
        with TestClient(app) as client:
            chat = client.post("/api/v1/chat/stream", json={"prompt": "Build an API"})
            project_id = next(
                json.loads(line.removeprefix("data: "))["project_id"]
                for line in chat.text.splitlines()
                if line.startswith('data: {"provider"')
            )
            generation = client.post(
                f"/api/v1/projects/{project_id}/generations", json={"name": "reviewed-api"}
            ).json()
            generation_id = generation["id"]
            approved_generation = client.post(
                f"/api/v1/projects/{project_id}/generations/{generation_id}/approve"
            ).json()
            staged = client.post(
                f"/api/v1/projects/{project_id}/generations/{generation_id}/reviews"
            )
            review_id = staged.json()["id"]
            approved = client.post(
                f"/api/v1/projects/{project_id}/generations/{generation_id}/reviews/"
                f"{review_id}/approve"
            )
    finally:
        app.dependency_overrides.pop(get_review_runtime, None)
        app.dependency_overrides.pop(get_generation_runtime, None)

    assert staged.status_code == 201
    assert staged.json()["status"] == "staged"
    assert staged.json()["report"]["findings"][0]["severity"] == "medium"
    assert staged.json()["test_manifest"]["files"][0]["path"] == "tests/test_health.py"
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    output = Path(approved_generation["output_path"])
    assert output.joinpath("tests/test_health.py").is_file()
