import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress


async def with_heartbeats(
    source: AsyncIterator[str],
    interval: float = 15,
) -> AsyncIterator[str | None]:
    """Keep an SSE connection alive without cancelling a slow model's next token."""
    pending: asyncio.Task[str] | None = None
    try:
        while True:
            if pending is None:
                pending = asyncio.create_task(anext(source))
            done, _ = await asyncio.wait({pending}, timeout=interval)
            if not done:
                yield None
                continue
            try:
                token = pending.result()
            except StopAsyncIteration:
                return
            pending = None
            yield token
    finally:
        if pending is not None:
            pending.cancel()
            with suppress(asyncio.CancelledError, StopAsyncIteration):
                await pending
        close = getattr(source, "aclose", None)
        if close is not None:
            await close()
