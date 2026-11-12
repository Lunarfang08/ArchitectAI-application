import asyncio
from uuid import uuid4

import pytest

from app.api.routes.models import active_streams, cancel_stream


async def test_cancel_endpoint_interrupts_pending_generation() -> None:
    request_id = uuid4()
    stopped = asyncio.Event()

    async def generation():
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    task = asyncio.create_task(generation())
    await asyncio.sleep(0)
    active_streams[str(request_id)] = task
    try:
        assert await cancel_stream(request_id) == {"cancelled": True}
        with pytest.raises(asyncio.CancelledError):
            await task
        assert stopped.is_set()
    finally:
        active_streams.pop(str(request_id), None)
