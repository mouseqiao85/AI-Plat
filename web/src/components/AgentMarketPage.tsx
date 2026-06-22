import { useState, useEffect, useMemo, useCallback } from "react";
import { Input, Button, Tag, Modal, Form, Switch, message, Popconfirm, Spin, Empty, Tooltip } from "antd";
import { SearchOutlined, PlusOutlined, UserOutlined, ThunderboltOutlined, EditOutlined, DeleteOutlined, LinkOutlined, BookOutlined } from "@ant-design/icons";
import { marketplaceApi } from "../services/api";
import type { MarketAgent } from "../types";

export const VERTICAL_CATEGORIES = ["项目管理", "技术开发", "部署运维"] as const;
export type VerticalCategory = typeof VERTICAL_CATEGORIES[number];

const LEGACY_CATEGORY_MAP: Record<string, VerticalCategory> = {
  项目管理: "项目管理",
  企业效率: "项目管理",
  知识管理: "项目管理",
  金融分析: "项目管理",
  研究写作: "项目管理",
  智能信贷: "项目管理",
  开发工具: "技术开发",
  技术开发: "技术开发",
  技术管理: "技术开发",
  效率工具: "技术开发",
  部署运维: "部署运维",
  运维: "部署运维",
  发布: "部署运维",
};

function normalizeCategory(category?: string): VerticalCategory {
  if (!category) return "项目管理";
  return LEGACY_CATEGORY_MAP[category] || "项目管理";
}

function openExternal(url?: string) {
  if (!url) return;
  window.open(url, "_blank", "noopener,noreferrer");
}

function AgentCard({ agent, onEdit, onDelete }: { agent: MarketAgent; onEdit: () => void; onDelete: () => void }) {
  const category = normalizeCategory(agent.category);
  const hasAccess = Boolean(agent.access_url?.trim());
  const hasKnowledge = Boolean(agent.knowledge_url?.trim());
  return (
    <div className={`agent-card${agent.featured ? " featured" : ""}`}>
      <div className="agent-card-header">
        <div className={agent.featured ? "agent-card-icon large" : "agent-card-icon small"}>
          <ThunderboltOutlined style={{ fontSize: agent.featured ? 24 : 16, color: agent.featured ? "#fff" : "#1A73E8" }} />
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <h3 className={agent.featured ? "agent-card-title" : "agent-card-title small"}>{agent.title}</h3>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <Tag className="agent-tag" color="blue">{category}</Tag>
            {agent.featured && <Tag color="gold">精选</Tag>}
          </div>
        </div>
      </div>
      {agent.function && <p className="agent-card-function">{agent.function}</p>}
      <p className="agent-card-desc">{agent.description || "暂无描述，可编辑补充智能体用途、输入输出和适用场景。"}</p>
      <div className="agent-card-meta">
        <span className="agent-card-author"><UserOutlined style={{ marginRight: 4 }} />{agent.author || "平台"}</span>
        <span>{agent.usage_count > 0 ? `${agent.usage_count.toLocaleString()} 次使用` : "未使用"}</span>
        <div className="agent-card-actions">
          {hasAccess && <Tooltip title="访问入口"><Button type="text" size="small" icon={<LinkOutlined />} onClick={(e) => { e.stopPropagation(); openExternal(agent.access_url); }} /></Tooltip>}
          {hasKnowledge && <Tooltip title="知识库"><Button type="text" size="small" icon={<BookOutlined />} onClick={(e) => { e.stopPropagation(); openExternal(agent.knowledge_url); }} /></Tooltip>}
          <Tooltip title="编辑"><Button type="text" size="small" icon={<EditOutlined />} onClick={(e) => { e.stopPropagation(); onEdit(); }} /></Tooltip>
          <Popconfirm title="确认删除？" onConfirm={(e) => { e?.stopPropagation(); onDelete(); }} okText="删除" cancelText="取消">
            <Tooltip title="删除"><Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} /></Tooltip>
          </Popconfirm>
        </div>
      </div>
    </div>
  );
}

