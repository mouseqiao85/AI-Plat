import { useState, useEffect, useMemo, useCallback } from "react";
import { Input, Button, Tag, Modal, Form, Switch, message, Popconfirm, Spin, Empty } from "antd";
import { SearchOutlined, PlusOutlined, UserOutlined, ThunderboltOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { marketplaceApi } from "../services/api";
import type { MarketAgent } from "../types";

const allCategories = ["全部", "项目管理", "银行行长", "智能信贷", "效率工具"];

function parseTags(tags: string): string[] {
  try { return JSON.parse(tags); } catch { return []; }
}

function AgentCard({ agent, onEdit, onDelete }: { agent: MarketAgent; onEdit: () => void; onDelete: () => void }) {
  const tags = parseTags(agent.tags);
  return (
    <div className={`agent-card${agent.featured ? " featured" : ""}`}>
      {agent.featured && (
        <div className="agent-card-icon large">
          <ThunderboltOutlined style={{ fontSize: 24, color: "#fff" }} />
        </div>
      )}
      {!agent.featured && (
        <div className="agent-card-header">
          <div className="agent-card-icon small">
            <ThunderboltOutlined style={{ fontSize: 16, color: "#1A73E8" }} />
          </div>
          <h4 className="agent-card-title small">{agent.title}</h4>
        </div>
      )}
      {agent.featured && <h3 className="agent-card-title">{agent.title}</h3>}
      <p className="agent-card-desc">{agent.description}</p>
      <div className="agent-card-tags">
        {tags.map((t) => <Tag key={t} className="agent-tag">{t}</Tag>)}
      </div>
      <div className="agent-card-meta" style={{ position: "relative" }}>
        <span><UserOutlined style={{ marginRight: 4 }} />{agent.author}</span>
        <span>{agent.usage_count.toLocaleString()} 次使用</span>
        <div className="agent-card-actions" style={{ position: "absolute", top: -8, right: 0, display: "flex", gap: 4 }}>
          <Button type="text" size="small" icon={<EditOutlined />} onClick={(e) => { e.stopPropagation(); onEdit(); }} />
          <Popconfirm title="确认删除？" onConfirm={(e) => { e?.stopPropagation(); onDelete(); }} okText="删除" cancelText="取消">
            <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
          </Popconfirm>
        </div>
      </div>
    </div>
  );
}

export default function AgentMarketPage() {
  const [agents, setAgents] = useState<MarketAgent[]>([]);
  const [, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("全部");

  // Create / Edit modal
  const [modalOpen, setModalOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<MarketAgent | null>(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const loadAgents = useCallback(async () => {
    setLoading(true);
    try {
      const cat = activeCategory !== "全部" ? activeCategory : undefined;
      const res = await marketplaceApi.list(cat);
      setAgents(res.agents);
      setTotal(res.total);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [activeCategory]);

  useEffect(() => { loadAgents(); }, [loadAgents]);

  const filtered = useMemo(() => {
    if (!search.trim()) return agents;
    const q = search.trim().toLowerCase();
    return agents.filter((a) =>
      a.title.toLowerCase().includes(q) ||
      a.description.toLowerCase().includes(q) ||
      parseTags(a.tags).some((t) => t.toLowerCase().includes(q))
    );
  }, [agents, search]);

  const featured = useMemo(() => filtered.filter((a) => a.featured), [filtered]);
  const categorized = useMemo(() => {
    const map: Record<string, MarketAgent[]> = {};
    for (const a of filtered.filter((a) => !a.featured)) {
      if (!map[a.category]) map[a.category] = [];
      map[a.category].push(a);
    }
    return map;
  }, [filtered]);

  const openCreate = () => {
    setEditingAgent(null);
    form.resetFields();
    form.setFieldsValue({ featured: false, category: "项目管理" });
    setModalOpen(true);
  };

  const openEdit = (agent: MarketAgent) => {
    setEditingAgent(agent);
    form.setFieldsValue({
      title: agent.title,
      description: agent.description,
      tags: parseTags(agent.tags).join(", "),
      category: agent.category,
      featured: agent.featured,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const tagsArr = values.tags ? values.tags.split(/[,，]/).map((s: string) => s.trim()).filter(Boolean) : [];
      const payload = {
        title: values.title,
        description: values.description || "",
        tags: JSON.stringify(tagsArr),
        category: values.category,
        featured: values.featured || false,
        author: "admin",
      };
      if (editingAgent) {
        await marketplaceApi.update(editingAgent.id, payload);
        message.success("更新成功");
      } else {
        await marketplaceApi.create(payload);
        message.success("创建成功");
      }
      setModalOpen(false);
      loadAgents();
    } catch (err) {
      if (err && typeof err === 'object' && 'errorFields' in err) return; // form validation
      message.error("操作失败");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await marketplaceApi.remove(id);
      message.success("已删除");
      loadAgents();
    } catch { message.error("删除失败"); }
  };

  return (
    <div className="market-page">
      {/* Top bar */}
      <div className="market-topbar">
        <h2 className="market-topbar-title">智能体应用市场</h2>
        <div className="market-topbar-center">
          <Input
            prefix={<SearchOutlined style={{ color: "#999" }} />}
            placeholder="搜索智能体..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="market-search"
          />
        </div>
        <Button type="primary" icon={<PlusOutlined />} className="market-create-btn" onClick={openCreate}>
          创建智能体
        </Button>
      </div>

      {/* Category tabs */}
      <div className="market-categories">
        {allCategories.map((cat) => (
          <span
            key={cat}
            className={`market-cat-tag${activeCategory === cat ? " active" : ""}`}
            onClick={() => setActiveCategory(cat)}
          >
            {cat}
          </span>
        ))}
      </div>

      {/* Content */}
      <div className="market-content">
        {search && (
          <div className="market-result-info">
            搜索 "<strong>{search}</strong>" 找到 {filtered.length} 个智能体
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: "center", padding: 60 }}><Spin size="large" /></div>
        ) : agents.length === 0 ? (
          <Empty description="暂无智能体，点击右上角创建" style={{ padding: 60 }} />
        ) : (
          <>
            {!search && featured.length > 0 && (
              <section className="market-section">
                <h3 className="market-section-title">今日精选</h3>
                <div className="market-grid-3">
                  {featured.map((a) => (
                    <AgentCard key={a.id} agent={a} onEdit={() => openEdit(a)} onDelete={() => handleDelete(a.id)} />
                  ))}
                </div>
              </section>
            )}
            {!search && Object.entries(categorized).map(([cat, list]) => (
              <section key={cat} className="market-section">
                <h3 className="market-section-title">{cat} ({list.length})</h3>
                <div className="market-grid-4">
                  {list.map((a) => (
                    <AgentCard key={a.id} agent={a} onEdit={() => openEdit(a)} onDelete={() => handleDelete(a.id)} />
                  ))}
                </div>
              </section>
            ))}
            {search && (
              <section className="market-section">
                <div className="market-grid-4">
                  {filtered.map((a) => (
                    <AgentCard key={a.id} agent={a} onEdit={() => openEdit(a)} onDelete={() => handleDelete(a.id)} />
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>

      {/* Create / Edit Modal */}
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
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="智能体描述" />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Input placeholder="用逗号分隔，如：合同,法务" />
          </Form.Item>
          <Form.Item name="category" label="分类" rules={[{ required: true, message: "请选择分类" }]}>
            <Input placeholder="项目管理 / 银行行长 / 智能信贷 / 效率工具" />
          </Form.Item>
          <Form.Item name="featured" label="设为精选" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
