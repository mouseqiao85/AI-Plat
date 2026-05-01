import { memo } from "react";
import { CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined, ClockCircleOutlined } from "@ant-design/icons";
import type { PlanData } from "../types";

const icons: Record<string, React.ReactNode> = {
  pending: <ClockCircleOutlined style={{ color: "var(--text-tertiary)" }} />,
  running: <LoadingOutlined style={{ color: "var(--brand)" }} />,
  completed: <CheckCircleOutlined style={{ color: "var(--success)" }} />,
  failed: <CloseCircleOutlined style={{ color: "var(--error)" }} />,
};

const PlanCard = memo(({ plan }: { plan: PlanData }) => (
  <div className="tool-call-card" style={{ borderColor: "var(--brand)", background: "var(--brand-light)" }}>
    <div className="tool-call-header" style={{ color: "var(--brand)", alignItems: "center" }}>
      <svg viewBox="64 64 896 896" width="14" height="14" fill="currentColor"><path d="M848 359.3H627.7L825.8 109c4.1-5.3.4-13-6.3-13H436c-2.8 0-5.5 1.5-6.9 4L170 547.5c-3.1 5.3.7 12 6.9 12h174.4l-89.4 357.6c-1.9 7.8 7.5 13.3 13.3 7.7L853.5 373c5.2-4.9 1.7-13.7-5.5-13.7z"/></svg>
      <span>执行计划</span>
      <span style={{ fontWeight: 400, fontSize: 11, marginLeft: "auto" }}>
        {plan.steps.filter(s => s.status === "completed").length}/{plan.steps.length} 完成
      </span>
    </div>
    <div className="tool-call-body">
      {plan.steps.map((step) => (
        <div key={step.step} style={{ display: "flex", alignItems: "center", gap: 6, padding: "2px 0", fontSize: 12.5 }}>
          {icons[step.status] || icons.pending}
          <span>{step.description || step.action}</span>
          {step.error && <span style={{ color: "var(--error)", fontSize: 11 }}>{step.error}</span>}
        </div>
      ))}
    </div>
  </div>
));
PlanCard.displayName = "PlanCard";
export default PlanCard;
