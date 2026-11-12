export type ServiceState = { status: string; detail: string | null };
export type HealthResponse = {
  status: "ok" | "degraded";
  environment: string;
  services: Record<string, ServiceState>;
};
export type ProjectSummary = {
  id: string;
  title: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
  conversation_count: number;
};
export type ConversationSummary = {
  id: string;
  project_id: string;
  title: string;
  model: string;
  created_at: string;
  updated_at: string;
};
export type ProjectDetail = ProjectSummary & { conversations: ConversationSummary[] };
export type Message = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  model: string | null;
  status: "completed" | "streaming" | "cancelled" | "failed";
  created_at: string;
  updated_at: string;
};
export type StreamMetadata = {
  model: string;
  provider: string;
  framework: "langgraph+autogen" | "langgraph+autogen+azure" | "langgraph+azure" | "autogen" | "direct";
  project_id: string;
  conversation_id: string;
  message_id: string;
  sources: string[];
};
export type KnowledgeDocument = {
  id: string;
  filename: string;
  content_type: string;
  chunk_count: number;
  character_count: number;
  created_at: string;
};
export type ProjectGeneration = {
  id: string;
  project_id: string;
  name: string;
  status: "staged" | "approved" | "failed";
  manifest: {
    summary: string;
    files: { path: string; content: string }[];
  };
  output_path: string | null;
  created_at: string;
  updated_at: string;
};
export type GenerationReview = {
  id: string;
  generation_id: string;
  status: "staged" | "approved";
  report: {
    summary: string;
    findings: {
      severity: "critical" | "high" | "medium" | "low" | "info";
      path: string | null;
      issue: string;
      recommendation: string;
    }[];
  };
  test_manifest: ProjectGeneration["manifest"];
  created_at: string;
  updated_at: string;
};
export type OperationStatus = "pending" | "active" | "complete" | "failed" | "cancelled";
export type OperationEvent = {
  operation_id: string;
  phase: string;
  step: string;
  status: OperationStatus;
  message: string;
  elapsed_ms: number;
  detail?: string;
  result?: unknown;
};
export type OperationStep = OperationEvent & { event: string };
export type ActiveOperation = {
  id: string;
  phase: string;
  status: OperationStatus;
  startedAt: number;
  steps: OperationStep[];
};
export type StreamHandlers = {
  onMetadata: (metadata: StreamMetadata) => void;
  onToken: (content: string) => void;
  onDone: (metadata: StreamMetadata) => void;
  onError: (message: string) => void;
  onCancelled: () => void;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
  return response.json() as Promise<T>;
}

export const getHealth = () => apiGet<HealthResponse>("/health");
export const getProjects = () => apiGet<ProjectSummary[]>("/projects");
export const getProject = (id: string) => apiGet<ProjectDetail>(`/projects/${id}`);
export const getMessages = (id: string) =>
  apiGet<Message[]>(`/conversations/${id}/messages`);
export const getKnowledgeDocuments = () =>
  apiGet<KnowledgeDocument[]>("/knowledge/documents");

export async function uploadKnowledgeDocument(file: File): Promise<KnowledgeDocument> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${API_BASE_URL}/knowledge/documents`, {
    method: "POST",
    body,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Upload failed with status ${response.status}`);
  }
  return response.json() as Promise<KnowledgeDocument>;
}

type OperationHandler = (event: OperationStep) => void;

export type FutureResult = {
  summary: string; confidence: string; survival_score: number;
  scores: Record<string, number>;
  components: { id: string; name: string; cause: string; mitigation: string; files: string[]; downstream: string[] }[];
  timeline: { time: string; component_id: string; state: "stable" | "warning" | "failed"; description: string }[];
  repairs: { priority: string; title: string; change: string; files: string[]; expected_improvement: string }[];
};
export type FutureSimulation = { id: string; scenario_type: string; scenario_input: string; result: FutureResult; created_at: string };
export const getSimulations = (id: string) => apiGet<FutureSimulation[]>(`/projects/${id}/simulations`);
export function runSimulation(id: string, scenario_type: string, scenario_input: string, signal: AbortSignal, onEvent: OperationHandler) {
  return streamOperation<FutureSimulation>(`/projects/${id}/simulations/stream`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scenario_type, scenario_input }) }, signal, onEvent);
}
export async function deleteSimulation(project: string, id: string) {
  const response = await fetch(`${API_BASE_URL}/projects/${project}/simulations/${id}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Could not delete simulation.");
}

async function streamOperation<T>(
  path: string,
  init: RequestInit,
  signal: AbortSignal,
  onEvent: OperationHandler,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { Accept: "text/event-stream", ...init.headers },
    signal,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Operation failed with status ${response.status}`);
  }
  if (!response.body) throw new Error("The browser did not expose the operation stream.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: T | undefined;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (signal.aborted) throw new DOMException("Operation cancelled.", "AbortError");
      buffer += decoder.decode(value, { stream: !done });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";
      for (const block of blocks) {
        const eventName = block.match(/^event: (.+)$/m)?.[1];
        const dataLine = block.match(/^data: (.+)$/m)?.[1];
        if (!eventName || !dataLine) continue;
        const event = { ...JSON.parse(dataLine), event: eventName } as OperationStep;
        onEvent(event);
        if (eventName === "failed") throw new Error(event.message);
        if (eventName === "completed") result = event.result as T;
      }
      if (done) break;
    }
  } finally {
    reader.releaseLock();
  }
  if (!result) throw new Error("The operation ended without a result.");
  return result;
}

