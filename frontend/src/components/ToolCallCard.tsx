import { useState, memo } from "react";
import { ToolOutlined, DownOutlined, RightOutlined, CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined } from "@ant-design/icons";

interface ToolCall {
  tool_name: string;
  tool_args?: Record<string, unknown>;
  result?: unknown;
  success?: boolean;
}

interface Props {
  calls: ToolCall[];
}

const ToolCallCard = memo(({ calls }: Props) => {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  const toggleExpand = (idx: number) => {
    setExpanded((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  if (!calls || calls.length === 0) return null;

  return (
    <div>
      {calls.map((call, idx) => {
        const isOpen = expanded[idx];
        const isSuccess = call.success ?? true;
        const statusIcon = call.result !== undefined
          ? isSuccess
            ? <CheckCircleOutlined style={{ color: "var(--success)", fontSize: 13 }} />
            : <CloseCircleOutlined style={{ color: "var(--error)", fontSize: 13 }} />
          : <LoadingOutlined style={{ color: "var(--brand)", fontSize: 13 }} />;

        return (
          <div key={idx} className="tool-call-card">
            <div className="tool-call-header" onClick={() => toggleExpand(idx)}>
              {isOpen ? <DownOutlined style={{ fontSize: 10 }} /> : <RightOutlined style={{ fontSize: 10 }} />}
              <ToolOutlined />
              <span>{call.tool_name}</span>
              <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4 }}>
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
                    <pre>{typeof call.result === "string" ? call.result : JSON.stringify(call.result, null, 2)}</pre>
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
