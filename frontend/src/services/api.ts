const API_BASE = "/api/v1";

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
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${res.status}`);
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
  getUserProfile: () =>
    requestWithRetry<{ profile: import("../types").UserProfile | null }>("/conversations/user-profile"),
  clearUserProfile: () =>
    request<void>("/conversations/user-profile", { method: "DELETE" }),
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

export function chatStream(message: string, conversationId?: number): ReadableStream<Uint8Array> | null {
  const token = localStorage.getItem("token");
  if (!token) return null;
  void message;
  void conversationId;
  return null; // Placeholder — actual streaming handled in streamChat
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
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${response.status}`);
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

  try {
    while (true) {
      // Check for inactivity timeout
      if (Date.now() - lastActivity > STREAM_INACTIVITY_TIMEOUT) {
        throw new Error("服务器响应超时，请稍后重试");
      }

      const { done, value } = await reader.read();

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
