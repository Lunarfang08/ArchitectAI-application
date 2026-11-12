import json
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from app.api.dependencies import get_agent_runtime, get_model_provider
from app.main import app
from app.services.model_provider import ModelProviderError
from tests.fakes import FakeAgentRuntime, FakeModelProvider

app.dependency_overrides[get_model_provider] = FakeModelProvider
app.dependency_overrides[get_agent_runtime] = FakeAgentRuntime


def test_lists_local_models() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/models")

    assert response.status_code == 200
    assert response.json()["models"][0]["name"] == "qwen2.5:3b"


def test_streams_chat_as_server_sent_events() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/chat/stream", json={"prompt": "Design an API"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: metadata" in response.text
    assert 'data: {"content": "Local"}' in response.text
    assert "event: done" in response.text

    metadata = next(
        line.removeprefix("data: ")
        for line in response.text.splitlines()
        if line.startswith('data: {"provider"')
    )
    assert '"project_id"' in metadata
    assert '"conversation_id"' in metadata
    assert '"message_id"' in metadata
    assert '"framework": "langgraph+autogen"' in metadata


def test_stream_reports_retrieved_local_sources() -> None:
    with TestClient(app) as client:
        uploaded = client.post(
            "/api/v1/knowledge/documents",
            files={
                "file": (
                    "payments.md",
                    b"Use the outbox pattern for reliable payment event delivery.",
                    "text/markdown",
                )
            },
        )
        response = client.post(
            "/api/v1/chat/stream",
            json={"prompt": "Design reliable payment event delivery"},
        )

    assert uploaded.status_code == 201
    metadata = next(
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith('data: {"provider"')
    )
    assert metadata["sources"] == ["payments.md"]


def test_rejects_empty_prompt() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/chat/stream", json={"prompt": ""})

    assert response.status_code == 422


def test_allows_local_development_cors_preflight() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/chat/stream",
            headers={
                "Origin": "http://127.0.0.1:3001",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3001"


def test_stream_persists_completed_messages() -> None:
    with TestClient(app) as client:
        stream = client.post("/api/v1/chat/stream", json={"prompt": "Design a local API"})
        metadata_line = next(
            line.removeprefix("data: ")
            for line in stream.text.splitlines()
            if line.startswith('data: {"provider"')
        )
        metadata = json.loads(metadata_line)
        response = client.get(
            f"/api/v1/conversations/{metadata['conversation_id']}/messages"
        )

    assert response.status_code == 200
    messages = response.json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "Local GenAI"
    assert messages[1]["status"] == "completed"


def test_unknown_conversation_returns_not_found() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/stream",
            json={
                "prompt": "Continue",
                "conversation_id": "00000000-0000-0000-0000-000000000001",
            },
        )

    assert response.status_code == 404


class FailingAgentRuntime(FakeAgentRuntime):
    async def stream(
        self,
        *,
        prompt: str,
        model: str,
        system_prompt: str,
    ) -> AsyncIterator[str]:
        del prompt, model, system_prompt
        if False:
            yield ""
        raise ModelProviderError("Expected local model failure.")


def test_failed_stream_is_persisted_as_failed() -> None:
    app.dependency_overrides[get_agent_runtime] = FailingAgentRuntime
    try:
        with TestClient(app) as client:
            stream = client.post("/api/v1/chat/stream", json={"prompt": "Design an API"})
            metadata_line = next(
                line.removeprefix("data: ")
                for line in stream.text.splitlines()
                if line.startswith('data: {"provider"')
            )
            metadata = json.loads(metadata_line)
            messages = client.get(
                f"/api/v1/conversations/{metadata['conversation_id']}/messages"
            ).json()
    finally:
        app.dependency_overrides[get_agent_runtime] = FakeAgentRuntime

    assert "event: error" in stream.text
    assert messages[1]["status"] == "failed"


def test_reports_experimental_autogen_status() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/autogen/status")

    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert response.json()["archived"] is True
    assert response.json()["code_execution_enabled"] is False


