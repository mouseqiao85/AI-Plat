import { RiseOutlined, FallOutlined } from "@ant-design/icons";

interface StockCardProps {
  data: Record<string, unknown>;
}

/** Safe number parse — returns 0 for NaN instead of propagating NaN.toFixed() */
function safeNum(v: unknown): number {
  const n = Number(v ?? 0);
  return Number.isFinite(n) ? n : 0;
}

export default function StockCard({ data }: StockCardProps) {
  const price = safeNum(data.price);
  const changePct = safeNum(data.change_percent);
  const isUp = changePct >= 0;

  return (
    <div className="fin-card animate-slide-up">
      <div className="fin-card-header">
        <div>
          <span className="fin-card-title">{String(data.name)}</span>
          <span className="fin-card-code">{String(data.code)}</span>
        </div>
        <span className={`fin-card-badge ${isUp ? "up" : "down"}`}>
          {isUp ? <RiseOutlined /> : <FallOutlined />}
          <span style={{ marginLeft: 4 }}>
            {isUp ? "+" : ""}{changePct.toFixed(2)}%
          </span>
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginTop: 4 }}>
        <span className={`fin-card-price ${isUp ? "up" : "down"}`}>
          ¥{price.toFixed(2)}
        </span>
      </div>

      <div className="fin-card-grid">
        <div className="fin-card-stat">
          <div className="fin-card-stat-label">开盘</div>
          <div className="fin-card-stat-value">{safeNum(data.open).toFixed(2)}</div>
        </div>
        <div className="fin-card-stat">
          <div className="fin-card-stat-label">最高</div>
          <div className="fin-card-stat-value">{safeNum(data.high).toFixed(2)}</div>
        </div>
        <div className="fin-card-stat">
          <div className="fin-card-stat-label">最低</div>
          <div className="fin-card-stat-value">{safeNum(data.low).toFixed(2)}</div>
        </div>
        <div className="fin-card-stat">
          <div className="fin-card-stat-label">成交量</div>
          <div className="fin-card-stat-value">{safeNum(data.volume).toLocaleString()}</div>
        </div>
        <div className="fin-card-stat">
          <div className="fin-card-stat-label">成交额</div>
          <div className="fin-card-stat-value">{(safeNum(data.turnover) / 1e8).toFixed(2)}亿</div>
        </div>
        <div className="fin-card-stat">
          <div className="fin-card-stat-label">市盈率</div>
          <div className="fin-card-stat-value">{data.pe_ratio ? safeNum(data.pe_ratio).toFixed(1) : "-"}</div>
        </div>
      </div>
    </div>
  );
}
