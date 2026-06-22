import { useState, useRef, memo } from "react";
import { Tooltip, Select } from "antd";
import { ExperimentOutlined, PlusOutlined, FileImageOutlined, CloseOutlined, ArrowUpOutlined, StopOutlined, SearchOutlined } from "@ant-design/icons";
import { useAppStore } from "../stores/appStore";
import { cancelStream } from "../services/api";

const ACCEPT = ".txt,.md,.csv,.pdf,.png,.jpg,.jpeg,.gif,.webp";

interface Props {
  onSend: (text?: string) => void;
  onSmartSearch?: (text?: string) => void;
}

const InputArea = memo(({ onSend, onSmartSearch }: Props) => {
  const {
    isStreaming, token, selectedSkill, user,
    providers, selectedProviderId, setSelectedProviderId,
    selectedModel, setSelectedModel,
  } = useAppStore();

  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<Array<{ uid: string; name: string }>>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const currentProvider = providers.find((p) => p.id === selectedProviderId) || providers[0];
  const effectiveModel = selectedModel || currentProvider?.models?.[0] || null;

  const adjustHeight = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  };

  const buildMessage = () => {
    const msg = input.trim();
    if (!msg) return "";
    let fullMsg = msg;
    if (attachments.length > 0) {
      fullMsg = attachments.map((f) => `[附件: ${f.name}]`).join(" ") + "\n" + msg;
    }
    return fullMsg;
  };

  const clearComposer = () => {
    setInput("");
    setAttachments([]);
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleSend = () => {
    const fullMsg = buildMessage();
    if (!fullMsg || isStreaming || !token) return;
    clearComposer();
    onSend(fullMsg);
  };

  const handleSmartSearch = () => {
    const fullMsg = buildMessage();
    if (!fullMsg || isStreaming || !token) return;
    clearComposer();
    onSmartSearch?.(fullMsg);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const newFiles = files.map((f, i) => ({ uid: `${Date.now()}-${i}`, name: f.name }));
    setAttachments((prev) => [...prev, ...newFiles].slice(0, 5));
    e.target.value = "";
  };

  const canSend = (input.trim().length > 0 || attachments.length > 0) && !isStreaming && !!token;

  return (
    <div className="input-zone">
      <div className="input-zone-inner">
        {selectedSkill && (
          <div style={{ marginBottom: 10 }}>
            <span className="skill-badge"><ExperimentOutlined style={{ fontSize: 12 }} />技能：{selectedSkill}</span>
          </div>
        )}

        {providers.length > 0 && user?.role === "admin" && (
          <div style={{ marginBottom: 10, display: "flex", gap: 8, alignItems: "center" }}>
            <Select size="small" value={selectedProviderId}
              onChange={(id) => { setSelectedProviderId(id); setSelectedModel(null); }}
              style={{ minWidth: 110 }}
              options={providers.map((p) => ({ value: p.id, label: p.name }))}
            />
            {currentProvider && currentProvider.models.length > 1 && (
              <Select size="small" value={effectiveModel || currentProvider.models[0]}
                onChange={(m) => setSelectedModel(m)} style={{ minWidth: 160 }}
                options={currentProvider.models.map((m) => ({ value: m, label: m }))}
              />
            )}
          </div>
        )}

        <div className="input-box">
          {attachments.length > 0 && (
            <div className="attach-list">
              {attachments.map((f) => (
                <span key={f.uid} className="attach-chip">
                  <FileImageOutlined style={{ fontSize: 12 }} />{f.name}
                  <CloseOutlined className="attach-chip-remove" style={{ cursor: "pointer" }}
                    onClick={() => setAttachments((prev) => prev.filter((x) => x.uid !== f.uid))} />
                </span>
              ))}
            </div>
          )}
          <textarea ref={textareaRef} className="input-textarea" value={input}
            placeholder="请描述任务，或使用 / 调用技能" disabled={isStreaming}
            onChange={(e) => { setInput(e.target.value); adjustHeight(); }}
            onKeyDown={handleKeyDown} rows={1}
          />
          <div className="input-footer">
            <div className="input-footer-left">
              <Tooltip title="上传文件或图片">
                <button className="btn-attach" onClick={() => fileInputRef.current?.click()}><PlusOutlined style={{ fontSize: 14 }} /></button>
              </Tooltip>
              <span className="char-hint">{input.length > 0 ? `${input.length} 字` : "Enter 发送 · Shift+Enter 换行"}</span>
            </div>
            <div className="input-footer-right">
              {isStreaming ? (
                <button className="btn-stop" onClick={() => {
                  cancelStream();
                  const { setStreaming } = useAppStore.getState();
                  setStreaming(false);
                }}><StopOutlined style={{ fontSize: 13 }} />停止</button>
              ) : (
                <>
                  <button className="btn-smart-search" disabled={!canSend} onClick={handleSmartSearch}>
                    <SearchOutlined style={{ fontSize: 14 }} />智能搜索
                  </button>
                  <button className="btn-send" disabled={!canSend} onClick={handleSend}>
                    <ArrowUpOutlined style={{ fontSize: 15 }} />发送
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
        <input ref={fileInputRef} type="file" multiple accept={ACCEPT} style={{ display: "none" }} onChange={handleFileChange} />
      </div>
    </div>
  );
});

InputArea.displayName = "InputArea";
export default InputArea;
