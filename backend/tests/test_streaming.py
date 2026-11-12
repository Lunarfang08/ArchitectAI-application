import asyncio

import pytest

from app.core.config import Settings
from app.services.streaming import with_heartbeats


async def test_slow_generation_gets_heartbeats_without_cancelling_model():
    release = asyncio.Event()

    async def source():
        await release.wait()
        yield "completed output"

    stream = with_heartbeats(source(), interval=0.001)
    assert await anext(stream) is None
    assert await anext(stream) is None
    release.set()
    assert await anext(stream) == "completed output"
    with pytest.raises(StopAsyncIteration):
        await anext(stream)


async def test_cancellation_closes_pending_model_stream():
    stopped = asyncio.Event()

    async def source():
        try:
            await asyncio.Event().wait()
            yield "unexpected"
        finally:
            stopped.set()

    stream = with_heartbeats(source(), interval=0.001)
    assert await anext(stream) is None
    await stream.aclose()
    assert stopped.is_set()


def test_default_has_no_total_deadline():
    settings = Settings(_env_file=None)
    assert settings.architecture_generation_timeout_seconds == 0
    assert settings.ollama_request_timeout_seconds == 600
