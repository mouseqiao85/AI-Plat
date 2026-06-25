const API_BASE = "/api/v1";
const AUTH_EXPIRED_EVENT = "agent-platform:auth-expired";

function notifyAuthExpired() {
  if (typeof window === "undefined") return;
  const hadAuth = Boolean(localStorage.getItem("token") || localStorage.getItem("user"));
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  if (hadAuth) {
    window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
  }
}

function shouldExpireAuth(path: string) {
  return path !== "/auth/login" && path !== "/auth/register" && path !== "/auth/dev-login";
}

async function buildResponseError(res: Response, shouldNotifyAuth = true): Promise<Error> {
  const body = await res.json().catch(() => ({}));
  if (res.status === 401 && shouldNotifyAuth) {
    notifyAuthExpired();
  }
  return new Error(body.detail || body.error || `HTTP ${res.status}`);
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem("token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // 30s timeout for non-streaming requests
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);

  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers, signal: controller.signal });
    if (!res.ok) {
      throw await buildResponseError(res, shouldExpireAuth(path));
    }
    if (res.status === 204 || res.headers.get("content-length") === "0") {
      return undefined as T;
    }
    return res.json();
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("请求超时，请检查网络连接后重试");
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

/** Retry a GET request up to 2 times on network errors or 5xx responses. */
async function requestWithRetry<T>(path: string, retries = 2): Promise<T> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await request<T>(path);
    } catch (err) {
      const isLastAttempt = attempt === retries;
      const msg = err instanceof Error ? err.message : "";
      const isRetryable = msg.includes("HTTP 5") || msg.includes("网络") || msg.includes("Failed to fetch");
      if (isLastAttempt || !isRetryable) throw err;
      // Exponential backoff: 1s, 2s
      await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
    }
  }
  throw new Error("unreachable");
}

// Auth
export const authApi = {
  register: (username: string, password: string) =>
    request<{ access_token: string; user: { id: number; nickname: string; membership_tier: string; role?: string } }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  login: (username: string, password: string) =>
    request<{ access_token: string; user: { id: number; nickname: string; membership_tier: string; role?: string } }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  devLogin: () =>
    request<{ access_token: string; user: { id: number; nickname: string; membership_tier: string; role?: string } }>("/auth/dev-login", {
      method: "POST",
    }),
  me: () =>
    request<{ id: number; nickname: string; membership_tier: string; role?: string }>("/auth/me"),
};

// Skills (uses retry for GET requests)
export const skillApi = {
  list: () =>
    requestWithRetry<{ skills: import("../types").Skill[] }>("/skills/"),
  get: (name: string) =>
    requestWithRetry<import("../types").Skill>(`/skills/${encodeURIComponent(name)}`),
  add: (path: string) =>
    request<import("../types").Skill>("/skills/", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),
  importGithub: async (data: { url: string; branch?: string; sub_path?: string; enable?: boolean }) => {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600_000);
    try {
      const res = await fetch(`${API_BASE}/skills/import/github`, {
        method: "POST",
        headers,
        body: JSON.stringify(data),
        signal: controller.signal,
      });
      if (!res.ok) {
        throw await buildResponseError(res);
      }
      return res.json() as Promise<import("../types").SkillGithubImportResult>;
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        throw new Error("GitHub 导入超时，请稍后重试");
      }
      throw err;
    } finally {
      clearTimeout(timeoutId);
    }
  },
  uploadZip: async (file: File) => {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/skills/upload`, {
      method: "POST",
      headers,
      body: formData,
    });
    if (!res.ok) {
      throw await buildResponseError(res);
    }
    return res.json() as Promise<import("../types").Skill>;
  },
  remove: (name: string) =>
    request<{ name: string; removed: boolean }>(`/skills/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
  enable: (name: string) =>
    request<{ name: string; enabled: boolean }>(`/skills/${encodeURIComponent(name)}/enable`, {
      method: "POST",
    }),
  disable: (name: string) =>
    request<{ name: string; enabled: boolean }>(`/skills/${encodeURIComponent(name)}/disable`, {
      method: "POST",
    }),
};

