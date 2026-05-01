import { Tag } from "antd";
import { RiseOutlined, FallOutlined } from "@ant-design/icons";

interface FundCardProps {
  data: Record<string, unknown>;
}

export default function FundCard({ data }: FundCardProps) {
  const nav = Number(data.nav ?? 0);
  const changePct = Number(data.change_percent ?? 0);
  const isUp = changePct >= 0;

  return (
    <div className="fin-card animate-slide-up">
      <div className="fin-card-header">
        <div>
          <span className="fin-card-title">{String(data.name)}</span>
          <span className="fin-card-code">{String(data.code)}</span>
        </div>
        {data.fund_type != null && (
          <Tag style={{ 
            background: "var(--brand-light)", 
            border: "none",
            color: "var(--brand-primary)",
            fontSize: 11,
            fontWeight: 500,
          }}>
            {String(data.fund_type)}
          </Tag>
        )}
      </div>
      
      <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginTop: 4 }}>
        <span className={`fin-card-price ${isUp ? "up" : "down"}`}>
          {nav.toFixed(4)}
        </span>
        <span className={`fin-card-change ${isUp ? "up" : "down"}`}>
          {isUp ? "+" : ""}{changePct.toFixed(2)}%
          {isUp ? <RiseOutlined style={{ marginLeft: 4, fontSize: 12 }} /> : <FallOutlined style={{ marginLeft: 4, fontSize: 12 }} />}
        </span>
      </div>
      
      <div className="fin-card-grid fin-card-grid-2">
        <div className="fin-card-stat">
          <div className="fin-card-stat-label">累计净值</div>
          <div className="fin-card-stat-value">{Number(data.acc_nav ?? 0).toFixed(4)}</div>
        </div>
        <div className="fin-card-stat">
          <div className="fin-card-stat-label">基金经理</div>
          <div className="fin-card-stat-value">{data.manager ? String(data.manager) : "-"}</div>
        </div>
        <div className="fin-card-stat">
          <div className="fin-card-stat-label">规模</div>
          <div className="fin-card-stat-value">{data.size ? `${(Number(data.size) / 1e8).toFixed(2)}亿` : "-"}</div>
        </div>
        <div className="fin-card-stat">
          <div className="fin-card-stat-label">成立日期</div>
          <div className="fin-card-stat-value">{data.establish_date ? String(data.establish_date) : "-"}</div>
        </div>
      </div>
    </div>
  );
}
