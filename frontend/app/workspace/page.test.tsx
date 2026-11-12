import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import WorkspacePage from "./page";

const health = {
  status: "ok",
  environment: "test",
  services: {
    api: { status: "ok", detail: null },
    model_provider: { status: "ok", detail: "Using qwen2.5-coder:7b" },
    azure: { status: "disabled", detail: null },
    autogen: { status: "configured", detail: "Active agent runtime" },
  },
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn((url: string) => Promise.resolve({
    ok: true,
    json: () => Promise.resolve(url.endsWith("/health") ? health : []),
  })));
});

describe("architect workspace", () => {
  it("shows progress immediately and stops a pending stream", async () => {
    let cancelled = false;
    const defaultFetch = globalThis.fetch;
    vi.stubGlobal("fetch", vi.fn((url: string, init?: RequestInit) => {
      if (url.endsWith("/chat/stream")) {
        return Promise.resolve({ ok: true, body: new ReadableStream({ cancel() { cancelled = true; } }) });
      }
      if (url.endsWith("/cancel")) return Promise.resolve({ ok: true });
      return defaultFetch(url, init);
    }));
    render(<WorkspacePage />);
    fireEvent.change(screen.getByLabelText("Project requirement"), { target: { value: "Design an API" } });
    fireEvent.click(screen.getByRole("button", { name: /Generate architecture/ }));
    expect(await screen.findByText("Thinking…")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Stop" }));
    expect(screen.getByRole("button", { name: /Generate architecture/ })).toBeInTheDocument();
    await waitFor(() => expect(cancelled).toBe(true));
    expect(screen.getByLabelText("Project requirement")).toHaveValue("Design an API");
  });
  it("retains the complete engineering dashboard", async () => {
    render(<WorkspacePage />);
    expect(screen.getByRole("navigation", { name: "Workspace sections" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Architecture" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Generate architecture/ })).toBeDisabled();
    await waitFor(() => expect(screen.getByText("Workspace connected")).toBeInTheDocument());
  });
  it("does not unlock project staging when architecture generation fails", async () => {
    const encoder = new TextEncoder();
    const defaultFetch = globalThis.fetch;
    vi.stubGlobal("fetch", vi.fn((url: string, init?: RequestInit) => {
      if (url.endsWith("/chat/stream")) {
        const events = [
          "event: metadata\ndata: {\"provider\":\"ollama\",\"model\":\"test\",\"framework\":\"direct\",\"project_id\":\"project-1\",\"conversation_id\":\"conversation-1\",\"message_id\":\"message-1\",\"sources\":[]}\n\n",
          "event: error\ndata: {\"message\":\"Model generation failed\"}\n\n",
        ];
        return Promise.resolve({
          ok: true,
          body: new ReadableStream({
            start(controller) {
              events.forEach((event) => controller.enqueue(encoder.encode(event)));
              controller.close();
            },
          }),
        });
      }
      return defaultFetch(url, init);
    }));

    render(<WorkspacePage />);
    fireEvent.change(screen.getByLabelText("Project requirement"), { target: { value: "Design an API" } });
    fireEvent.click(screen.getByRole("button", { name: /Generate architecture/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Model generation failed");
    fireEvent.click(screen.getByRole("button", { name: /Build/ }));
    expect(screen.getByRole("button", { name: "Stage project files" })).toBeDisabled();
    expect(screen.getByText("Complete an architecture response before staging files.")).toBeInTheDocument();
  });
});
