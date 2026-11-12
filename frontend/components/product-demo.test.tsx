import "@testing-library/jest-dom/vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ProductDemo } from "./product-demo";

afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); });
it("advances when visible, pauses after stage selection, and replays deterministically", () => {
  vi.useFakeTimers();
  vi.stubGlobal("IntersectionObserver", class { constructor(private callback: (entries: {isIntersecting: boolean}[]) => void) {} observe() { this.callback([{ isIntersecting: true }]); } disconnect() {} });
  render(<ProductDemo />);
  act(() => vi.advanceTimersByTime(3500));
  expect(screen.getByRole("heading", { name: "A clear direction from your brief." })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Show Discover" }));
  act(() => vi.advanceTimersByTime(20000));
  expect(screen.getByRole("heading", { name: "Find the first domino." })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Replay" }));
  expect(screen.getByRole("heading", { name: "Every system starts with a question." })).toBeInTheDocument();
});
