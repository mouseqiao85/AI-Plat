import type { FileDownloadInfo } from "../types";

const FILE_EXTENSIONS = ["ppt", "pptx", "html", "htm", "md", "markdown", "doc", "docx", "xls", "xlsx", "csv"];

const CONTENT_TYPE_BY_EXT: Record<string, string> = {
  ppt: "application/vnd.ms-powerpoint",
  pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  html: "text/html",
  htm: "text/html",
  md: "text/markdown",
  markdown: "text/markdown",
  doc: "application/msword",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  xls: "application/vnd.ms-excel",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  csv: "text/csv",
};

const FILE_NAME_RE = /([\w\u4e00-\u9fff .()[\]-]+?\.(?:pptx?|html?|md|markdown|docx?|xlsx?|csv))/i;

export function fileOutputExtension(filename?: string) {
  const ext = (filename || "").split(".").pop()?.toLowerCase() || "";
  return FILE_EXTENSIONS.includes(ext) ? ext : "";
}

export function isDownloadableOutputContent(content?: string) {
  const text = (content || "").trim();
  if (!text) return false;
  if (/^已生成文件[:：]\s*.+\.(?:pptx?|html?|md|markdown|docx?|xlsx?|csv)\s*$/i.test(text)) return true;
  if (text.length < 220) return false;
  if (/^\s*<!doctype html|<html[\s>]/i.test(text)) return true;
  if (/^```(?:html|markdown|md|csv)\b/i.test(text)) return true;
  if (/^\s*\|.+\|\s*$/m.test(text) && /\.(?:xlsx?|csv)\b/i.test(text)) return true;
  return /(?:输出|生成|导出|保存|下载).{0,20}(?:pptx?|html?|markdown|md|docx?|word|xlsx?|excel|csv|文件)/i.test(text);
}

export function inferredOutputFilename(content: string, fallback = "generated-output.md") {
  const text = (content || "").trim();
  const direct = /^已生成文件[:：]\s*(.+)$/i.exec(text)?.[1]?.trim();
  const match = direct || FILE_NAME_RE.exec(text)?.[1]?.trim();
  if (match) return match.replace(/[\\/:"*?<>|]+/g, "-");
  if (/^\s*<!doctype html|<html[\s>]/i.test(text)) return "generated-output.html";
  if (/^\s*\|.+\|\s*$/m.test(text)) return "generated-output.xlsx";
  return fallback;
}

export function inferredFileDownload(content: string): FileDownloadInfo {
  const filename = inferredOutputFilename(content);
  const ext = fileOutputExtension(filename) || "md";
  return {
    file_id: `inline-${filename}`,
    filename,
    content_type: CONTENT_TYPE_BY_EXT[ext] || "application/octet-stream",
    size: new Blob([content]).size,
    download_url: URL.createObjectURL(new Blob([content], { type: CONTENT_TYPE_BY_EXT[ext] || "text/plain" })),
  };
}

export function fileKindLabel(info: Pick<FileDownloadInfo, "filename" | "content_type">) {
  const ext = fileOutputExtension(info.filename);
  if (ext) return ext === "md" ? "Markdown" : ext.toUpperCase();
  if (info.content_type === "text/html") return "HTML";
  if (info.content_type === "text/markdown") return "Markdown";
  return "文件";
}
