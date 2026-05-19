import { memo, useState } from "react";
import { CopyOutlined, CheckOutlined } from "@ant-design/icons";
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

const MarkdownContent = memo(({ content }: { content: string }) => {
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

MarkdownContent.displayName = "MarkdownContent";
export default MarkdownContent;
