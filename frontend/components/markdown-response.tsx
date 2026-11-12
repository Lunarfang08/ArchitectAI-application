"use client";

import {
  Children,
  ComponentPropsWithoutRef,
  ReactElement,
  ReactNode,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";

export function normalizeMarkdown(content: string) {
  const withoutOpeningWrapper = content.replace(/^\s*```(?:markdown|md)\s*\n/i, "");
  const fenceCount = (withoutOpeningWrapper.match(/```/g) ?? []).length;
  if (fenceCount % 2 === 1 && /\n```\s*$/.test(withoutOpeningWrapper)) {
    return withoutOpeningWrapper.replace(/\n```\s*$/, "");
  }
  return withoutOpeningWrapper;
}

function CodeBlock({ children }: ComponentPropsWithoutRef<"pre">) {
  const [copied, setCopied] = useState(false);
  const child = Children.only(children) as ReactElement<{
    className?: string;
    children?: ReactNode;
  }>;
  const code = String(child.props.children ?? "").replace(/\n$/, "");
  const language = child.props.className?.replace("language-", "") || "text";

  async function copy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="codeBlock">
      <div className="codeToolbar">
        <span>{language}</span>
        <button type="button" onClick={copy} aria-label="Copy code">
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre>{children}</pre>
    </div>
  );
}

export function MarkdownResponse({ content }: { content: string }) {
  return (
    <div className="markdownBody">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={{
          pre: CodeBlock,
          a: ({ children, ...props }) => (
            <a {...props} target="_blank" rel="noreferrer noopener">
              {children}
            </a>
          ),
        }}
      >
        {normalizeMarkdown(content)}
      </ReactMarkdown>
    </div>
  );
}
