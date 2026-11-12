from fastapi.testclient import TestClient

from app.api.dependencies import get_agent_runtime, get_model_provider
from app.main import app
from tests.fakes import FakeAgentRuntime, FakeModelProvider

app.dependency_overrides[get_model_provider] = FakeModelProvider
app.dependency_overrides[get_agent_runtime] = FakeAgentRuntime


def test_project_and_conversation_lifecycle() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/projects",
            json={"title": "Inventory platform", "description": "Local-first"},
        )
        project_id = created.json()["id"]
        conversation = client.post(
            f"/api/v1/projects/{project_id}/conversations",
            json={"title": "Initial architecture"},
        )
        listed = client.get("/api/v1/projects")
        detail = client.get(f"/api/v1/projects/{project_id}")

    assert created.status_code == 201
    assert conversation.status_code == 201
    assert conversation.json()["project_id"] == project_id
    assert listed.json()[0]["conversation_count"] == 1
    assert detail.json()["conversations"][0]["title"] == "Initial architecture"


def test_missing_workspace_resources_return_not_found() -> None:
    missing = "00000000-0000-0000-0000-000000000001"
    with TestClient(app) as client:
        project = client.get(f"/api/v1/projects/{missing}")
        conversation = client.get(f"/api/v1/conversations/{missing}/messages")

    assert project.status_code == 404
    assert conversation.status_code == 404
