import { useState, useRef, useCallback, memo, useEffect } from "react";
import { Virtuoso } from "react-virtuoso";
import type { VirtuosoHandle } from "react-virtuoso";
import { useAppStore } from "../stores/appStore";
import { streamChat, conversationApi, chatApi } from "../services/api";
import type { CardData, FileDownloadInfo, PlanData, WorkerInfo, SkillNoticeData, ToolCallEntry } from "../types";
import MessageBubble from "./MessageBubble";
import InputArea from "./InputArea";
import WelcomeScreen from "./WelcomeScreen";
import SkillNoticeCard from "./SkillNoticeCard";
import PlanCard from "./PlanCard";
import WorkersCard from "./WorkersCard";

interface ChatPanelProps {
  onConversationCreated?: () => void;
}

export default function ChatPanel({ onConversationCreated }: ChatPanelProps) {
  const {
    messages, addMessage, updateLastAssistant, isStreaming, setStreaming,
    token, selectedSkill, currentConversationId, setCurrentConversationId,
    setConversations, updateConversationTitle,
    providers, setProviders, selectedProviderId, selectedModel,
  } = useAppStore();

  const [skillNotice, setSkillNotice] = useState<SkillNoticeData | null>(null);
  const [streamStatus, setStreamStatus] = useState<"idle" | "connecting" | "thinking" | "tool" | "answering">("idle");

  const virtuosoRef = useRef<VirtuosoHandle>(null);
  const isMountedRef = useRef(true);
  const rafRef = useRef<number | null>(null);
  const dirtyRef = useRef(false);
  // Track whether we should auto-follow the bottom
  const atBottomRef = useRef(true);

  // Stream state accumulated in refs — only committed to Zustand via RAF
  const streamRef = useRef({
    content: "",
    cards: [] as CardData[],
    fileDownloads: [] as FileDownloadInfo[],
    plan: null as PlanData | null,
    workers: [] as WorkerInfo[],
    toolCalls: [] as ToolCallEntry[],
  });

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  useEffect(() => {
    chatApi.listProviders().then((res) => setProviders(res.providers)).catch(() => {});
  }, [setProviders]);

  const scrollToBottom = useCallback(() => {
    if (atBottomRef.current) {
      virtuosoRef.current?.scrollToIndex({ index: "LAST", behavior: "smooth" });
    }
  }, []);

  const refreshConversations = useCallback(async (wasNew: boolean) => {
    try {
      const convs = await conversationApi.list();
      setConversations(convs);
      if (wasNew && convs.length > 0) setCurrentConversationId(convs[0].id);
      onConversationCreated?.();
    } catch { /* non-critical */ }
  }, [onConversationCreated, setConversations, setCurrentConversationId]);

  const scheduleFlush = useCallback(() => {
    if (rafRef.current !== null) return; // already scheduled
    dirtyRef.current = true;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      if (!dirtyRef.current || !isMountedRef.current) return;
      dirtyRef.current = false;
      const s = streamRef.current;
      updateLastAssistant(
        s.content,
        s.cards.length > 0 ? [...s.cards] : undefined,
        s.fileDownloads.length > 0 ? [...s.fileDownloads] : undefined,
        s.plan ?? undefined,
        s.workers.length > 0 ? [...s.workers] : undefined,
        s.toolCalls.length > 0 ? [...s.toolCalls] : undefined,
      );
      scrollToBottom();
    });
  }, [updateLastAssistant, scrollToBottom]);

  const handleSend = async (text?: string) => {
    const msg = (text || "").trim();
    if (!msg || isStreaming || !token) return;

    setSkillNotice(null);
    // Reset stream state
    streamRef.current = { content: "", cards: [], fileDownloads: [], plan: null, workers: [], toolCalls: [] };
    dirtyRef.current = false;

    const wasNew = currentConversationId === null;
    addMessage({ id: `user-${Date.now()}`, role: "user", content: msg, timestamp: Date.now() });
    addMessage({ id: `asst-${Date.now()}`, role: "assistant", content: "", timestamp: Date.now() });
    setStreaming(true);
    setStreamStatus("connecting");
    // Force scroll to bottom on new message
    atBottomRef.current = true;
    scrollToBottom();

    const s = streamRef.current;
    let streamFinished = false;

    try {
      const effectiveModel = selectedModel || providers.find((p) => p.id === selectedProviderId)?.models?.[0];
      for await (const event of streamChat(msg, currentConversationId ?? undefined, selectedSkill ?? undefined,
        selectedProviderId !== "default" ? selectedProviderId : undefined, effectiveModel ?? undefined)) {
        if (!isMountedRef.current) break;

        switch (event.event) {
          case "text":
            setStreamStatus("answering");
            s.content += event.data?.text || "";
            scheduleFlush();
            break;
          case "thinking": setStreamStatus("thinking"); break;
          case "tool_call": {
            setStreamStatus("tool");
            const tcStatus = event.data?.status || "running";
            if (tcStatus === "running") {
              s.toolCalls = [...s.toolCalls, {
                tool_name: event.data?.name || "",
                tool_args: event.data?.tool_args,
                started_at: Date.now(),
                status: "running",
              }];
            } else {
              const last = s.toolCalls[s.toolCalls.length - 1];
              if (last) {
                const updated = { ...last };
                updated.status = tcStatus === "completed" ? "completed" :
                                tcStatus === "failed" || tcStatus === "error" || tcStatus === "timeout" ? "failed" :
                                "running";
                if (event.data?.result !== undefined) updated.result = event.data.result;
                updated.success = tcStatus === "completed";
                updated.completed_at = Date.now();
                s.toolCalls = [...s.toolCalls.slice(0, -1), updated];
              }
            }
            scheduleFlush();
            break;
          }
          case "tool_result": {
            const last = s.toolCalls[s.toolCalls.length - 1];
            if (last) {
              const updated = { ...last };
              updated.result = event.data?.result;
              updated.success = event.data?.success ?? true;
              updated.completed_at = Date.now();
              updated.status = updated.success ? "completed" : "failed";
              s.toolCalls = [...s.toolCalls.slice(0, -1), updated];
            }
            scheduleFlush();
            break;
          }
          case "notice": setSkillNotice(event.data as SkillNoticeData); break;
          case "card": {
            if (event.data?.name === "get_stock_quote") s.cards = [...s.cards, { type: "stock", data: event.data.data?.quote || event.data.data }];
            else if (event.data?.name === "get_fund_info") s.cards = [...s.cards, { type: "fund", data: event.data.data?.fund_info || event.data.data }];
            scheduleFlush();
            break;
          }
          case "plan_created": s.plan = event.data as PlanData; scheduleFlush(); break;
          case "plan_step_update": {
            if (s.plan) {
              const step = s.plan.steps.find(st => st.step === event.data?.step);
              if (step) { step.status = event.data?.status ?? step.status; if (event.data?.error) step.error = event.data.error; }
            }
            scheduleFlush();
            break;
          }
          case "worker_started": s.workers = [...s.workers, { worker_id: event.data?.worker_id, task: event.data?.task || "", status: "running" as const }]; scheduleFlush(); break;
          case "worker_done": {
            const w = s.workers.find(w => w.worker_id === event.data?.worker_id);
            if (w) { w.status = event.data?.status === "failed" ? "failed" : "completed"; if (event.data?.result_preview) w.result_preview = event.data.result_preview; }
            scheduleFlush();
            break;
          }
          case "file_download": if (event.data?.file_id) { s.fileDownloads = [...s.fileDownloads, event.data as FileDownloadInfo]; scheduleFlush(); } break;
          case "conversation_id": {
            const cid = event.data?.conversation_id as number | undefined;
            if (cid && currentConversationId === null) {
              setCurrentConversationId(cid);
              const { conversations: cur, setConversations: setCur } = useAppStore.getState();
              if (!cur.some((c) => c.id === cid)) {
                const now = new Date().toISOString();
                const title = msg.replace(/\n/g, " ").slice(0, 30) + (msg.length > 30 ? "…" : "");
                setCur([{ id: cid, title, created_at: now, updated_at: now }, ...cur]);
              }
            }
            break;
          }
          case "conversation_title": {
            const cid = event.data?.conversation_id as number | undefined;
            if (cid && event.data?.title) updateConversationTitle(cid, event.data.title);
            break;
          }
          case "done":
            streamFinished = true;
            break;
          case "error":
            s.content += `\n\n❌ 错误: ${event.data?.message || "未知错误"}`;
            streamFinished = true;
            break;
        }
        if (streamFinished) break;
      }
    } catch (err) {
      s.content += `\n\n❌ 请求失败: ${err instanceof Error ? err.message : "未知错误"}`;
    } finally {
      // Cancel pending RAF and do final flush
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      dirtyRef.current = false;
      const final = streamRef.current;
      updateLastAssistant(
        final.content,
        final.cards.length > 0 ? [...final.cards] : undefined,
        final.fileDownloads.length > 0 ? [...final.fileDownloads] : undefined,
        final.plan ?? undefined,
        final.workers.length > 0 ? [...final.workers] : undefined,
        final.toolCalls.length > 0 ? [...final.toolCalls] : undefined,
      );
      setStreaming(false);
      setStreamStatus("idle");
      scrollToBottom();
      refreshConversations(wasNew);
    }
  };

  // Virtuoso item renderer
  const itemContent = useCallback((idx: number) => {
    const msg = messages[idx];
    if (!msg) return null;
    const isLast = isStreaming && idx === messages.length - 1;
    return (
      <div>
        {msg.role === "assistant" && idx === messages.length - 1 && skillNotice && <SkillNoticeCard notice={skillNotice} />}
        {msg.role === "assistant" && msg.plan && <PlanCard plan={msg.plan} />}
        {msg.role === "assistant" && msg.workers && msg.workers.length > 0 && <WorkersCard workers={msg.workers} />}
        {msg.cards?.map((card, ci) => (
          <pre key={ci} style={{ fontSize: 12, background: "var(--surface-sunken)", padding: 8, borderRadius: 6, color: "var(--text-secondary)" }}>
            {JSON.stringify(card.data, null, 2)}
          </pre>
        ))}
        <MessageBubble msg={msg} isStreaming={!!isLast} />
        {msg.role === "assistant" && msg.fileDownloads?.map((fd) => (
          <div key={fd.file_id} style={{ marginTop: 4 }}>
            <a href={fd.download_url} download={fd.filename} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: "var(--brand)" }}>{fd.filename}</a>
          </div>
        ))}
      </div>
    );
  }, [messages, isStreaming, skillNotice]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div className="chat-area" style={{ flex: 1, minHeight: 0 }}>
        {messages.length === 0 ? (
          <div className="chat-inner" style={{ overflowY: "auto", height: "100%", paddingTop: 20, paddingBottom: 12 }}>
            <WelcomeScreen onSend={(t) => handleSend(t)} />
          </div>
        ) : (
          <Virtuoso
            ref={virtuosoRef}
            style={{ height: "100%", paddingTop: 20, paddingBottom: 12 }}
            totalCount={messages.length}
            itemContent={itemContent}
            followOutput="smooth"
            atBottomStateChange={(bottom) => { atBottomRef.current = bottom; }}
            increaseViewportBy={{ top: 400, bottom: 200 }}
            className="chat-inner"
          />
        )}
      </div>

      {isStreaming && <StreamStatus status={streamStatus} />}
      <InputArea onSend={handleSend} />
    </div>
  );
}

/* Small sub-components */

const toStatusText = (status: string) =>
  status === "connecting" ? "正在连接…" :
  status === "thinking" ? "正在规划任务…" :
  status === "tool" ? "正在调用工具…" :
  status === "answering" ? "正在生成回答…" : "";

const StreamStatus = memo(({ status }: { status: string }) => (
  <div className="stream-status-bar">
    <div className="stream-status-dot" />
    <span>{toStatusText(status)}</span>
    <span style={{ marginLeft: "auto", fontSize: 11, opacity: 0.55, userSelect: "none" }}>会话进行中</span>
  </div>
));
StreamStatus.displayName = "StreamStatus";