// Conversations (uses retry for GET requests)
export const conversationApi = {
  list: () =>
    requestWithRetry<import("../types").Conversation[]>("/conversations/"),
  messages: (id: number) =>
    requestWithRetry<import("../types").ConversationMessage[]>(`/conversations/${id}/messages`),
  rename: (id: number, title: string) =>
    request<import("../types").Conversation>(`/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  remove: (id: number) =>
    request<void>(`/conversations/${id}`, { method: "DELETE" }),
  clearMessages: (id: number) =>
    request<void>(`/conversations/${id}/messages`, { method: "DELETE" }),
  getUserProfile: () =>
    requestWithRetry<{ profile: { memory: import("../types").UserProfile | null } | null }>("/conversations/user-profile"),
  clearUserProfile: () =>
    request<void>("/conversations/user-profile", { method: "DELETE" }),
  deleteAll: () =>
    request<{ deleted: number }>("/conversations/delete-all", { method: "POST" }),
};

// Chat (SSE streaming)

// Track the active AbortController and reader so the UI can cancel an in-flight request
let activeAbortController: AbortController | null = null;
let activeReader: ReadableStreamDefaultReader<Uint8Array> | null = null;

/** Cancel the current streaming chat request (if any). */
export function cancelStream() {
  if (activeAbortController) {
    activeAbortController.abort();
    activeAbortController = null;
  }
  if (activeReader) {
    activeReader.cancel().catch(() => {});
    activeReader.releaseLock();
    activeReader = null;
  }
}

/** Maximum seconds of silence (no SSE event) before we consider the stream dead.
 *  3 minutes — the backend sends ping events every 15s, so real inactivity means
 *  the server is down. Deep research tasks still work because they emit continuous events. */
const STREAM_INACTIVITY_TIMEOUT = 3 * 60_000; // 3min

export async function* streamChat(message: string, conversationId?: number, skillName?: string, providerId?: string, model?: string) {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("Not authenticated");

  const body: Record<string, unknown> = { message };
  if (conversationId) body.conversation_id = conversationId;
  if (skillName) body.skill_name = skillName;
  if (providerId) body.provider_id = providerId;
  if (model) body.model = model;

  // AbortController with timeout for the initial connection (not the stream)
  const controller = new AbortController();
  activeAbortController = controller;
  const connectTimeout = setTimeout(() => controller.abort(), 60_000);

  const response = await fetch(`${API_BASE}/chat/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
    signal: controller.signal,
  });

  clearTimeout(connectTimeout);

  if (!response.ok) {
    activeAbortController = null;
    throw await buildResponseError(response);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    activeAbortController = null;
    throw new Error("No response body");
  }
  activeReader = reader;

  const decoder = new TextDecoder();
  let buffer = "";
  let lastActivity = Date.now();
  let inactivityTimer: ReturnType<typeof setTimeout> | null = null;

  try {
    while (true) {
      // Race reader.read() against an inactivity timeout so we don't block forever
      const readPromise = reader.read();
      const timeoutPromise = new Promise<never>((_, reject) => {
        const remaining = STREAM_INACTIVITY_TIMEOUT - (Date.now() - lastActivity);
        // Clear previous timer to prevent accumulation
        if (inactivityTimer !== null) clearTimeout(inactivityTimer);
        inactivityTimer = setTimeout(
          () => reject(new Error("服务器响应超时，请稍后重试")),
          Math.max(remaining, 5000),
        );
      });

      let done: boolean;
      let value: Uint8Array | undefined;
      try {
        const result = await Promise.race([readPromise, timeoutPromise]);
        done = result.done;
        value = result.value;
      } catch (err) {
        if (err instanceof Error && err.message.includes("超时")) {
          throw err;
        }
        // AbortError or other — re-throw
        throw err;
      }

      if (value) {
        lastActivity = Date.now();
        buffer += decoder.decode(value, { stream: true });
      }

      if (done) {
        // Server closed the stream — flush any remaining buffered data before breaking
        if (buffer.trim()) {
          buffer += "\n\n"; // ensure the last event is terminated
          const events = buffer.split("\n\n");
          for (const eventBlock of events) {
            if (!eventBlock.trim()) continue;
            let eventType = "";
            const dataLines: string[] = [];
            for (const line of eventBlock.split("\n")) {
              if (line.startsWith("event: ")) {
                eventType = line.slice(7).trim();
              } else if (line.startsWith("data: ")) {
                dataLines.push(line.slice(6).trim());
              }
            }
            const dataStr = dataLines.join("\n");
            if (!dataStr) continue;
            try {
              const data = JSON.parse(dataStr);
              yield { event: eventType, data };
            } catch (e) {
              console.warn("[SSE] JSON parse error on flush:", { eventType, dataStr: dataStr.slice(0, 200) });
            }
          }
        }
        console.debug("[SSE] stream closed by server (done=true)");
        break;
      }

      // SSE events are separated by double newlines
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";

      for (const eventBlock of events) {
        let eventType = "";
        const dataLines: string[] = [];

        for (const line of eventBlock.split("\n")) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            // SSE spec: multiple data: lines are concatenated with newlines
            dataLines.push(line.slice(6).trim());
          }
        }

        const dataStr = dataLines.join("\n");
        if (!dataStr) continue;

        // Heartbeat pings keep the connection alive — reset inactivity timer
        if (eventType === "ping") { lastActivity = Date.now(); continue; }

        try {
          const data = JSON.parse(dataStr);
          yield { event: eventType, data };
        } catch (e) {
          // Skip malformed JSON — log for debugging
          console.warn("[SSE] JSON parse error, skipping block:", { eventType, dataStr: dataStr.slice(0, 200), error: e });
        }
      }
    }
  } finally {
    if (inactivityTimer !== null) clearTimeout(inactivityTimer);
    activeReader = null;
    activeAbortController = null;
    try { reader.releaseLock(); } catch { /* already released */ }
    console.debug("[SSE] generator finally — reader released");
  }
}

