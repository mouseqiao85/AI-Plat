import { memo } from "react";
import { RobotOutlined, SearchOutlined, BulbOutlined, MessageOutlined, ThunderboltOutlined, CodeOutlined, BarChartOutlined, FileTextOutlined } from "@ant-design/icons";

const SUGGESTIONS = [
  { icon: <SearchOutlined />, text: "帮我搜索一下最新的 AI 资讯" },
  { icon: <BulbOutlined />, text: "解释一下什么是大语言模型" },
  { icon: <MessageOutlined />, text: "帮我写一段产品介绍文案" },
  { icon: <ThunderboltOutlined />, text: "如何提升代码的可读性？" },
];

const FEATURES = [
  { icon: <SearchOutlined />, cls: "search", label: "智能搜索" },
  { icon: <CodeOutlined />, cls: "code", label: "代码生成" },
  { icon: <BarChartOutlined />, cls: "chart", label: "数据分析" },
  { icon: <FileTextOutlined />, cls: "doc", label: "文档写作" },
];

interface Props {
  onSend: (text: string) => void;
}

const WelcomeScreen = memo(({ onSend }: Props) => (
  <div className="welcome">
    <div className="welcome-icon"><RobotOutlined /></div>
    <h2 className="welcome-title">超级助理</h2>
    <p className="welcome-sub">智能搜索 · 知识问答 · 代码生成 · 技能扩展</p>

    <div className="welcome-features">
      {FEATURES.map((f) => (
        <div key={f.label} className="welcome-feature">
          <div className={`welcome-feature-icon ${f.cls}`}>{f.icon}</div>
          <span className="welcome-feature-label">{f.label}</span>
        </div>
      ))}
    </div>

    <div className="suggestion-grid">
      {SUGGESTIONS.map((s) => (
        <span key={s.text} className="suggestion-chip" onClick={() => onSend(s.text)}>
          {s.icon}{s.text}
        </span>
      ))}
    </div>
  </div>
));

WelcomeScreen.displayName = "WelcomeScreen";
export default WelcomeScreen;
