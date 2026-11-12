"use client";

import { useEffect, useState } from "react";
import type { ActiveOperation } from "../lib/api";

export function ActivityTrace({
  operation,
  onCancel,
}: {
  operation: ActiveOperation | null;
  onCancel: () => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!operation || operation.status !== "active") return;
    const update = () => setElapsed(Date.now() - operation.startedAt);
    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, [operation]);

  if (!operation) return null;
  const latest = operation.steps.at(-1);
  const seconds = Math.max(elapsed, latest?.elapsed_ms ?? 0) / 1000;

  return (
    <aside className={`activityTrace ${operation.status}`} aria-live="polite">
      <button className="activityTop" type="button" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded}>
        <span className="activityGlyph" aria-hidden="true"><i /><i /><i /></span>
        <span className="activityTitle">
          <small>{operation.phase.replaceAll("-", " ")} · live operation</small>
          <strong>{latest?.message ?? "Preparing operation"}</strong>
        </span>
        <span className="activityTime">{seconds.toFixed(1)}s</span>
        <span className="activityToggle">{expanded ? "Hide" : "Show"}</span>
      </button>
      {expanded && (
        <div className="activityBody">
          <ol className="activitySteps">
            {operation.steps.filter((step) => step.event !== "detail").map((step, index) => (
              <li className={step.status} key={`${step.step}-${index}`}>
                <span aria-hidden="true">{step.status === "complete" ? "✓" : step.status === "failed" ? "!" : "·"}</span>
                <div><strong>{step.message}</strong><small>{(step.elapsed_ms / 1000).toFixed(1)}s</small></div>
              </li>
            ))}
          </ol>
          <details className="technicalTrace">
            <summary>Technical trace</summary>
            <div>
              {operation.steps.map((step, index) => (
                <p key={`${step.event}-${index}`}><time>+{step.elapsed_ms}ms</time><span>{step.event}</span>{step.detail ?? step.message}</p>
              ))}
            </div>
          </details>
          {operation.status === "active" && <button className="cancelOperation" type="button" onClick={onCancel}>Cancel operation</button>}
        </div>
      )}
    </aside>
  );
}
