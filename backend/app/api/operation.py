import json
from time import monotonic
from typing import Any
from uuid import uuid4


class OperationTrace:
    def __init__(self, phase: str) -> None:
        self.id = str(uuid4())
        self.phase = phase
        self.started_at = monotonic()

    def event(
        self,
        event: str,
        step: str,
        status: str,
        message: str,
        *,
        detail: str | None = None,
        result: Any | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "operation_id": self.id,
            "phase": self.phase,
            "step": step,
            "status": status,
            "message": message,
            "elapsed_ms": round((monotonic() - self.started_at) * 1000),
        }
        if detail is not None:
            payload["detail"] = detail
        if result is not None:
            payload["result"] = result
        return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def stream_headers() -> dict[str, str]:
    return {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
