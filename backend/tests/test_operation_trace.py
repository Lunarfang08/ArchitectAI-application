import json

from app.api.operation import OperationTrace


def test_operation_trace_emits_stable_sse_contract() -> None:
    trace = OperationTrace("generation")
    raw = trace.event(
        "step",
        "validate",
        "active",
        "Validating generated files",
        detail="3 paths checked",
    )

    event_line, data_line = raw.strip().splitlines()
    payload = json.loads(data_line.removeprefix("data: "))

    assert event_line == "event: step"
    assert payload["operation_id"] == trace.id
    assert payload["phase"] == "generation"
    assert payload["step"] == "validate"
    assert payload["status"] == "active"
    assert payload["detail"] == "3 paths checked"
    assert payload["elapsed_ms"] >= 0


def test_operation_trace_includes_completed_result() -> None:
    trace = OperationTrace("review")
    raw = trace.event(
        "completed",
        "ready",
        "complete",
        "Review ready",
        result={"id": "review-1"},
    )

    payload = json.loads(raw.split("data: ", 1)[1])
    assert payload["result"] == {"id": "review-1"}
