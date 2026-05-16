import { useState, useMemo } from "react";
import { Input, Button, Select } from "antd";
import { SearchOutlined, PlusOutlined, HeartOutlined, StarOutlined, ExperimentOutlined } from "@ant-design/icons";

/* ── Mock Data ── */
interface SkillItem {
  id: string;
  title: string;
  description: string;
  tags: string[];
  author: string;
  publishDate: string;
  likes: number;
  favorites: number;
  isFeatured: boolean;
  isOfficial: boolean;
}

const mockSkills: SkillItem[] = [
  { id: "s1", title: "百度搜索", description: "使用百度搜索引擎进行网页搜索，获取实时信息。适用于搜索新闻、文档、教程或任何需要网络搜索的信息。", tags: ["调查研究", "效率工具"], author: "liangfu", publishDate: "2026-02-13", likes: 0, favorites: 4, isFeatured: false, isOfficial: false },
  { id: "s2", title: "知识库文档", description: "管理和检索企业内部知识文档，支持多种格式导入与智能问答。", tags: ["开发编程", "知识管理"], author: "qinqin", publishDate: "2026-01-20", likes: 35, favorites: 35, isFeatured: true, isOfficial: true },
  { id: "s3", title: "百度邮箱助手", description: "智能邮箱管理助手，自动分类、摘要与回复建议。", tags: ["效率工具"], author: "shanghaifeng", publishDate: "2026-03-01", likes: 2, favorites: 4, isFeatured: false, isOfficial: false },
  { id: "s4", title: "每日热榜", description: "聚合全网热点新闻，AI生成摘要与趋势分析。", tags: ["内容创作", "媒体"], author: "liangfu", publishDate: "2026-02-28", likes: 3, favorites: 2, isFeatured: false, isOfficial: true },
  { id: "s5", title: "代码审查助手", description: "AI驱动的代码审查工具，支持多语言与自定义规则。", tags: ["开发编程"], author: "devteam", publishDate: "2026-04-10", likes: 128, favorites: 96, isFeatured: true, isOfficial: true },
  { id: "s6", title: "数据可视化", description: "将数据快速转换为交互式图表，支持多种图表类型。", tags: ["数据分析", "效率工具"], author: "dataviz", publishDate: "2026-03-15", likes: 56, favorites: 42, isFeatured: false, isOfficial: false },
];

const categories = ["参赛专区", "全部", "效率工具", "开发编程", "数据分析", "内容创作", "媒体", "调查研究", "知识管理"];
const filterTypes = ["全部", "精选", "官方"];
const sortOptions = ["最多使用", "最新发布", "最多收藏"];

/* ── Skill Card ── */

function SkillCard({ skill }: { skill: SkillItem }) {
  return (
    <div className="skill-card">
      <div className="skill-card-icon-wrap">
        <ExperimentOutlined style={{ fontSize: 24, color: "#1A73E8" }} />
      </div>
      <h4 className="skill-card-title">{skill.title}</h4>
      <p className="skill-card-desc">{skill.description}</p>
      <div className="skill-card-tags">
        {skill.tags.map((t) => (
          <span key={t} className="skill-tag">{t}</span>
        ))}
      </div>
      <div className="skill-card-footer">
        <div className="skill-card-author">
          <span className="skill-card-author-name">{skill.author}</span>
          <span className="skill-card-date">{skill.publishDate}</span>
        </div>
        <div className="skill-card-stats">
          <span className="skill-stat"><HeartOutlined /> {skill.likes}</span>
          <span className="skill-stat"><StarOutlined /> {skill.favorites}</span>
        </div>
      </div>
    </div>
  );
}

/* ── Main Page ── */

export default function SkillsCenterPage() {
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<"skill" | "list">("skill");
  const [activeCategory, setActiveCategory] = useState("全部");
  const [activeFilter, setActiveFilter] = useState("全部");
  const [sortBy, setSortBy] = useState("最多使用");

  const filtered = useMemo(() => {
    let list = mockSkills;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter((s) =>
        s.title.toLowerCase().includes(q) || s.description.toLowerCase().includes(q) || s.tags.some((t) => t.toLowerCase().includes(q))
      );
    }
    if (activeCategory !== "全部") {
      list = list.filter((s) => s.tags.includes(activeCategory));
    }
    if (activeFilter === "精选") {
      list = list.filter((s) => s.isFeatured);
    } else if (activeFilter === "官方") {
      list = list.filter((s) => s.isOfficial);
    }
    // Sort
    if (sortBy === "最多使用") list.sort((a, b) => b.favorites - a.favorites);
    else if (sortBy === "最新发布") list.sort((a, b) => b.publishDate.localeCompare(a.publishDate));
    else if (sortBy === "最多收藏") list.sort((a, b) => b.likes - a.likes);
    return list;
  }, [search, activeCategory, activeFilter, sortBy]);

  return (
    <div className="market-page">
      {/* Top bar */}
      <div className="market-topbar">
        <h2 className="market-topbar-title">Skills Center</h2>
        <div className="market-topbar-center">
          <span className="skills-explore-icon">
            <ExperimentOutlined style={{ fontSize: 18 }} />
          </span>
          <Input
            prefix={<SearchOutlined style={{ color: "#999" }} />}
            placeholder="搜索技能..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="market-search"
            style={{ width: 320 }}
          />
        </div>
        <Button type="primary" icon={<PlusOutlined />} className="market-create-btn">
          创建 Skill
        </Button>
      </div>

      {/* Secondary nav */}
      <div className="skills-secondary-nav">
        <div className="skills-tabs">
          <span
            className={`skills-tab${activeTab === "skill" ? " active" : ""}`}
            onClick={() => setActiveTab("skill")}
          >
            Skill
          </span>
          <span
            className={`skills-tab${activeTab === "list" ? " active" : ""}`}
            onClick={() => setActiveTab("list")}
          >
            清单
          </span>
        </div>
        <span className="skills-count">共{filtered.length}条 技能</span>
      </div>

      {/* Filters */}
      <div className="skills-filters">
        <div className="skills-filter-row">
          {categories.map((cat) => (
            <span
              key={cat}
              className={`skills-filter-tag${activeCategory === cat ? " active" : ""}`}
              onClick={() => setActiveCategory(cat)}
            >
              {cat}
            </span>
          ))}
        </div>
        <div className="skills-filter-row">
          <div className="skills-filter-types">
            {filterTypes.map((ft) => (
              <span
                key={ft}
                className={`skills-filter-type${activeFilter === ft ? " active" : ""}`}
                onClick={() => setActiveFilter(ft)}
              >
                {ft}
              </span>
            ))}
          </div>
          <Select
            value={sortBy}
            onChange={setSortBy}
            size="small"
            style={{ width: 120 }}
            options={sortOptions.map((s) => ({ value: s, label: s }))}
          />
        </div>
      </div>

      {/* Results */}
      <div className="market-content">
        {search && (
          <div className="market-result-info">
            搜索 "<strong>{search}</strong>" 找到 {filtered.length} 个技能
          </div>
        )}

        {filtered.length > 0 ? (
          <div className="skills-grid">
            {filtered.map((s) => <SkillCard key={s.id} skill={s} />)}
          </div>
        ) : (
          <div className="market-empty">未找到相关技能，试试其他关键词</div>
        )}
      </div>
    </div>
  );
}