export function streamKnowledgeUpload(
  file: File,
  signal: AbortSignal,
  onEvent: OperationHandler,
) {
  const body = new FormData();
  body.append("file", file);
  return streamOperation<KnowledgeDocument>(
    "/knowledge/documents/stream",
    { method: "POST", body },
    signal,
    onEvent,
  );
}

export async function deleteKnowledgeDocument(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/knowledge/documents/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error(`Delete failed with status ${response.status}`);
}

export const getProjectGenerations = (projectId: string) =>
  apiGet<ProjectGeneration[]>(`/projects/${projectId}/generations`);

export async function stageProjectGeneration(projectId: string): Promise<ProjectGeneration> {
  const response = await fetch(`${API_BASE_URL}/projects/${projectId}/generations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "generated-app" }),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.detail ?? `Generation failed with status ${response.status}`);
  return payload as ProjectGeneration;
}

export function streamProjectGeneration(
  projectId: string,
  signal: AbortSignal,
  onEvent: OperationHandler,
) {
  return streamOperation<ProjectGeneration>(
    `/projects/${projectId}/generations/stream`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: "generated-app" }) },
    signal,
    onEvent,
  );
}

export async function approveProjectGeneration(
  projectId: string,
  generationId: string,
): Promise<ProjectGeneration> {
  const response = await fetch(
    `${API_BASE_URL}/projects/${projectId}/generations/${generationId}/approve`,
    { method: "POST" },
  );
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.detail ?? `Approval failed with status ${response.status}`);
  return payload as ProjectGeneration;
}

export function streamProjectApproval(
  projectId: string,
  generationId: string,
  signal: AbortSignal,
  onEvent: OperationHandler,
) {
  return streamOperation<ProjectGeneration>(
    `/projects/${projectId}/generations/${generationId}/approve/stream`,
    { method: "POST" },
    signal,
    onEvent,
  );
}

export const getGenerationReviews = (projectId: string, generationId: string) =>
  apiGet<GenerationReview[]>(
    `/projects/${projectId}/generations/${generationId}/reviews`,
  );

export async function stageGenerationReview(
  projectId: string,
  generationId: string,
): Promise<GenerationReview> {
  const response = await fetch(
    `${API_BASE_URL}/projects/${projectId}/generations/${generationId}/reviews`,
    { method: "POST" },
  );
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.detail ?? `Review failed with status ${response.status}`);
  return payload as GenerationReview;
}

export function streamGenerationReview(
  projectId: string,
  generationId: string,
  signal: AbortSignal,
  onEvent: OperationHandler,
) {
  return streamOperation<GenerationReview>(
    `/projects/${projectId}/generations/${generationId}/reviews/stream`,
    { method: "POST" },
    signal,
    onEvent,
  );
}

export async function approveGenerationReview(
  projectId: string,
  generationId: string,
  reviewId: string,
): Promise<GenerationReview> {
  const response = await fetch(
    `${API_BASE_URL}/projects/${projectId}/generations/${generationId}/reviews/${reviewId}/approve`,
    { method: "POST" },
  );
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.detail ?? `Test approval failed with status ${response.status}`);
  return payload as GenerationReview;
}

export function streamTestApproval(
  projectId: string,
  generationId: string,
  reviewId: string,
  signal: AbortSignal,
  onEvent: OperationHandler,
) {
  return streamOperation<GenerationReview>(
    `/projects/${projectId}/generations/${generationId}/reviews/${reviewId}/approve/stream`,
    { method: "POST" },
    signal,
    onEvent,
  );
}

export async function streamChat(
  prompt: string,
  conversationId: string | null,
  handlers: StreamHandlers,
  signal: AbortSignal,
  requestId?: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ prompt, conversation_id: conversationId, request_id: requestId }),
    signal,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with status ${response.status}`);
  }
  if (!response.body) throw new Error("The browser did not expose the response stream.");

  const reader = response.body.getReader();
  const cancelReader = () => {
    void reader.cancel("Generation cancelled by the user.").catch(() => undefined);
  };
  signal.addEventListener("abort", cancelReader, { once: true });
  const decoder = new TextDecoder();
  let buffer = "";
  let terminalError: string | null = null;
  try {
    if (signal.aborted) {
      cancelReader();
      throw new DOMException("Generation cancelled.", "AbortError");
    }
    while (true) {
      const { done, value } = await reader.read();
      if (signal.aborted) throw new DOMException("Generation cancelled.", "AbortError");
      buffer += decoder.decode(value, { stream: !done });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";
      for (const block of events) {
        if (signal.aborted) throw new DOMException("Generation cancelled.", "AbortError");
        const event = block.match(/^event: (.+)$/m)?.[1];
        const dataLine = block.match(/^data: (.+)$/m)?.[1];
        if (!event || !dataLine) continue;
        const data = JSON.parse(dataLine);
        if (event === "metadata") handlers.onMetadata(data);
        if (event === "token") handlers.onToken(data.content);
        if (event === "done") handlers.onDone(data);
        if (event === "cancelled") handlers.onCancelled();
        if (event === "error") {
          terminalError = data.message;
          handlers.onError(data.message);
        }
      }
      if (done) break;
    }
  } finally {
    signal.removeEventListener("abort", cancelReader);
    reader.releaseLock();
  }
  if (terminalError) throw new Error(terminalError);
}

export async function cancelChat(requestId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/streams/${requestId}/cancel`, { method: "POST" });
  if (!response.ok) throw new Error("Could not confirm server cancellation.");
}