export default function AgentMarketPage({ activeCategory }: { activeCategory: VerticalCategory }) {
  const [agents, setAgents] = useState<MarketAgent[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");

  const [modalOpen, setModalOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<MarketAgent | null>(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const loadAgents = useCallback(async () => {
    setLoading(true);
    try {
      // 拉取全量后在前端按新的三类垂类归并，避免旧分类数据继续污染页面导航。
      const res = await marketplaceApi.list(undefined, 1, 500);
      setAgents(res.agents || []);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "智能体加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAgents(); }, [loadAgents]);

  const verticalAgents = useMemo(
    () => agents.filter((a) => normalizeCategory(a.category) === activeCategory),
    [agents, activeCategory],
  );

  const filtered = useMemo(() => {
    if (!search.trim()) return verticalAgents;
    const q = search.trim().toLowerCase();
    return verticalAgents.filter((a) =>
      a.title.toLowerCase().includes(q) ||
      (a.function || "").toLowerCase().includes(q) ||
      (a.description || "").toLowerCase().includes(q) ||
      (a.author || "").toLowerCase().includes(q)
    );
  }, [verticalAgents, search]);

  const featured = useMemo(() => filtered.filter((a) => a.featured), [filtered]);
  const normalAgents = useMemo(() => filtered.filter((a) => !a.featured), [filtered]);

  const openCreate = () => {
    setEditingAgent(null);
    form.resetFields();
    form.setFieldsValue({ featured: false, category: activeCategory, author: "平台" });
    setModalOpen(true);
  };

  const openEdit = (agent: MarketAgent) => {
    setEditingAgent(agent);
    form.setFieldsValue({
      title: agent.title,
      function: agent.function,
      description: agent.description,
      access_url: agent.access_url,
      knowledge_url: agent.knowledge_url,
      category: normalizeCategory(agent.category),
      featured: agent.featured,
      author: agent.author || "平台",
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = {
        title: values.title.trim(),
        function: values.function || "",
        description: values.description || "",
        access_url: values.access_url || "",
        knowledge_url: values.knowledge_url || "",
        tags: "[]",
        category: values.category || activeCategory,
        featured: values.featured || false,
        author: values.author || "平台",
      };
      if (editingAgent) {
        await marketplaceApi.update(editingAgent.id, payload);
        message.success("更新成功");
      } else {
        await marketplaceApi.create(payload);
        message.success("创建成功");
      }
      setModalOpen(false);
      await loadAgents();
    } catch (err) {
      if (err && typeof err === "object" && "errorFields" in err) return;
      message.error(err instanceof Error ? err.message : "操作失败");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await marketplaceApi.remove(id);
      message.success("已删除");
      await loadAgents();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "删除失败");
    }
  };

  return (
    <div className="market-page">
      <div className="market-topbar">
        <h2 className="market-topbar-title">垂类智能体</h2>
        <div className="market-topbar-center">
          <Input
            prefix={<SearchOutlined style={{ color: "#999" }} />}
            placeholder={`搜索${activeCategory}智能体...`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="market-search"
            allowClear
          />
        </div>
        <Button type="primary" icon={<PlusOutlined />} className="market-create-btn" onClick={openCreate}>
          创建智能体
        </Button>
      </div>

      <div className="market-categories">
        {VERTICAL_CATEGORIES.map((cat) => (
          <span key={cat} className={`market-cat-tag${activeCategory === cat ? " active" : ""}`}>
            {cat}
          </span>
        ))}
      </div>

      <div className="market-content">
        <div className="market-result-info">
          {search ? <>搜索 "<strong>{search}</strong>" 找到 {filtered.length} 个智能体</> : <>{activeCategory} · {verticalAgents.length} 个智能体</>}
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: 60 }}><Spin size="large" /></div>
        ) : verticalAgents.length === 0 ? (
          <Empty description={`暂无${activeCategory}智能体，点击右上角创建`} style={{ padding: 60 }} />
        ) : filtered.length === 0 ? (
          <Empty description="未找到相关智能体，试试其他关键词" style={{ padding: 60 }} />
        ) : (
          <>
            {!search && featured.length > 0 && (
              <section className="market-section">
                <h3 className="market-section-title">精选智能体</h3>
                <div className="market-grid-3">
                  {featured.map((a) => (
                    <AgentCard key={a.id} agent={a} onEdit={() => openEdit(a)} onDelete={() => handleDelete(a.id)} />
                  ))}
                </div>
              </section>
            )}
            <section className="market-section">
              <h3 className="market-section-title">{activeCategory} ({normalAgents.length || filtered.length})</h3>
              <div className="market-grid-4">
                {(search ? filtered : normalAgents.length > 0 ? normalAgents : filtered).map((a) => (
                  <AgentCard key={a.id} agent={a} onEdit={() => openEdit(a)} onDelete={() => handleDelete(a.id)} />
                ))}
              </div>
            </section>
          </>
        )}
      </div>

      <Modal
        title={editingAgent ? "编辑智能体" : "创建智能体"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        confirmLoading={saving}
        okText={editingAgent ? "保存" : "创建"}
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="title" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input placeholder="智能体名称" />
          </Form.Item>
          <Form.Item name="function" label="功能定位">
            <Input placeholder="一句话说明该智能体能做什么" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="补充适用场景、输入输出和使用说明" />
          </Form.Item>
          <Form.Item name="access_url" label="访问入口">
            <Input placeholder="https://...（可选）" />
          </Form.Item>
          <Form.Item name="knowledge_url" label="知识库链接">
            <Input placeholder="https://...（可选）" />
          </Form.Item>
          <Form.Item name="category" label="垂类" rules={[{ required: true, message: "请选择垂类" }]}>
            <select style={{ width: "100%", height: 32, border: "1px solid #d9d9d9", borderRadius: 6, padding: "0 8px" }}>
              {VERTICAL_CATEGORIES.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
            </select>
          </Form.Item>
          <Form.Item name="author" label="作者/来源">
            <Input placeholder="平台 / 团队 / 创建人" />
          </Form.Item>
          <Form.Item name="featured" label="设为精选" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
