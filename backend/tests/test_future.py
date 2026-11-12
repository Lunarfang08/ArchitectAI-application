import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.dependencies import get_agent_runtime, get_generation_runtime, get_model_provider
from app.main import app
from app.schemas.future import SimulationCreate, SimulationResult
from tests.fakes import FakeAgentRuntime, FakeModelProvider

RESULT = {
    "summary": "The API waits for its database.",
    "confidence": "medium",
    "survival_score": 55,
    "scores": dict.fromkeys(
        ["security", "scalability", "reliability", "cost", "maintainability"], 55
    ),
    "components": [{"id": "api", "name": "API", "cause": "No fallback", "mitigation": "Queue"}],
    "timeline": [
        {
            "time": "5 seconds",
            "component_id": "api",
            "state": "failed",
            "description": "Requests fail",
        }
    ],
    "repairs": [
        {
            "priority": "high",
            "title": "Queue",
            "change": "Add durable queue",
            "expected_improvement": "Fewer lost requests",
        }
    ],
}


def test_validation():
    SimulationResult.model_validate(RESULT)
    with pytest.raises(ValidationError):
        SimulationResult.model_validate({**RESULT, "survival_score": 101})
    with pytest.raises(ValidationError):
        SimulationCreate(scenario_type="unknown")
    with pytest.raises(ValidationError):
        SimulationCreate(scenario_type="custom", scenario_input="bad\x00text")


def test_saved_simulation_lifecycle_and_failure_cleanup():
    class Runtime:
        invalid = False

        async def stream(self, **kwargs):
            yield "invalid" if self.invalid else json.dumps(RESULT)

    runtime = Runtime()
    overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_model_provider] = FakeModelProvider
    app.dependency_overrides[get_agent_runtime] = FakeAgentRuntime
    app.dependency_overrides[get_generation_runtime] = lambda: runtime
    try:
        with TestClient(app) as client:
            chat = client.post("/api/v1/chat/stream", json={"prompt": "Build an inventory service"})
            project = next(
                json.loads(line[6:])["project_id"]
                for line in chat.text.splitlines()
                if line.startswith('data: {"provider"')
            )
            base = f"/api/v1/projects/{project}/simulations"
            response = client.post(base + "/stream", json={"scenario_type": "database"})
            assert "event: completed" in response.text
            rows = client.get(base).json()
            assert len(rows) == 1
            assert rows[0]["result"]["survival_score"] == 55
            assert client.get(base + "/" + rows[0]["id"]).status_code == 200
            runtime.invalid = True
            assert (
                "event: failed"
                in client.post(base + "/stream", json={"scenario_type": "traffic"}).text
            )
            assert len(client.get(base).json()) == 1
            assert (
                client.post(
                    base + "/stream", json={"scenario_type": "custom", "scenario_input": "short"}
                ).status_code
                == 422
            )
            assert client.delete(base + "/" + rows[0]["id"]).status_code == 204
            assert client.get(base).json() == []
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
