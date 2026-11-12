import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ActivityTrace } from "./activity-trace";

describe("ActivityTrace", () => {
  it("shows readable progress and expandable technical detail", () => {
    const cancel = vi.fn();
    render(
      <ActivityTrace
        operation={{
          id: "op-1",
          phase: "generation",
          status: "active",
          startedAt: Date.now(),
          steps: [{
            operation_id: "op-1",
            phase: "generation",
            step: "model",
            status: "active",
            message: "Generating the project blueprint",
            elapsed_ms: 120,
            detail: "40 streamed chunks received",
            event: "detail",
          }],
        }}
        onCancel={cancel}
      />,
    );

    expect(screen.getByText("Generating the project blueprint")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Technical trace"));
    expect(screen.getByText("40 streamed chunks received")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel operation" }));
    expect(cancel).toHaveBeenCalledOnce();
  });
});