// Chat providers
export const chatApi = {
  listProviders: () =>
    requestWithRetry<{ providers: import("../types").LlmProvider[] }>("/chat/providers"),
};

// Marketplace
export const marketplaceApi = {
  list: (category?: string, page?: number, pageSize?: number) => {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (page) params.set("page", String(page));
    if (pageSize) params.set("pageSize", String(pageSize));
    const qs = params.toString();
    return requestWithRetry<{ agents: import("../types").MarketAgent[]; total: number; page: number; pageSize: number }>(`/marketplace/agents${qs ? "?" + qs : ""}`);
  },
  get: (id: number) =>
    requestWithRetry<import("../types").MarketAgent>(`/marketplace/agents/${id}`),
  create: (data: {
    title: string;
    function?: string;
    description: string;
    access_url?: string;
    knowledge_url?: string;
    tags: string;
    category: string;
    featured: boolean;
    author?: string;
  }) =>
    request<import("../types").MarketAgent>("/marketplace/agents", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: {
    title?: string;
    function?: string;
    description?: string;
    access_url?: string;
    knowledge_url?: string;
    tags?: string;
    category?: string;
    featured?: boolean;
    author?: string;
  }) =>
    request<import("../types").MarketAgent>(`/marketplace/agents/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  remove: (id: number) =>
    request<void>(`/marketplace/agents/${id}`, { method: "DELETE" }),
};

// Knowledge Graph / GraphRAG
export const knowledgeGraphApi = {
  getStats: () =>
    requestWithRetry<import("../types").KnowledgeGraphStats>("/knowledge-graph/stats"),
  listSources: () =>
    requestWithRetry<import("../types").KnowledgeSource[]>("/knowledge-graph/sources"),
  deleteSource: (id: number) =>
    request<import("../types").KnowledgeSourceDeleteResult>(`/knowledge-graph/sources/${id}`, {
      method: "DELETE",
    }),
  listImportJobs: (limit = 20, offset = 0) =>
    requestWithRetry<import("../types").KnowledgeImportJob[]>(`/knowledge-graph/import-jobs?limit=${limit}&offset=${offset}`),
  searchNodes: (params?: { q?: string; node_type?: string; source_id?: number; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set("q", params.q);
    if (params?.node_type) qs.set("node_type", params.node_type);
    if (params?.source_id !== undefined) qs.set("source_id", String(params.source_id));
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const query = qs.toString();
    return requestWithRetry<import("../types").KnowledgeNode[]>(`/knowledge-graph/nodes${query ? "?" + query : ""}`);
  },
  getNode: (id: number) =>
    requestWithRetry<import("../types").KnowledgeNode>(`/knowledge-graph/nodes/${id}`),
  getNeighbors: (id: number, params?: { depth?: number; direction?: "incoming" | "outgoing" | "both"; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.depth) qs.set("depth", String(params.depth));
    if (params?.direction) qs.set("direction", params.direction);
    if (params?.limit) qs.set("limit", String(params.limit));
    const query = qs.toString();
    return requestWithRetry<import("../types").KnowledgeNeighbors>(`/knowledge-graph/nodes/${id}/neighbors${query ? "?" + query : ""}`);
  },
  getSubgraph: (params?: { q?: string; node_id?: number; source_id?: number; depth?: number; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set("q", params.q);
    if (params?.node_id !== undefined) qs.set("node_id", String(params.node_id));
    if (params?.source_id !== undefined) qs.set("source_id", String(params.source_id));
    if (params?.depth) qs.set("depth", String(params.depth));
    if (params?.limit) qs.set("limit", String(params.limit));
    const query = qs.toString();
    return requestWithRetry<import("../types").KnowledgeSubgraph>(`/knowledge-graph/subgraph${query ? "?" + query : ""}`);
  },
  queryGraphRAG: (q: string, limit = 5) => {
    const qs = new URLSearchParams();
    qs.set("q", q);
    qs.set("limit", String(limit));
    return requestWithRetry<import("../types").GraphRAGQueryResult>(`/knowledge-graph/graphrag?${qs.toString()}`);
  },
  answerGraphRAG: (data: { q: string; limit?: number; provider_id?: string; model?: string }) =>
    request<import("../types").GraphRAGAnswerResult>("/knowledge-graph/graphrag/answer", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  importObsidianVault: async (file: File, sourceName?: string) => {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const formData = new FormData();
    formData.append("file", file);
    if (sourceName) formData.append("source_name", sourceName);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600_000);
    try {
      const res = await fetch(`${API_BASE}/knowledge-graph/import/obsidian`, {
        method: "POST",
        headers,
        body: formData,
        signal: controller.signal,
      });
      if (!res.ok) {
        throw await buildResponseError(res);
      }
      return res.json() as Promise<import("../types").KnowledgeImportResult>;
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        throw new Error("Obsidian 导入超时，请稍后重试");
      }
      throw err;
    } finally {
      clearTimeout(timeoutId);
    }
  },
};

// Admin
export const adminApi = {
  listProviders: () =>
    request<{ providers: import("../types").LlmProvider[]; static_count: number; dynamic_count: number }>("/admin/providers"),
  addProvider: (provider: Omit<import("../types").LlmProvider, "custom_header"> & { custom_header?: string }) =>
    request<{ added: boolean; id: string }>("/admin/providers", {
      method: "POST",
      body: JSON.stringify(provider),
    }),
  updateProvider: (id: string, provider: Omit<import("../types").LlmProvider, "custom_header"> & { custom_header?: string }) =>
    request<{ updated: boolean; id: string }>(`/admin/providers/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(provider),
    }),
  deleteProvider: (id: string) =>
    request<{ deleted: boolean; id: string }>(`/admin/providers/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
};

// ── hermes-bridge (multi-agent orchestrator, /api/v2) ──────────────────────

const HERMES_BASE = "/api/v2";

async function hermesRequest<T>(path: string, options?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const token = localStorage.getItem("token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const { timeoutMs = 60_000, signal, ...fetchOptions } = options || {};
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  const abortHandler = () => controller.abort();
  if (signal) signal.addEventListener("abort", abortHandler, { once: true });
  try {
    const res = await fetch(`${HERMES_BASE}${path}`, { ...fetchOptions, headers, signal: controller.signal });
    if (!res.ok) {
      throw await buildResponseError(res);
    }
    if (res.status === 204) return undefined as T;
    return res.json();
  } finally {
    if (signal) signal.removeEventListener("abort", abortHandler);
    clearTimeout(timeoutId);
  }
}

export const hermesApi = {
  // Roles
  listRoles: (category?: string) => {
    const qs = category ? `?category=${encodeURIComponent(category)}` : "";
    return hermesRequest<{ roles: import("../types").ExpertRole[]; count: number }>(`/roles${qs}`);
  },
  getRole: (id: string) =>
    hermesRequest<import("../types").ExpertRole>(`/roles/${encodeURIComponent(id)}`),
  reloadGstack: () =>
    hermesRequest<{ scanned: number; loaded: number; installed: number; install_failures: { name: string; error: string }[]; duration_ms: number }>(
      "/gstack/load",
      { method: "POST", body: JSON.stringify({ install: true }) },
    ),

  // Scenarios
  listScenarios: () =>
    hermesRequest<{ scenarios: import("../types").ToolScenario[] }>("/scenarios"),

  // Flows
  listFlows: (ownerId?: number) => {
    const qs = ownerId !== undefined ? `?owner_id=${ownerId}` : "";
    return hermesRequest<{ flows: import("../types").DialogFlow[] }>(`/flows${qs}`);
  },
  getFlow: (id: number) =>
    hermesRequest<import("../types").DialogFlow>(`/flows/${id}`),
  createFlow: (data: {
    name: string;
    flow_type: import("../types").FlowType;
    role_ids: string[];
    description?: string;
    scenario_id?: string;
    prompt_template?: string;
    model?: string;
    sandbox_policy?: import("../types").SandboxPolicy;
    flow_spec?: Record<string, unknown>;
    owner_id?: number;
  }) =>
    hermesRequest<import("../types").DialogFlow>("/flows", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateFlow: (id: number, data: Partial<{
    name: string;
    description: string;
    flow_type: import("../types").FlowType;
    role_ids: string[];
    scenario_id: string;
    prompt_template: string;
    model: string;
    sandbox_policy: import("../types").SandboxPolicy;
    flow_spec: Record<string, unknown>;
  }>) =>
    hermesRequest<import("../types").DialogFlow>(`/flows/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteFlow: (id: number) =>
    hermesRequest<{ deleted: number }>(`/flows/${id}`, { method: "DELETE" }),

  // Runs
  startFlowRun: (flowId: number, message: string, signal?: AbortSignal) =>
    hermesRequest<{ run_id: number; status: string }>(`/flows/${flowId}/runs`, {
      method: "POST",
      body: JSON.stringify({ message }),
      signal,
    }),
  listRuns: (flowId: number) =>
    hermesRequest<{ runs: import("../types").FlowRun[] }>(`/flows/${flowId}/runs`),
  getRun: (runId: number) =>
    hermesRequest<import("../types").FlowRun>(`/runs/${runId}`),
  listRunEvents: (runId: number, afterSeq = 0) =>
    hermesRequest<{ events: import("../types").RunEvent[] }>(`/runs/${runId}/events?after_seq=${afterSeq}`),
  listCollaborationMessages: (runId: number, afterSeq = 0, limit = 500) =>
    hermesRequest<{ messages: import("../types").CollaborationMessage[] }>(
      `/runs/${runId}/collaboration/messages?after_seq=${afterSeq}&limit=${limit}`,
    ),
  cancelRun: (runId: number) =>
    hermesRequest<import("../types").FlowRun>(`/runs/${runId}/cancel`, { method: "POST" }),
  deleteRun: (runId: number) =>
    hermesRequest<{ deleted: number; workdir_removed: boolean; workdir: string }>(`/runs/${runId}`, { method: "DELETE" }),
  downloadRunArtifacts: async (runId: number) => {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${HERMES_BASE}/runs/${runId}/artifacts.zip`, { headers });
    if (!res.ok) {
      throw await buildResponseError(res);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = disposition.match(/filename\*?=(?:UTF-8''|\")?([^\";]+)/i);
    const filename = match?.[1] ? decodeURIComponent(match[1]) : `run-${runId}-materials.zip`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};

export const tabsApi = {
  listTabs: () =>
    hermesRequest<{ tabs: import("../types").SkillTab[] }>("/tabs"),
  getTab: (id: string) =>
    hermesRequest<import("../types").SkillTab>(`/tabs/${encodeURIComponent(id)}`),
  createTab: (data: {
    id: string;
    name: string;
    description?: string;
    source_type?: string;
    source_url?: string;
    branch?: string;
    sub_path?: string;
    icon?: string;
  }) =>
    hermesRequest<import("../types").SkillTab>("/tabs", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateTab: (id: string, data: Partial<{
    name: string;
    description: string;
    icon: string;
    tab_order: number;
  }>) =>
    hermesRequest<import("../types").SkillTab>(`/tabs/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteTab: (id: string) =>
    hermesRequest<{ deleted: string }>(`/tabs/${encodeURIComponent(id)}`, { method: "DELETE" }),
  importTab: (id: string, data: { url: string; branch?: string; sub_path?: string }) =>
    hermesRequest<import("../types").TabImportResult>(`/tabs/${encodeURIComponent(id)}/import`, {
      method: "POST",
      body: JSON.stringify(data),
      timeoutMs: 600_000,
    }),
  refreshTab: (id: string) =>
    hermesRequest<import("../types").TabImportResult>(`/tabs/${encodeURIComponent(id)}/refresh`, {
      method: "POST",
      timeoutMs: 600_000,
    }),
  listTabRoles: (id: string) =>
    hermesRequest<{ roles: import("../types").TabRole[]; count: number }>(`/tabs/${encodeURIComponent(id)}/roles`),
  listTabScenarios: (id: string) =>
    hermesRequest<{ scenarios: import("../types").TabScenario[] }>(`/tabs/${encodeURIComponent(id)}/scenarios`),
};

/** Stream a flow run's events. Yields {event, data} pairs from SSE.
 *  The orchestrator emits role_started / role_completed / role_failed / run_completed / run_failed. */
export async function* streamRunEvents(
  runId: number,
  fromSeq = 0,
  signal?: AbortSignal,
): AsyncGenerator<import("../types").RunEvent> {
  const token = localStorage.getItem("token");
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const response = await fetch(`${HERMES_BASE}/runs/${runId}/events/stream?from_seq=${fromSeq}`, {
    method: "GET",
    headers,
    signal,
  });
  if (!response.ok) {
    throw await buildResponseError(response);
  }
  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (value) buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = done ? "" : events.pop() || "";
      for (const block of events) {
        const dataLines: string[] = [];
        for (const line of block.split("\n")) {
          if (line.startsWith("data: ")) dataLines.push(line.slice(6));
        }
        const dataStr = dataLines.join("\n").trim();
        if (!dataStr) continue;
        try {
          yield JSON.parse(dataStr) as import("../types").RunEvent;
        } catch {
          /* skip malformed */
        }
      }
      if (done) break;
    }
  } finally {
    try { reader.releaseLock(); } catch { /* already released */ }
  }
}
