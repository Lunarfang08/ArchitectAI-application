import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MarkdownResponse } from "./markdown-response";

beforeEach(() => {
  Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
});

describe("MarkdownResponse", () => {
  it("formats GFM headings, lists, tables, and fenced code", () => {
    render(
      <MarkdownResponse
        content={"## Architecture\n\n- API\n- UI\n\n| Layer | Tool |\n| --- | --- |\n| API | FastAPI |\n\n```python\nprint('safe')\n```"}
      />,
    );

    expect(screen.getByRole("heading", { name: "Architecture" })).toBeInTheDocument();
    expect(screen.getByRole("list")).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("python")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Copy code" }));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("print('safe')");
  });

  it("does not render model-provided raw HTML", () => {
    const { container } = render(
      <MarkdownResponse content={'<script>alert("unsafe")</script><b>raw</b>'} />,
    );
    expect(container.querySelector("script")).not.toBeInTheDocument();
    expect(container.querySelector("b")).not.toBeInTheDocument();
  });

  it("unwraps an accidental whole-response markdown fence", () => {
    render(
      <MarkdownResponse
        content={'```markdown\n## Architecture\n\n- API\n\n```python\nprint("hello")\n```'}
      />,
    );
    expect(screen.getByRole("heading", { name: "Architecture" })).toBeInTheDocument();
    expect(screen.getByText("python")).toBeInTheDocument();
  });
});
