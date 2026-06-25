import { memo } from "react";
import { Tag } from "antd";
import { WarningOutlined, CheckCircleOutlined, InfoCircleOutlined } from "@ant-design/icons";
import type { SkillNoticeData } from "../types";

const SkillNoticeCard = memo(({ notice }: { notice: SkillNoticeData }) => {
  const hasMissing = notice.missing?.length > 0;
  return (
    <div style={{ margin: "0 0 10px", padding: "10px 14px", borderRadius: 8,
      border: `1px solid ${hasMissing ? "#faad14" : "#91d5ff"}`,
      background: `var(--bg-card, ${hasMissing ? "#fffbe6" : "#e6f7ff"})`,
      fontSize: 12.5, lineHeight: 1.7, color: "var(--text-secondary)" }}>
      <div style={{ fontWeight: 600, marginBottom: 4, display: "flex", alignItems: "center", gap: 6 }}>
        {hasMissing ? <WarningOutlined style={{ color: "#faad14" }} /> : <CheckCircleOutlined style={{ color: "#52c41a" }} />}
        <span>技能依赖提示 · {notice.skill}</span>
      </div>
      {notice.tools?.length > 0 && <div><InfoCircleOutlined style={{ color: "#1677ff", marginRight: 5 }} /><strong>工具：</strong>{notice.tools.map(t => <Tag key={t} style={{ fontSize: 11 }}>{t}</Tag>)}</div>}
      {notice.requires?.length > 0 && <div style={{ marginTop: 4 }}><strong>必填配置：</strong>{notice.requires.map(r => <Tag key={r} color={notice.missing?.includes(r) ? "warning" : "success"} style={{ fontSize: 11 }}>{r}{notice.missing?.includes(r) ? " ⚠" : " ✓"}</Tag>)}</div>}
      {notice.dependencies?.length > 0 && <div style={{ marginTop: 4 }}><strong>依赖：</strong>{notice.dependencies.join("、")}</div>}
    </div>
  );
});
SkillNoticeCard.displayName = "SkillNoticeCard";
export default SkillNoticeCard;
