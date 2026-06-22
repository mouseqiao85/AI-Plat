import { lazy, memo, Suspense } from "react";
import { Spin } from "antd";
import { RobotOutlined, UserOutlined } from "@ant-design/icons";

import type { ChatMessage, ToolCallEntry } from "../types";
import ToolCallCard from "./ToolCallCard";
import { inferredOutputFilename, isDownloadableOutputContent } from "../utils/fileOutput";

const MarkdownContent = lazy(() => import("./MarkdownContent"));

/** Lightweight streaming renderer — avoids expensive full Markdown parsing
 *  while content is actively changing every animation frame.
 *  Uses a simple whitespace-preserving div instead of ReactMarkdown. */
const StreamingContent = memo(({ content }: { content: string }) => {
  if (!content) return null;
  return (
    <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", lineHeight: 1.6, fontFamily: "inherit" }}>
      {content}
    </div>
  );
});
StreamingContent.displayName = "StreamingContent";

interface Props {
  msg: ChatMessage;
  isStreaming: boolean;
  toolCalls?: ToolCallEntry[];
}

const MessageBubble = memo(({ msg, isStreaming, toolCalls }: Props) => {
  const isUser = msg.role === "user";
  // Use live toolCalls prop during streaming, msg.toolCalls from history after done
  const displayToolCalls = toolCalls ?? msg.toolCalls;
  const hideFileBody = !isUser && !isStreaming && isDownloadableOutputContent(msg.content);
  const displayContent = hideFileBody ? `已生成文件：${inferredOutputFilename(msg.content)}` : msg.content;
  return (
    <div className={`msg-row${isUser ? " user" : ""}`}>
      <div className={`msg-avatar ${isUser ? "user" : "bot"}`}>
        {isUser ? <UserOutlined style={{ fontSize: 15 }} /> : <RobotOutlined style={{ fontSize: 15 }} />}
      </div>
      <div className="msg-body">
        {displayToolCalls && displayToolCalls.length > 0 && <ToolCallCard calls={displayToolCalls} />}
        {msg.plan && (() => {
          const steps = msg.plan.steps || [];
          return (
            <div className="tool-call-card" style={{ borderColor: "var(--brand)", background: "var(--brand-light)" }}>
              <div className="tool-call-header" style={{ color: "var(--brand)" }}>
                <ThunderboltIcon /> 执行计划 ({steps.filter((s: { status: string }) => s.status === "completed").length}/{steps.length})
              </div>
            </div>
          );
        })()}
        {(displayContent || (isStreaming && !isUser)) && (
          <div className={`bubble ${isUser ? "user" : "bot"}`}>
            {isUser ? msg.content : (
              isStreaming
                ? <StreamingContent content={displayContent} />
                : <Suspense fallback={<StreamingContent content={displayContent} />}><MarkdownContent content={displayContent} /></Suspense>
            )}
            {isStreaming && !isUser && !msg.content && <Spin size="small" />}
          </div>
        )}
      </div>
    </div>
  );
}, (prev, next) => {
  // Non-streaming messages: only re-render if id or content changed
  if (!prev.isStreaming && !next.isStreaming) {
    return prev.msg.id === next.msg.id && prev.msg.content === next.msg.content;
  }
  // Streaming: always re-render (content is actively changing)
  return false;
});

const ThunderboltIcon = () => (
  <svg viewBox="64 64 896 896" width="1em" height="1em" fill="currentColor">
    <path d="M848 359.3H627.7L825.8 109c4.1-5.3.4-13-6.3-13H436c-2.8 0-5.5 1.5-6.9 4L170 547.5c-3.1 5.3.7 12 6.9 12h174.4l-89.4 357.6c-1.9 7.8 7.5 13.3 13.3 7.7L853.5 373c5.2-4.9 1.7-13.7-5.5-13.7z"/>
  </svg>
);

MessageBubble.displayName = "MessageBubble";
export default MessageBubble;
