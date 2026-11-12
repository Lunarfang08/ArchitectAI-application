"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import {
  ActiveOperation,
  ConversationSummary,
  deleteKnowledgeDocument,
  getHealth,
  getGenerationReviews,
  getKnowledgeDocuments,
  getMessages,
  getProject,
  getProjectGenerations,
  getProjects,
  HealthResponse,
  GenerationReview,
  KnowledgeDocument,
  Message,
  ProjectSummary,
  ProjectGeneration,
  OperationStep,
  streamGenerationReview,
  streamKnowledgeUpload,
  streamProjectApproval,
  streamProjectGeneration,
  streamTestApproval,
  streamChat,
  cancelChat,
} from "../lib/api";
import { ActivityTrace } from "./activity-trace";
import { ArchitectLogo } from "./architect-logo";
import { MarkdownResponse } from "./markdown-response";
import { FutureLab } from "./future-lab";

const starterPrompt =
  "Design a secure inventory platform with a Next.js dashboard, FastAPI backend, and event-driven stock updates.";

function shortDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(
    new Date(value),
  );
}

export function ArchitectDashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState("");
  const [model, setModel] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [conversation, setConversation] = useState<ConversationSummary | null>(null);
  const [architectureReady, setArchitectureReady] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [knowledgeBusy, setKnowledgeBusy] = useState(false);
  const [sources, setSources] = useState<string[]>([]);
  const [generation, setGeneration] = useState<ProjectGeneration | null>(null);
  const [generationBusy, setGenerationBusy] = useState(false);
  const [review, setReview] = useState<GenerationReview | null>(null);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [activeOperation, setActiveOperation] = useState<ActiveOperation | null>(null);
  const [selectedView, setSelectedView] = useState<"architecture" | "knowledge" | "generation" | "review" | "future">("architecture");
  const controller = useRef<AbortController | null>(null);
  const activeRequestId = useRef<string | null>(null);
  const operationController = useRef<AbortController | null>(null);
  const responseRef = useRef<HTMLDivElement | null>(null);
  const autoScroll = useRef(true);
  const futureCancel = useRef<(() => void) | null>(null);

  function recordOperation(event: OperationStep) {
    setActiveOperation((current) => {
      if (current && current.id !== event.operation_id && current.status === "active") return current;
      return {
        id: event.operation_id,
        phase: event.phase,
        status: event.status,
        startedAt: current?.startedAt ?? Date.now() - event.elapsed_ms,
        steps: [...(current?.steps ?? []), event],
      };
    });
  }

  function cancelOperation() {
    if (activeOperation?.phase === "future") { futureCancel.current?.(); return; }
    operationController.current?.abort();
    operationController.current = null;
    setActiveOperation((current) => current ? { ...current, status: "cancelled" } : current);
    setGenerationBusy(false);
    setReviewBusy(false);
    setKnowledgeBusy(false);
  }

  async function refreshProjects() {
    setProjects(await getProjects());
  }

  useEffect(() => {
    Promise.all([getHealth(), getProjects(), getKnowledgeDocuments()])
      .then(([healthResult, projectResult, documentResult]) => {
        setHealth(healthResult);
        setProjects(projectResult);
        setDocuments(documentResult);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  useEffect(() => {
    const node = responseRef.current;
    if (node && autoScroll.current) node.scrollTop = node.scrollHeight;
  }, [answer, messages]);

  async function openProject(id: string) {
    setLoadingHistory(true);
    setError(null);
    try {
      const detail = await getProject(id);
      setProjectId(detail.id);
      const latest = detail.conversations[0] ?? null;
      setConversation(latest);
      const [savedMessages, generations] = await Promise.all([
        latest ? getMessages(latest.id) : Promise.resolve([]),
        getProjectGenerations(detail.id),
      ]);
      setMessages(savedMessages);
      setArchitectureReady(
        savedMessages.some(
          (message) => message.role === "assistant" && message.status === "completed",
        ),
      );
      setGeneration(generations[0] ?? null);
      setReview(
        generations[0]
          ? (await getGenerationReviews(detail.id, generations[0].id))[0] ?? null
          : null,
      );
      setAnswer("");
      setModel(latest?.model ?? null);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setLoadingHistory(false);
    }
  }

  function newWorkspace() {
    setProjectId(null);
    setConversation(null);
    setArchitectureReady(false);
    setMessages([]);
    setAnswer("");
    setPrompt("");
    setError(null);
    setSources([]);
    setGeneration(null);
    setReview(null);
  }

  async function stageGeneration() {
    if (!projectId || !architectureReady || generationBusy) return;
    setGenerationBusy(true);
    setSelectedView("generation");
    setError(null);
    const requestController = new AbortController();
    operationController.current = requestController;
    try {
      setGeneration(await streamProjectGeneration(projectId, requestController.signal, recordOperation));
      setReview(null);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      if (operationController.current === requestController) operationController.current = null;
      setGenerationBusy(false);
    }
  }

  async function approveGeneration() {
    if (!projectId || !generation || generation.status !== "staged" || generationBusy) return;
    setGenerationBusy(true);
    setError(null);
    const requestController = new AbortController();
    operationController.current = requestController;
    try {
      setGeneration(await streamProjectApproval(projectId, generation.id, requestController.signal, recordOperation));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      if (operationController.current === requestController) operationController.current = null;
      setGenerationBusy(false);
    }
  }

  async function stageReview() {
    if (!projectId || !generation || reviewBusy) return;
    setReviewBusy(true);
    setSelectedView("review");
    setError(null);
    const requestController = new AbortController();
    operationController.current = requestController;
    try {
      setReview(await streamGenerationReview(projectId, generation.id, requestController.signal, recordOperation));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      if (operationController.current === requestController) operationController.current = null;
      setReviewBusy(false);
    }
  }

  async function approveTests() {
    if (!projectId || !generation || !review || review.status !== "staged" || reviewBusy) return;
    setReviewBusy(true);
    setError(null);
    const requestController = new AbortController();
    operationController.current = requestController;
    try {
      setReview(await streamTestApproval(projectId, generation.id, review.id, requestController.signal, recordOperation));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      if (operationController.current === requestController) operationController.current = null;
      setReviewBusy(false);
    }
  }

  async function uploadDocument(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || knowledgeBusy) return;
    setKnowledgeBusy(true);
    setSelectedView("knowledge");
    setError(null);
    const requestController = new AbortController();
    operationController.current = requestController;
    try {
      const document = await streamKnowledgeUpload(file, requestController.signal, recordOperation);
      setDocuments((current) => [document, ...current.filter((item) => item.id !== document.id)]);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      if (operationController.current === requestController) operationController.current = null;
      setKnowledgeBusy(false);
    }
  }

  async function removeDocument(id: string) {
    setKnowledgeBusy(true);
    setError(null);
    try {
      await deleteKnowledgeDocument(id);
      setDocuments((current) => current.filter((document) => document.id !== id));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setKnowledgeBusy(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const requirement = prompt.trim();
    if (!requirement || streaming) return;
    setAnswer("");
    setSources([]);
    setGeneration(null);
    setReview(null);
    setArchitectureReady(false);
    setError(null);
    setStreaming(true);
    autoScroll.current = true;
    const requestController = new AbortController();
    controller.current = requestController;
    const requestId = crypto.randomUUID();
    activeRequestId.current = requestId;
    setActiveOperation({
      id: requestId,
      phase: "architecture",
      status: "active",
      startedAt: Date.now(),
      steps: [{
        operation_id: requestId,
        phase: "architecture",
        step: "prepare",
        status: "active",
        message: "Preparing architecture context",
        elapsed_ms: 0,
        event: "started",
      }],
    });
    try {
      await streamChat(
        requirement,
        conversation?.id ?? null,
        {
          onMetadata: (metadata) => {
            if (controller.current !== requestController || requestController.signal.aborted) return;
            recordOperation({
              operation_id: requestId,
              phase: "architecture",
              step: "model",
              status: "active",
              message: `Streaming architecture with ${metadata.model}`,
              elapsed_ms: Date.now() - (activeOperation?.startedAt ?? Date.now()),
              detail: metadata.framework,
              event: "step",
            });
            setModel(metadata.model);
            setProjectId(metadata.project_id);
            setSources(metadata.sources ?? []);
            setConversation((current) => ({
              id: metadata.conversation_id,
              project_id: metadata.project_id,
              title: current?.title ?? requirement.split("\n")[0].slice(0, 160),
              model: metadata.model,
              created_at: current?.created_at ?? new Date().toISOString(),
              updated_at: new Date().toISOString(),
            }));
          },
          onToken: (token) => {
            if (controller.current === requestController && !requestController.signal.aborted) {
              setAnswer((current) => current + token);
            }
          },
          onDone: () => {
            setArchitectureReady(true);
            recordOperation({
              operation_id: requestId,
              phase: "architecture",
              step: "ready",
              status: "complete",
              message: "Architecture completed and saved locally",
              elapsed_ms: 0,
              event: "completed",
            });
          },
          onError: (message) => {
            if (controller.current === requestController && !requestController.signal.aborted) {
              setArchitectureReady(false);
              setError(message);
              recordOperation({ operation_id: requestId, phase: "architecture", step: "failed", status: "failed", message, elapsed_ms: 0, event: "failed" });
            }
          },
          onCancelled: () => {
            if (controller.current === requestController) {
              setArchitectureReady(false);
              setError("Generation cancelled.");
            }
          },
        },
        requestController.signal,
        requestId,
      );
      if (requestController.signal.aborted || controller.current !== requestController) return;
      setPrompt("");
      await refreshProjects();
    } catch (reason) {
      if (!requestController.signal.aborted && controller.current === requestController) setError((reason as Error).message);
    } finally {
      if (controller.current === requestController) {
        setStreaming(false);
        controller.current = null;
        activeRequestId.current = null;
      }
    }
  }

  function stopStreaming() {
    const activeController = controller.current;
    if (!activeController) return;
    controller.current = null;
    const requestId = activeRequestId.current;
    activeRequestId.current = null;
    setStreaming(false);
    setArchitectureReady(false);
    setError("Generation cancelled.");
    setActiveOperation((current) => current ? {
      ...current,
      status: "cancelled",
      steps: [...current.steps, {
        operation_id: current.id,
        phase: current.phase,
        step: "cancelled",
        status: "cancelled",
        message: "Architecture generation cancelled",
        elapsed_ms: Date.now() - current.startedAt,
        event: "cancelled",
      }],
    } : current);
    activeController.abort();
    if (requestId) void cancelChat(requestId).catch(() => setError("Stopped locally; server cancellation could not be confirmed."));
  }

  const modelState = health?.services.model_provider;

  return (
    <main className="appShell">
      <aside className="sidebar">
        <div className="brand"><ArchitectLogo className="brandMark" /><span>ArchitectAI</span></div>
        <button className="newWorkspace" type="button" onClick={newWorkspace}>+ New workspace</button>
        <section className="recentProjects" aria-label="Recent projects">
          <p className="navLabel">RECENT PROJECTS</p>
          {projects.length === 0 ? <small>No saved projects yet</small> : projects.map((project) => (
            <button
              type="button"
              className={project.id === projectId ? "selected" : ""}
              onClick={() => openProject(project.id)}
              key={project.id}
            >
              <span>{project.title}</span>
              <small>{project.conversation_count} chat{project.conversation_count === 1 ? "" : "s"} · {shortDate(project.updated_at)}</small>
            </button>
          ))}
        </section>
        <div className="localBadge"><span className="pulse" /> Local data · cloud optional</div>
      </aside>

      <section className="content" id="architect-dashboard">
        <header className="topbar">
          <div><p className="eyebrow">ARCHITECTURE STUDIO</p><h1>Draw the system<br /><em>before you build it.</em></h1></div>
          <div className={`modelPill ${health?.status ?? "loading"}`}>
            <span className="pulse" />
            <div><small>MODEL</small><strong>{model ?? modelState?.detail?.replace("Using ", "") ?? "Checking…"}</strong></div>
          </div>
        </header>

        <nav className="workspaceTabs" aria-label="Workspace sections">
          {([
            ["architecture", "Architecture", architectureReady, streaming],
            ["knowledge", "Knowledge", documents.length > 0, knowledgeBusy],
            ["generation", "Build", Boolean(generation), generationBusy],
            ["review", "Review", Boolean(review), reviewBusy],
            ["future", "Future Lab", activeOperation?.phase === "future" && activeOperation.status === "complete", activeOperation?.phase === "future" && activeOperation.status === "active"],
          ] as const).map(([id, label, complete, active]) => (
            <button
              type="button"
              className={`${selectedView === id ? "selected" : ""} ${active ? "active" : complete ? "complete" : "ready"}`}
              onClick={() => setSelectedView(id)}
              key={id}
            >
              <strong>{label}</strong>
            </button>
          ))}
        </nav>

        <ActivityTrace operation={activeOperation} onCancel={activeOperation?.phase === "architecture" ? stopStreaming : cancelOperation} />

        {selectedView === "architecture" && <section className="workspace workspacePanel">
          <div className="workspaceIntro">
            <div><span className="eyebrow">PROJECT BRIEF</span><h2>{conversation?.title ?? "What are we making?"}</h2></div>
            {conversation && <span className="savedBadge">Saved locally</span>}
          </div>

          {(messages.length > 0 || answer || error || loadingHistory || streaming) && (
            <div
              className="transcript"
              ref={responseRef}
              onScroll={(event) => {
                const node = event.currentTarget;
                autoScroll.current = node.scrollHeight - node.scrollTop - node.clientHeight < 80;
              }}
            >
              {loadingHistory && <p className="emptyState">Loading saved conversation…</p>}
              {messages.map((message) => (
                <article className={`message ${message.role}`} key={message.id}>
                  <div className="messageMeta"><span>{message.role === "user" ? "YOU" : "ARCHITECTAI"}</span><small>{message.status}</small></div>
                  {message.role === "assistant" ? <MarkdownResponse content={message.content} /> : <p>{message.content}</p>}
                </article>
              ))}
              {(answer || streaming) && (
                <article className="message assistant live">
                  <div className="messageMeta"><span>ARCHITECTAI</span><small>{streaming ? "Generating" : "completed"}</small></div>
                  <MarkdownResponse content={answer || "Thinking…"} />
                  {streaming && <span className="cursor" aria-hidden="true" />}
                </article>
              )}
              {sources.length > 0 && (
                <p className="sourceLine">Local sources: {sources.join(", ")}</p>
              )}
              {error && <div className="errorBanner" role="alert">{error}</div>}
            </div>
          )}

          <form className="composer" onSubmit={submit}>
            <label htmlFor="requirement">Project requirement</label>
            <textarea
              id="requirement"
              placeholder={starterPrompt}
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              disabled={streaming}
              onKeyDown={(event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === "Enter") event.currentTarget.form?.requestSubmit();
              }}
            />
            <div className="composerActions">
              <span>{streaming ? `Generating with ${model}` : "⌘/Ctrl + Enter to send"}</span>
              {streaming ? (
                <button type="button" className="stop" onClick={stopStreaming}>Stop</button>
              ) : (
                <button type="submit" disabled={!prompt.trim()}>Generate architecture <span>→</span></button>
              )}
            </div>
          </form>
        </section>}

        {selectedView === "generation" && <section className="generationPanel workspacePanel" id="project-generation">
          <div className="generationHeader">
            <div>
              <p className="eyebrow">PROJECT GENERATION</p>
              <h2>Generated project</h2>
              <p>A project generator prepares a validated file list. Review every file before approving the local write.</p>
            </div>
            {!generation && (
              <button type="button" onClick={stageGeneration} disabled={!projectId || !architectureReady || streaming || generationBusy}>
                {generationBusy ? "Generating manifest…" : "Stage project files"}
              </button>
            )}
          </div>
          {!projectId && <p className="generationEmpty">Generate an architecture first.</p>}
          {projectId && !architectureReady && <p className="generationEmpty">Complete an architecture response before staging files.</p>}
          {generation && (
            <div className="manifestPreview">
              <div className="manifestSummary">
                <div><strong>{generation.manifest.summary}</strong><small>{generation.manifest.files.length} proposed files · {generation.status}</small></div>
                {generation.status === "staged" ? (
                  <button type="button" onClick={approveGeneration} disabled={generationBusy}>
                    {generationBusy ? "Writing…" : "Approve and write files"}
                  </button>
                ) : <span className="approvedBadge">Written locally</span>}
              </div>
              {generation.manifest.files.map((file) => (
                <details key={file.path}>
                  <summary>{file.path}</summary>
                  <pre>{file.content}</pre>
                </details>
              ))}
              {generation.output_path && <p className="outputPath">Output: <code>{generation.output_path}</code></p>}
            </div>
          )}
        </section>}

        {selectedView === "review" && <section className="reviewPanel workspacePanel" id="code-review">
          <div className="generationHeader">
            <div>
              <p className="eyebrow">CODE REVIEW & TEST DESIGN</p>
              <h2>Code review</h2>
              <p>Review the staged source and proposed tests without running the project.</p>
            </div>
            {!review && (
              <button type="button" onClick={stageReview} disabled={!generation || reviewBusy}>
                {reviewBusy ? "Reviewing…" : "Run code review"}
              </button>
            )}
          </div>
          {!generation && <p className="generationEmpty">Stage a generated project first.</p>}
          {review && (
            <div className="reviewBody">
              <div className="reviewSummary">
                <div><strong>{review.report.summary}</strong><small>{review.report.findings.length} findings · {review.test_manifest.files.length} test files</small></div>
                {review.status === "staged" ? (
                  <button type="button" onClick={approveTests} disabled={generation?.status !== "approved" || reviewBusy}>
                    {reviewBusy ? "Writing tests…" : generation?.status === "approved" ? "Approve test files" : "Approve project first"}
                  </button>
                ) : <span className="approvedBadge">Tests written</span>}
              </div>
              <div className="findingList">
                {review.report.findings.length === 0 ? <p>No findings reported.</p> : review.report.findings.map((finding, index) => (
                  <article key={`${finding.path ?? "project"}-${index}`}>
                    <span className={`severity ${finding.severity}`}>{finding.severity}</span>
                    <div><strong>{finding.path ?? "Project-wide"}: {finding.issue}</strong><p>{finding.recommendation}</p></div>
                  </article>
                ))}
              </div>
              {review.test_manifest.files.map((file) => (
                <details className="testPreview" key={file.path}><summary>{file.path}</summary><pre>{file.content}</pre></details>
              ))}
            </div>
          )}
        </section>}

        {selectedView === "knowledge" && <section className="knowledgePanel workspacePanel" id="knowledge-base">
          <div>
            <p className="eyebrow">PROJECT KNOWLEDGE</p>
            <h2>Knowledge Base</h2>
            <p>Upload UTF-8 text, Markdown, JSON, YAML, or CSV. Relevant passages are added to your project context.</p>
          </div>
          <label className={`uploadButton ${knowledgeBusy ? "disabled" : ""}`}>
            {knowledgeBusy ? "Indexing…" : "+ Add document"}
            <input type="file" accept=".txt,.md,.markdown,.json,.yaml,.yml,.csv" onChange={uploadDocument} disabled={knowledgeBusy} />
          </label>
          <div className="documentList">
            {documents.length === 0 ? <p>No indexed documents yet.</p> : documents.map((document) => (
              <article key={document.id}>
                <div><strong>{document.filename}</strong><small>{document.chunk_count} chunks · {document.character_count.toLocaleString()} characters</small></div>
                <button type="button" disabled={knowledgeBusy} onClick={() => removeDocument(document.id)}>Remove</button>
              </article>
            ))}
          </div>
        </section>}

        <div hidden={selectedView !== "future"}><FutureLab key={projectId ?? "new"} projectId={projectId} ready={architectureReady} onEvent={recordOperation} cancelRef={futureCancel} onOpenArchitecture={() => setSelectedView("architecture")} /></div>
        <footer className="commandFooter">
          <span><i className={`healthDot ${health?.status ?? "loading"}`} />{health?.status === "ok" ? "Systems nominal" : "Service check required"}</span>
          <span>{projects.length} saved project{projects.length === 1 ? "" : "s"}</span>
          <span>{health?.status === "ok" ? "Workspace connected" : "Check workspace connection"}</span>
        </footer>
      </section>
    </main>
  );
}
