import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { FutureLab } from "./future-lab";
import * as api from "../lib/api";

vi.mock("../lib/api", () => ({ getSimulations: vi.fn().mockResolvedValue([]), runSimulation: vi.fn(), deleteSimulation: vi.fn() }));
afterEach(cleanup);
it("locks simulation before architecture completion", () => {
  render(<FutureLab projectId={null} ready={false} onEvent={vi.fn()} cancelRef={{ current: null }} />);
  expect(screen.getByRole("button", { name: /Run simulation/ })).toBeDisabled();
});
it("validates custom input and reports a failed request", async () => {
  vi.mocked(api.runSimulation).mockRejectedValue(new Error("Model unavailable"));
  render(<FutureLab projectId="project" ready onEvent={vi.fn()} cancelRef={{ current: null }} />);
  fireEvent.click(screen.getByRole("checkbox"));
  expect(screen.getByRole("button", { name: /Run simulation/ })).toBeDisabled();
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "The database is unavailable for one hour" } });
  fireEvent.click(screen.getByRole("button", { name: /Run simulation/ }));
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Model unavailable"));
  expect(api.runSimulation).toHaveBeenCalledWith("project", "custom", "The database is unavailable for one hour", expect.any(AbortSignal), expect.any(Function));
});
