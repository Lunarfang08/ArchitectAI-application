from collections.abc import AsyncIterator

from app.services.langgraph_runtime import LangGraphRuntime


class RecordingAgentRuntime:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def stream(
        self, *, prompt: str, model: str, system_prompt: str
    ) -> AsyncIterator[str]:
        self.calls.append((prompt, system_prompt))

        async def tokens() -> AsyncIterator[str]:
            yield "final"

        return tokens()


async def test_orchestration_streams_only_one_concise_architect_call() -> None:
    agent_runtime = RecordingAgentRuntime()
    runtime = LangGraphRuntime(agent_runtime)

    result = "".join(
        [
            token
            async for token in runtime.stream(
                prompt="Design a local inventory system",
                model="local-model",
                system_prompt="Use Markdown.",
            )
        ]
    )

    assert result == "## Architecture proposal\n\nfinal"
    assert len(agent_runtime.calls) == 1
    assert "avoid repeating" in agent_runtime.calls[0][0]
    assert "Architect agent" in agent_runtime.calls[0][1]


async def test_cancellation_stops_architect_generation() -> None:
    import asyncio

    import pytest

    started = asyncio.Event()
    stopped = asyncio.Event()

    class BlockingRuntime:
        async def stream(self, **kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
                yield "unexpected"
            finally:
                stopped.set()

    runtime = LangGraphRuntime(BlockingRuntime())
    async def consume():
        async for _ in runtime.stream(prompt="test", model="test", system_prompt="test"):
            pass

    task = asyncio.create_task(consume())
    await asyncio.wait_for(started.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.wait_for(stopped.wait(), 1)
