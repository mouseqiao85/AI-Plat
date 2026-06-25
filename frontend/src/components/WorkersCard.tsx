import { memo } from "react";
import { CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined, ExperimentOutlined } from "@ant-design/icons";
import type { WorkerInfo } from "../types";

const WorkersCard = memo(({ workers }: { workers: WorkerInfo[] }) => (
  <div className="tool-call-card">
    <div className="tool-call-header">
      <ExperimentOutlined style={{ color: "var(--brand)" }} />
      <span>子任务</span>
    </div>
    <div className="tool-call-body">
      {workers.map((w) => {
        const icon = w.status === "completed" ? <CheckCircleOutlined style={{ color: "var(--success)" }} />
          : w.status === "failed" ? <CloseCircleOutlined style={{ color: "var(--error)" }} />
          : <LoadingOutlined style={{ color: "var(--brand)" }} />;
        return (
          <div key={w.worker_id} style={{ display: "flex", alignItems: "center", gap: 6, padding: "2px 0", fontSize: 12.5 }}>
            {icon}<span>{w.task}</span>
            {w.result_preview && <span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>{w.result_preview}</span>}
          </div>
        );
      })}
    </div>
  </div>
));
WorkersCard.displayName = "WorkersCard";
export default WorkersCard;
