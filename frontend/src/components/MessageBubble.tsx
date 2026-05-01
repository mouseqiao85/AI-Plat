import { useState, memo } from "react";
import { Spin } from "antd";
import { RobotOutlined, UserOutlined, CopyOutlined, CheckOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight, oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";
import typescript from "react-syntax-highlighter/dist/esm/languages/prism/typescript";

SyntaxHighlighter.registerLanguage("bash", bash);
SyntaxHighlighter.registerLanguage("python", python);
SyntaxHighlighter.registerLanguage("json", json);
SyntaxHighlighter.registerLanguage("typescript", typescript);

import type { ChatMessage } from "../types";
import ToolCallCard from "./ToolCallCard";

const CopyButton = ({ code }: { code: string }) => {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(code).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); });
      }}
      title="复制代码"
      style={{ position: "absolute", top: 8, right: 8, background: "none", border: "none", cursor: "pointer", color: copied ? "#52c41a" : "var(--text-tertiary)", fontSize: 13, padding: "2px 6px", borderRadius: 4, transition: "color 0.2s" }}
    >
      {copied ? <CheckOutlined /> : <CopyOutlined />}
    </button>
  );
};

const MsgContent = memo(({ content }: { content: string }) => {
  if (!content) return null;
  const normalized = content.replace(
    /<img\s[^>]*?src=["']([^"']+)["'][^>]*?(?:alt=["']([^"']*?)["'])?[^>]*?\/?>/gi,
    (_, src: string, alt = "") => `![${alt}](${src})`
  );

  const isDark = typeof document !== "undefined" && document.documentElement.getAttribute("data-theme") === "dark";
  const codeStyle = isDark ? oneDark : oneLight;

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const codeStr = String(children).replace(/\n$/, "");
          const isBlock = !!match || codeStr.includes("\n");
          if (isBlock) {
            return (
              <div style={{ position: "relative", margin: "4px 0" }}>
                <SyntaxHighlighter style={codeStyle} language={match?.[1] || "text"} PreTag="div"
                  customStyle={{ borderRadius: 8, border: "1px solid var(--border-subtle, #e8e8e8)", fontSize: 12.5, lineHeight: 1.65, margin: 0, padding: "12px 16px", paddingRight: 40 }}
                >{codeStr}</SyntaxHighlighter>
                <CopyButton code={codeStr} />
              </div>
            );
          }
          return <code style={{ background: "var(--surface-sunken, #f5f5f5)", borderRadius: 4, padding: "1px 5px", fontSize: "0.88em", fontFamily: '"SF Mono","Fira Code",monospace', color: "var(--brand-primary, #1677ff)" }} {...props}>{children}</code>;
        },
        table({ children }) { return <div style={{ overflowX: "auto", margin: "4px 0" }}><table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>{children}</table></div>; },
        thead({ children }) { return <thead style={{ background: "var(--surface-sunken, #f5f5f5)" }}>{children}</thead>; },
        th({ children }) { return <th style={{ border: "1px solid var(--border-subtle, #e8e8e8)", padding: "6px 12px", textAlign: "left", fontWeight: 600 }}>{children}</th>; },
        td({ children }) { return <td style={{ border: "1px solid var(--border-subtle, #e8e8e8)", padding: "6px 12px" }}>{children}</td>; },
        p({ children }) { return <p style={{ margin: "2px 0", lineHeight: 1.6 }}>{children}</p>; },
        a({ href, children }) { return <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: "var(--brand)", textDecoration: "underline" }}>{children}</a>; },
        blockquote({ children }) { return <blockquote style={{ borderLeft: "3px solid var(--brand)", margin: "5px 0", padding: "3px 10px", color: "var(--text-secondary)", background: "var(--surface-sunken)", borderRadius: "0 4px 4px 0" }}>{children}</blockquote>; },
        hr() { return <hr style={{ border: "none", borderTop: "1px solid var(--border-subtle)", margin: "6px 0" }} />; },
        img({ src, alt }) { return <img src={src} alt={alt} style={{ maxWidth: "100%", borderRadius: 6, margin: "4px 0" }} />; },
      }}
    >{normalized}</ReactMarkdown>
  );
});

MsgContent.displayName = "MsgContent";

interface Props {
  msg: ChatMessage;
  isStreaming: boolean;
  toolCalls?: Array<{ tool_name: string; tool_args?: Record<string, unknown>; result?: unknown; success?: boolean }>;
}

const MessageBubble = memo(({ msg, isStreaming, toolCalls }: Props) => {
  const isUser = msg.role === "user";
  return (
    <div className={`msg-row${isUser ? " user" : ""}`}>
      <div className={`msg-avatar ${isUser ? "user" : "bot"}`}>
        {isUser ? <UserOutlined style={{ fontSize: 15 }} /> : <RobotOutlined style={{ fontSize: 15 }} />}
      </div>
      <div className="msg-body">
        {msg.plan && (
          <div className="tool-call-card" style={{ borderColor: "var(--brand)", background: "var(--brand-light)" }}>
            <div className="tool-call-header" style={{ color: "var(--brand)" }}>
              <ThunderboltIcon /> 执行计划 ({msg.plan.steps.filter((s: { status: string }) => s.status === "completed").length}/{msg.plan.steps.length})
            </div>
          </div>
        )}
        {toolCalls && toolCalls.length > 0 && <ToolCallCard calls={toolCalls} />}
        {(msg.content || (isStreaming && !isUser)) && (
          <div className={`bubble ${isUser ? "user" : "bot"}${isStreaming && !isUser && !msg.content ? "" : ""}`}>
            {isUser ? msg.content : <MsgContent content={msg.content} />}
            {isStreaming && !isUser && !msg.content && <Spin size="small" />}
          </div>
        )}
      </div>
    </div>
  );
});

const ThunderboltIcon = () => (
  <svg viewBox="64 64 896 896" width="1em" height="1em" fill="currentColor">
    <path d="M848 359.3H627.7L825.8 109c4.1-5.3.4-13-6.3-13H436c-2.8 0-5.5 1.5-6.9 4L170 547.5c-3.1 5.3.7 12 6.9 12h174.4l-89.4 357.6c-1.9 7.8 7.5 13.3 13.3 7.7L853.5 373c5.2-4.9 1.7-13.7-5.5-13.7z"/>
  </svg>
);

MessageBubble.displayName = "MessageBubble";
export default MessageBubble;
