import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Home from "./page";

beforeEach(() => {
  vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({
    matches: true,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
  vi.stubGlobal("ResizeObserver", class {
    observe() {}
    unobserve() {}
    disconnect() {}
  });
});

describe("ArchitectAI home", () => {
  it("introduces the product and links to the workspace", () => {
    render(<Home />);

    expect(screen.getByRole("heading", { name: /Don't just prompt/i })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /workspace|architecting|ArchitectAI/i }).some((link) => link.getAttribute("href") === "/workspace")).toBe(true);
    expect(screen.getByText("Architecture with context.")).toBeInTheDocument();
    expect(screen.getByText("Your machine.")).toBeInTheDocument();
  });
});

