import { useState, useRef, useCallback, memo, useEffect } from "react";
import { useAppStore } from "../stores/appStore";
import { streamChat, conversationApi, chatApi } from "../services/api";
import type { CardData, FileDownloadInfo, PlanData, WorkerInfo, SkillNoticeData } from "../types";
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
  const [toolCalls, setToolCalls] = useState<Array<{ tool_name: string; tool_args?: Record<string, unknown>; result?: unknown; success?: boolean }>>([]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const isMountedRef = useRef(true);
  const flushTimerRef = useRef<number | null>(null);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (flushTimerRef.current !== null) window.clearTimeout(flushTimerRef.current);
    };
  }, []);

  useEffect(() => {
    chatApi.listProviders().then((res) => setProviders(res.providers)).catch(() => {});
  }, [setProviders]);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }), 80);
  }, []);

  const refreshConversations = useCallback(async (wasNew: boolean) => {
    try {
      const convs = await conversationApi.list();
      setConversations(convs);
      if (wasNew && convs.length > 0) setCurrentConversationId(convs[0].id);
      onConversationCreated?.();
    } catch { /* non-critical */ }
  }, [onConversationCreated, setConversations, setCurrentConversationId]);

  const flushAssistant = (fullContent: string, cards: CardData[], fileDownloads: FileDownloadInfo[], plan: PlanData | null, workers: WorkerInfo[]) => {
    const flush = () => {
      updateLastAssistant(fullContent, cards.length > 0 ? cards : undefined, fileDownloads.length > 0 ? fileDownloads : undefined, plan ?? undefined, workers.length > 0 ? workers : undefined);
      scrollToBottom();
    };
    flush();
  };

  const handleSend = async (text?: string) => {
    const msg = (text || "").trim();
    if (!msg || isStreaming || !token) return;

    setSkillNotice(null);
    setToolCalls([]);

    const wasNew = currentConversationId === null;
    addMessage({ id: `user-${Date.now()}`, role: "user", content: msg, timestamp: Date.now() });
    addMessage({ id: `asst-${Date.now()}`, role: "assistant", content: "", timestamp: Date.now() });
    setStreaming(true);
    setStreamStatus("connecting");
    scrollToBottom();

    let fullContent = "";
    const cards: CardData[] = [];
    const fileDownloads: FileDownloadInfo[] = [];
    let currentPlan: PlanData | null = null;
    let currentWorkers: WorkerInfo[] = [];
    const tcs: Array<{ tool_name: string; tool_args?: Record<string, unknown>; result?: unknown; success?: boolean }> = [];

    try {
      const effectiveModel = selectedModel || providers.find((p) => p.id === selectedProviderId)?.models?.[0];
      for await (const event of streamChat(msg, currentConversationId ?? undefined, selectedSkill ?? undefined,
        selectedProviderId !== "default" ? selectedProviderId : undefined, effectiveModel ?? undefined)) {
        if (!isMountedRef.current) break;

        switch (event.event) {
          case "text":
            setStreamStatus("answering");
            fullContent += event.data?.text || "";
            break;
          case "thinking": setStreamStatus("thinking"); break;
          case "tool_call":
            setStreamStatus("tool");
            tcs.push({ tool_name: event.data?.tool_name || "", tool_args: event.data?.tool_args });
            setToolCalls([...tcs]);
            break;
          case "tool_result":
            const last = tcs[tcs.length - 1];
            if (last) { last.result = event.data?.result; last.success = event.data?.success ?? true; }
            setToolCalls([...tcs]);
            break;
          case "notice": setSkillNotice(event.data as SkillNoticeData); break;
          case "card": {
            if (event.data?.name === "get_stock_quote") cards.push({ type: "stock", data: event.data.data?.quote || event.data.data });
            else if (event.data?.name === "get_fund_info") cards.push({ type: "fund", data: event.data.data?.fund_info || event.data.data });
            break;
          }
          case "plan_created": currentPlan = event.data as PlanData; break;
          case "plan_step_update": {
            if (currentPlan) {
              const step = currentPlan.steps.find(s => s.step === event.data?.step);
              if (step) { step.status = event.data?.status ?? step.status; if (event.data?.error) step.error = event.data.error; }
            }
            break;
          }
          case "worker_started": currentWorkers = [...currentWorkers, { worker_id: event.data?.worker_id, task: event.data?.task || "", status: "running" as const }]; break;
          case "worker_done": {
            const w = currentWorkers.find(w => w.worker_id === event.data?.worker_id);
            if (w) { w.status = event.data?.status === "failed" ? "failed" : "completed"; if (event.data?.result_preview) w.result_preview = event.data.result_preview; }
            break;
          }
          case "file_download": if (event.data?.file_id) fileDownloads.push(event.data as FileDownloadInfo); break;
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
          case "done": break;
          case "error": fullContent += `\n\n❌ 错误: ${event.data?.message || "未知错误"}`; break;
        }
        flushAssistant(fullContent, cards, fileDownloads, currentPlan, currentWorkers);
      }
    } catch (err) {
      fullContent += `\n\n❌ 请求失败: ${err instanceof Error ? err.message : "未知错误"}`;
    } finally {
      setStreaming(false);
      setStreamStatus("idle");
      scrollToBottom();
      refreshConversations(wasNew);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div ref={scrollRef} className="chat-area" style={{ flex: 1 }}>
        <div className="chat-inner">
          {messages.length === 0 && <WelcomeScreen onSend={(t) => handleSend(t)} />}
          {messages.map((msg, idx) => {
            const isLast = isStreaming && idx === messages.length - 1;
            return (
              <div key={msg.id}>
                {msg.role === "assistant" && idx === messages.length - 1 && skillNotice && <SkillNoticeCard notice={skillNotice} />}
                {msg.role === "assistant" && msg.plan && <PlanCard plan={msg.plan} />}
                {msg.role === "assistant" && msg.workers && msg.workers.length > 0 && <WorkersCard workers={msg.workers} />}
                {msg.cards?.map((card, ci) => (
                  <pre key={ci} style={{ fontSize: 12, background: "var(--surface-sunken)", padding: 8, borderRadius: 6, color: "var(--text-secondary)" }}>
                    {JSON.stringify(card.data, null, 2)}
                  </pre>
                ))}
                <MessageBubble msg={msg} isStreaming={!!isLast} toolCalls={isLast ? toolCalls : undefined} />
                {msg.role === "assistant" && msg.fileDownloads?.map((fd) => (
                  <div key={fd.file_id} style={{ marginTop: 4 }}>
                    <a href={fd.download_url} style={{ fontSize: 13, color: "var(--brand)" }}>{fd.filename}</a>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
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
