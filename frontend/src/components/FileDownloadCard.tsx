import { memo } from "react";
import { FileTextOutlined, DownloadOutlined } from "@ant-design/icons";
import type { FileDownloadInfo } from "../types";

/** Format bytes to human-readable size */
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const FileDownloadCard = memo(({ info }: { info: FileDownloadInfo }) => {
  const isHtml = info.content_type === "text/html";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 14px",
        borderRadius: "var(--radius-sm, 8px)",
        border: "1px solid var(--border-subtle, #e8e8e8)",
        background: "var(--surface-sunken, #f5f5f5)",
        margin: "6px 0",
        cursor: "default",
      }}
    >
      <div style={{
        width: 36, height: 36, borderRadius: 8,
        background: isHtml ? "#e6f7ff" : "#f6ffed",
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0,
      }}>
        <FileTextOutlined style={{ fontSize: 18, color: isHtml ? "#1677ff" : "#52c41a" }} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {info.filename}
        </div>
        <div style={{ fontSize: 11, color: "#8c8c8c", marginTop: 2 }}>
          {formatSize(info.size)} · {isHtml ? "HTML" : info.content_type === "text/markdown" ? "Markdown" : "文本"}
        </div>
      </div>
      <a
        href={info.download_url}
        download={info.filename}
        style={{
          display: "flex", alignItems: "center", gap: 4,
          padding: "6px 12px", borderRadius: 6,
          background: "var(--brand-primary, #1677ff)",
          color: "#fff", fontSize: 12, fontWeight: 500,
          textDecoration: "none", flexShrink: 0,
          transition: "opacity 0.2s",
        }}
        onMouseEnter={(e) => { (e.currentTarget.style.opacity = "0.85"); }}
        onMouseLeave={(e) => { (e.currentTarget.style.opacity = "1"); }}
      >
        <DownloadOutlined style={{ fontSize: 13 }} />
        下载
      </a>
    </div>
  );
});

export default FileDownloadCard;
