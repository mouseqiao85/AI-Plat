import { useState, memo, useMemo } from "react";
import { ToolOutlined, DownOutlined, RightOutlined, CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined } from "@ant-design/icons";
import type { ToolCallEntry } from "../types";

const RESULT_TRUNCATE_CHARS = 2000;

/** Render tool result with truncation for large outputs */
const TruncatedResult = ({ result }: { result: unknown }) => {
  const [showFull, setShowFull] = useState(false);
  const text = useMemo(() => typeof result === "string" ? result : JSON.stringify(result, null, 2), [result]);

  if (text.length <= RESULT_TRUNCATE_CHARS || showFull) {
    return (
      <div>
        <pre>{text}</pre>
        {showFull && text.length > RESULT_TRUNCATE_CHARS && (
          <button onClick={() => setShowFull(false)} style={{ fontSize: 11, color: "var(--brand)", background: "none", border: "none", cursor: "pointer", padding: "4px 0" }}>
            收起
          </button>
        )}
      </div>
    );
  }

  return (
    <div>
      <pre>{text.slice(0, RESULT_TRUNCATE_CHARS)}</pre>
      <button onClick={() => setShowFull(true)} style={{ fontSize: 11, color: "var(--brand)", background: "none", border: "none", cursor: "pointer", padding: "4px 0" }}>
        …展开完整结果 ({(text.length / 1024).toFixed(1)} KB)
      </button>
    </div>
  );
};

interface Props {
  calls: ToolCallEntry[];
}

const ToolCallCard = memo(({ calls }: Props) => {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  if (!calls || calls.length === 0) return null;

  return (
    <div>
      {calls.map((call, idx) => {
        const isOpen = expanded[idx];
        const statusIcon = call.status === "completed"
          ? <CheckCircleOutlined style={{ color: "var(--success)", fontSize: 13 }} />
          : call.status === "failed"
            ? <CloseCircleOutlined style={{ color: "var(--error)", fontSize: 13 }} />
            : <LoadingOutlined style={{ color: "var(--brand)", fontSize: 13 }} />;

        const elapsed = call.started_at
          ? ((call.completed_at ?? Date.now()) - call.started_at) / 1000
          : 0;
        const timeStr = call.status === "running"
          ? `运行中 (${elapsed.toFixed(1)}s)`
          : call.status === "completed"
            ? `完成 (${elapsed.toFixed(1)}s)`
            : call.status === "failed"
              ? `失败 (${elapsed.toFixed(1)}s)`
              : "";

        return (
          <div key={idx} className="tool-call-card">
            <div className="tool-call-header" onClick={() => setExpanded(prev => ({ ...prev, [idx]: !isOpen }))}>
              {isOpen ? <DownOutlined style={{ fontSize: 10 }} /> : <RightOutlined style={{ fontSize: 10 }} />}
              <ToolOutlined />
              <span>{call.tool_name}</span>
              <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-tertiary)" }}>
                <span>{timeStr}</span>
                {statusIcon}
              </span>
            </div>
            {isOpen && (
              <div className="tool-call-body">
                {call.tool_args && Object.keys(call.tool_args).length > 0 && (
                  <div style={{ marginBottom: 6 }}>
                    <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 11, color: "var(--text-tertiary)" }}>参数</div>
                    <pre>{JSON.stringify(call.tool_args, null, 2)}</pre>
                  </div>
                )}
                {call.result !== undefined && (
                  <div>
                    <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 11, color: "var(--text-tertiary)" }}>结果</div>
                    <TruncatedResult result={call.result} />
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
});

ToolCallCard.displayName = "ToolCallCard";
export default ToolCallCard;
