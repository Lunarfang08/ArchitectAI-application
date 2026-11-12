from fastapi.testclient import TestClient

from app.api.dependencies import get_agent_runtime, get_model_provider
from app.main import app
from tests.fakes import FakeAgentRuntime, FakeModelProvider

app.dependency_overrides[get_model_provider] = FakeModelProvider
app.dependency_overrides[get_agent_runtime] = FakeAgentRuntime


def test_health_reports_local_defaults() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["services"]["model_provider"]["status"] == "ok"
    assert body["services"]["azure"]["status"] == "disabled"


def test_root_links_to_docs_and_health() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json()["health"] == "/api/v1/health"

