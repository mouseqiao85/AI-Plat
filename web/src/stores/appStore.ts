import { create } from "zustand";
import type { ChatMessage, CardData, FileDownloadInfo, User, Skill, Conversation, PlanData, WorkerInfo, LlmProvider, ToolCallEntry } from "../types";

interface AppState {
  // Auth
  user: User | null;
  token: string | null;
  setAuth: (user: User, token: string) => void;
  logout: () => void;

  // Conversations
  conversations: Conversation[];
  currentConversationId: number | null;
  setConversations: (convs: Conversation[]) => void;
  setCurrentConversationId: (id: number | null) => void;
  removeConversation: (id: number) => void;
  updateConversationTitle: (id: number, title: string) => void;

  // Chat
  messages: ChatMessage[];
  isStreaming: boolean;
  addMessage: (msg: ChatMessage) => void;
  setMessages: (msgs: ChatMessage[]) => void;
  updateLastAssistant: (content: string, cards?: CardData[], fileDownloads?: FileDownloadInfo[], plan?: PlanData, workers?: WorkerInfo[], toolCalls?: ToolCallEntry[]) => void;
  setStreaming: (v: boolean) => void;
  clearMessages: () => void;

  // Skills
  skills: Skill[];
  setSkills: (skills: Skill[]) => void;
  selectedSkill: string | null;
  setSelectedSkill: (name: string | null) => void;

  // LLM Provider
  providers: LlmProvider[];
  setProviders: (providers: LlmProvider[]) => void;
  selectedProviderId: string;
  setSelectedProviderId: (id: string) => void;
  selectedModel: string | null;
  setSelectedModel: (model: string | null) => void;

  // Theme
  theme: "light" | "dark";
  toggleTheme: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Auth
  user: (() => { try { return JSON.parse(localStorage.getItem("user") || "null"); } catch { return null; } })(),
  token: localStorage.getItem("token"),
  setAuth: (user, token) => {
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(user));
    set({ user, token });
  },
  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    set({
      user: null,
      token: null,
      conversations: [],
      currentConversationId: null,
      messages: [],
      skills: [],
      selectedSkill: null,
      providers: [],
    });
  },

  // Conversations
  conversations: [],
  currentConversationId: null,
  setConversations: (convs) => set({ conversations: convs }),
  setCurrentConversationId: (id) => set({ currentConversationId: id }),
  removeConversation: (id) =>
    set((s) => ({
      conversations: s.conversations.filter((c) => c.id !== id),
      currentConversationId: s.currentConversationId === id ? null : s.currentConversationId,
      messages: s.currentConversationId === id ? [] : s.messages,
    })),
  updateConversationTitle: (id, title) =>
    set((s) => ({
      conversations: s.conversations.map((c) => (c.id === id ? { ...c, title } : c)),
    })),

  // Chat
  messages: [],
  isStreaming: false,
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setMessages: (msgs) => set({ messages: msgs }),
  updateLastAssistant: (content, cards, fileDownloads, plan, workers, toolCalls?) =>
    set((s) => {
      // Short-circuit: if nothing changed, return same reference to prevent re-render
      const last = s.messages[s.messages.length - 1];
      if (last?.role === "assistant" && last.content === content &&
          cards === undefined && fileDownloads === undefined &&
          plan === undefined && workers === undefined && toolCalls === undefined) {
        return s;
      }
      const msgs = [...s.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "assistant") {
          msgs[i] = {
            ...msgs[i],
            content,
            cards: cards ?? msgs[i].cards,
            fileDownloads: fileDownloads ?? msgs[i].fileDownloads,
            plan: plan ?? msgs[i].plan,
            workers: workers ?? msgs[i].workers,
            toolCalls: toolCalls ?? msgs[i].toolCalls,
          };
          break;
        }
      }
      return { messages: msgs };
    }),
  setStreaming: (v) => set({ isStreaming: v }),
  clearMessages: () => set({ messages: [] }),

  // Skills
  skills: [],
  setSkills: (skills) => set({ skills }),
  selectedSkill: null,
  setSelectedSkill: (name) => set({ selectedSkill: name }),

  // LLM Provider
  providers: [],
  setProviders: (providers) => set({ providers }),
  selectedProviderId: localStorage.getItem("selectedProviderId") || "default",
  setSelectedProviderId: (id) => {
    localStorage.setItem("selectedProviderId", id);
    set({ selectedProviderId: id, selectedModel: null });
  },
  selectedModel: null,
  setSelectedModel: (model) => set({ selectedModel: model }),

  // Theme
  theme: (localStorage.getItem("theme") as "light" | "dark") || "light",
  toggleTheme: () => set((s) => {
    const next = s.theme === "light" ? "dark" : "light";
    localStorage.setItem("theme", next);
    document.documentElement.setAttribute("data-theme", next);
    return { theme: next };
  }),
}));

// Initialize theme on load
const initTheme = () => {
  const theme = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", theme);
};
initTheme();
