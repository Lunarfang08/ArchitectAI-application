from collections.abc import AsyncIterator

from app.schemas.models import ModelInfo, ModelStatus


class FakeModelProvider:
    async def status(self) -> ModelStatus:
        return ModelStatus(
            available=True,
            provider="ollama",
            selected_model="qwen2.5:3b",
            detail="Using qwen2.5:3b",
        )

    async def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(name="qwen2.5:3b", size_bytes=1_900_000_000)]

    async def resolve_model(self, requested_model: str | None = None) -> str:
        return requested_model or "qwen2.5:3b"

    async def stream_chat(
        self,
        *,
        prompt: str,
        model: str,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        del prompt, model, system_prompt
        for token in ("Local", " GenAI"):
            yield token


class FakeAgentRuntime:
    async def stream(
        self, *, prompt: str, model: str, system_prompt: str
    ) -> AsyncIterator[str]:
        del prompt, model, system_prompt
        for token in ("Local", " GenAI"):
            yield token


class FakeGenerationRuntime:
    async def stream(
        self, *, prompt: str, model: str, system_prompt: str
    ) -> AsyncIterator[str]:
        del prompt, model, system_prompt
        yield (
            '{"summary":"FastAPI starter","files":['
            '{"path":"README.md","content":"# Generated app\\n"},'
            '{"path":"app/main.py","content":"from fastapi import FastAPI\\n\\napp = FastAPI()\\n"}'
            "]}"
        )


class FakeReviewRuntime:
    def __init__(self) -> None:
        self.calls = 0

    async def stream(
        self, *, prompt: str, model: str, system_prompt: str
    ) -> AsyncIterator[str]:
        del prompt, model, system_prompt
        self.calls += 1
        if self.calls == 1:
            yield (
                '{"summary":"One validation gap found","findings":['
                '{"severity":"medium","path":"app/main.py","issue":"No health test",'
                '"recommendation":"Add a health endpoint test"}]}'
            )
            return
        yield (
            '{"summary":"Health endpoint coverage","files":['
            '{"path":"tests/test_health.py","content":"def test_health():\\n    assert True\\n"}'
            "]}"
        )

