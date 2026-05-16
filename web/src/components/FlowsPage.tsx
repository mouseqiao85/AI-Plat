import { useEffect, useMemo, useState, useRef } from "react";
import {
  Button, Input, Select, Tag, Empty, Spin, message, Modal, Popconfirm, Tooltip, Checkbox, Radio, Tabs, Upload,
} from "antd";
import {
  PlusOutlined, DeleteOutlined, PlayCircleOutlined,
  SaveOutlined, EditOutlined, SearchOutlined, ThunderboltOutlined, CheckCircleFilled,
  WarningFilled, StopOutlined, ClearOutlined, GithubOutlined, DownloadOutlined, PaperClipOutlined,
} from "@ant-design/icons";
import { hermesApi, tabsApi, streamFlowRun } from "../services/api";
import type {
  ExpertRole, ToolScenario, DialogFlow, FlowType, RunEvent, FlowRunOutput,
  SkillTab, TabRole,
} from "../types";
import { useAppStore } from "../stores/appStore";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ImportSkillModal from "./ImportSkillModal";

/* ── Category labels (must match gstack_loader.CATEGORY_MAP) ── */
const CATEGORY_LABELS: Record<string, string> = {
  plan: "规划",
  implement: "实现",
  release: "发布",
  ops: "运维",
  browser: "浏览器",
  safety: "安全",
  other: "其他",
};
const CATEGORY_ORDER = ["plan", "implement", "release", "ops", "browser", "safety", "other"];

interface RunRolePanel {
  role_id: string;
  status: "pending" | "running" | "completed" | "failed";
  content: string;
  error?: string;
  latency_ms?: number;
}

export default function FlowsPage() {
  const { user } = useAppStore();

  /* ── Data ── */
  const [roles, setRoles] = useState<ExpertRole[]>([]);
  const [scenarios, setScenarios] = useState<ToolScenario[]>([]);
  const [flows, setFlows] = useState<DialogFlow[]>([]);
  const [loading, setLoading] = useState(false);

  /* ── Composer state ── */
  const [composerOpen, setComposerOpen] = useState(false);
  const [editingFlow, setEditingFlow] = useState<DialogFlow | null>(null);
  const [flowName, setFlowName] = useState("");
  const [flowDesc, setFlowDesc] = useState("");
  const [flowType, setFlowType] = useState<FlowType>("sequential");
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>("");
  const [promptTemplate, setPromptTemplate] = useState("");
  const [selectedModel, setSelectedModel] = useState<string>("deepseek-v4-flash");
  const [searchKeyword, setSearchKeyword] = useState("");
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [saving, setSaving] = useState(false);

  /* ── Run state ── */
  const [activeFlowId, setActiveFlowId] = useState<number | null>(null);
  const [runInput, setRunInput] = useState("");
  const [running, setRunning] = useState(false);
  const [runRoles, setRunRoles] = useState<RunRolePanel[]>([]);
  const [runError, setRunError] = useState<string>("");
  const [pastRuns, setPastRuns] = useState<{ id: number; status: string; outputs: FlowRunOutput[]; started_at: string }[]>([]);
  const [attachedFiles, setAttachedFiles] = useState<{ name: string; content: string }[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  /* ── Tab state ── */
  const [skillTabs, setSkillTabs] = useState<SkillTab[]>([]);
  const [activeTab, setActiveTab] = useState<string>("software-engineering");
  const [tabRoles, setTabRoles] = useState<TabRole[]>([]);
  const [importModalOpen, setImportModalOpen] = useState(false);

  /* ── Load data ── */
  const loadAll = async () => {
    setLoading(true);
    try {
      const [r, s, f, t] = await Promise.all([
        hermesApi.listRoles(),
        hermesApi.listScenarios(),
        hermesApi.listFlows(user?.id),
        tabsApi.listTabs(),
      ]);
      setRoles(r.roles || []);
      setScenarios(s.scenarios || []);
      setFlows(f.flows || []);
      setSkillTabs(t.tabs || []);
    } catch (e) {
      message.error("加载失败：" + (e instanceof Error ? e.message : "网络错误"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) loadAll();
  }, [user?.id]);

  const loadTabRoles = async (tabId: string) => {
    if (tabId === "software-engineering") {
      setTabRoles([]);
      return;
    }
    try {
      const res = await tabsApi.listTabRoles(tabId);
      setTabRoles(res.roles || []);
    } catch { setTabRoles([]); }
  };

  const handleTabSwitch = (tabId: string) => {
    setActiveTab(tabId);
    loadTabRoles(tabId);
  };

  /* ── Composer helpers ── */

  const openComposer = (flow?: DialogFlow) => {
    if (flow) {
      setEditingFlow(flow);
      setFlowName(flow.name || "");
      setFlowDesc(flow.description || "");
      setFlowType(flow.flow_type || "sequential");
      setSelectedRoles([...(flow.role_ids || [])]);
      setSelectedScenario(flow.scenario_id || "");
      setPromptTemplate(flow.prompt_template || "");
      setSelectedModel(flow.model || "deepseek-v4-flash");
    } else {
      setEditingFlow(null);
      setFlowName("");
      setFlowDesc("");
      setFlowType("sequential");
      setSelectedRoles([]);
      setSelectedScenario("");
      setPromptTemplate("");
      setSelectedModel("deepseek-v4-flash");
    }
    setSearchKeyword("");
    setFilterCategory("all");
    setComposerOpen(true);
  };

  const closeComposer = () => {
    setComposerOpen(false);
    setEditingFlow(null);
  };

  const handleScenarioChange = (sid: string) => {
    setSelectedScenario(sid);
    if (!sid) return;
    const sc = scenarios.find((s) => s.id === sid);
    if (!sc) return;
    // Recommend roles from scenario (intersect with installed roles).
    const installed = new Set(roles.map((r) => r.id));
    const recommended = (sc.recommended_roles || []).filter((rid) => installed.has(rid));
    if (recommended.length > 0) {
      setSelectedRoles((prev) => Array.from(new Set([...prev, ...recommended])));
    }
  };

  const toggleRole = (id: string) => {
    setSelectedRoles((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const moveRole = (idx: number, dir: -1 | 1) => {
    const next = [...selectedRoles];
    const target = idx + dir;
    if (target < 0 || target >= next.length) return;
    [next[idx], next[target]] = [next[target], next[idx]];
    setSelectedRoles(next);
  };

  const filteredRoles = useMemo(() => {
    const kw = searchKeyword.trim().toLowerCase();
    return roles.filter((r) => {
      if (filterCategory !== "all" && r.category !== filterCategory) return false;
      if (!kw) return true;
      return (
        r.id.toLowerCase().includes(kw) ||
        r.name.toLowerCase().includes(kw) ||
        (r.description || "").toLowerCase().includes(kw) ||
        (r.triggers || []).some((t) => t.toLowerCase().includes(kw))
      );
    });
  }, [roles, searchKeyword, filterCategory]);

  const rolesByCategory = useMemo(() => {
    const m: Record<string, ExpertRole[]> = {};
    for (const r of filteredRoles) {
      const c = r.category || "other";
      if (!m[c]) m[c] = [];
      m[c].push(r);
    }
    return m;
  }, [filteredRoles]);

  const saveFlow = async () => {
    if (!flowName.trim()) { message.warning("请填写流程名称"); return; }
    if (selectedRoles.length === 0) { message.warning("至少选择 1 个角色"); return; }
    setSaving(true);
    try {
      if (editingFlow) {
        await hermesApi.updateFlow(editingFlow.id, {
          name: flowName.trim(),
          description: flowDesc,
          flow_type: flowType,
          role_ids: selectedRoles,
          scenario_id: selectedScenario,
          prompt_template: promptTemplate,
          model: selectedModel,
        });
        message.success("流程已更新");
      } else {
        await hermesApi.createFlow({
          name: flowName.trim(),
          description: flowDesc,
          flow_type: flowType,
          role_ids: selectedRoles,
          scenario_id: selectedScenario,
          prompt_template: promptTemplate,
          model: selectedModel,
          owner_id: user?.id || 0,
        });
        message.success("流程已创建");
      }
      closeComposer();
      await loadAll();
    } catch (e) {
      message.error("保存失败：" + (e instanceof Error ? e.message : ""));
    } finally {
      setSaving(false);
    }
  };

  const deleteFlow = async (id: number) => {
    try {
      await hermesApi.deleteFlow(id);
      message.success("已删除");
      if (activeFlowId === id) setActiveFlowId(null);
      await loadAll();
    } catch (e) {
      message.error("删除失败：" + (e instanceof Error ? e.message : ""));
    }
  };

  /* ── Run a flow ── */

  const selectFlow = async (id: number) => {
    setActiveFlowId(id);
    setRunRoles([]);
    setRunError("");
    setRunInput("");
    setPastRuns([]);
    try {
      const r = await hermesApi.listRuns(id);
      setPastRuns((r.runs || []).slice(0, 10).map((x) => ({
        id: x.id, status: x.status, outputs: x.outputs || [], started_at: x.started_at,
      })));
    } catch { /* ignore */ }
  };

  const startRun = async () => {
    const flow = flows.find((f) => f.id === activeFlowId);
    if (!flow) { message.warning("先选择一个流程"); return; }
    if (!runInput.trim() && attachedFiles.length === 0) { message.warning("请输入运行内容或上传附件"); return; }
    setRunning(true);
    setRunError("");
    setRunRoles((flow.role_ids || []).map((rid) => ({ role_id: rid, status: "pending", content: "" })));

    // Build message: user input + attached file contents
    let fullMessage = runInput.trim();
    if (attachedFiles.length > 0) {
      const fileParts = attachedFiles.map((f) => `\n\n---\n**附件: ${f.name}**\n\n${f.content}`).join("");
      fullMessage = fullMessage ? fullMessage + fileParts : fileParts.trim();
    }

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      for await (const ev of streamFlowRun(flow.id, fullMessage, ctrl.signal)) {
        applyRunEvent(ev);
      }
    } catch (e) {
      if (e instanceof Error && e.name !== "AbortError") {
        setRunError(e.message);
        message.error("运行错误：" + e.message);
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
      // Refresh past runs
      try {
        const r = await hermesApi.listRuns(flow.id);
        setPastRuns((r.runs || []).slice(0, 10).map((x) => ({
          id: x.id, status: x.status, outputs: x.outputs || [], started_at: x.started_at,
        })));
      } catch { /* ignore */ }
    }
  };

  const applyRunEvent = (ev: RunEvent) => {
    setRunRoles((prev) => {
      const next = [...prev];
      const findIdx = (rid?: string, idx?: number) => {
        if (idx !== undefined && idx >= 0 && idx < next.length && next[idx].role_id === rid) return idx;
        return next.findIndex((p) => p.role_id === rid);
      };
      switch (ev.type) {
        case "role_started": {
          const i = findIdx(ev.role_id, ev.index);
          if (i >= 0) next[i] = { ...next[i], status: "running" };
          break;
        }
        case "role_output": {
          // Streaming text chunk — append to current role content
          const i = findIdx(ev.role_id, ev.index);
          if (i >= 0) next[i] = {
            ...next[i], status: "running",
            content: (next[i].content || "") + (ev.content || ""),
          };
          break;
        }
        case "role_completed": {
          const i = findIdx(ev.role_id, ev.index);
          if (i >= 0) next[i] = {
            ...next[i], status: "completed",
            content: ev.content, latency_ms: ev.latency_ms,
          };
          break;
        }
        case "role_failed": {
          const i = findIdx(ev.role_id, ev.index);
          if (i >= 0) next[i] = {
            ...next[i], status: "failed",
            error: ev.error, latency_ms: ev.latency_ms,
          };
          break;
        }
        case "run_failed":
          setRunError(ev.error);
          break;
        case "error":
          setRunError(ev.error);
          break;
      }
      return next;
    });
  };

  const cancelRun = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
      setRunning(false);
      message.info("已取消");
    }
  };

  /* ── Render ── */

  if (loading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Spin size="large" tip="加载多智能体配置..." />
      </div>
    );
  }

  if (!user) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Empty description="请先登录后使用多智能体功能" />
      </div>
    );
  }

  const activeFlow = flows.find((f) => f.id === activeFlowId);
  const roleById = (id: string) => roles.find((r) => r.id === id);

  const exportRunToMd = () => {
    const flow = activeFlow;
    const now = new Date().toLocaleString("zh-CN");
    const lines: string[] = [
      "# 多智能体流程运行报告\n",
      `- **流程**: ${flow?.name || "未命名"}`,
      `- **类型**: ${flow?.flow_type || "sequential"}`,
      `- **时间**: ${now}`,
      `- **输入**: ${runInput}\n`,
      "---\n",
    ];
    for (const rp of runRoles) {
      const r = roleById(rp.role_id);
      const name = r?.name || rp.role_id;
      const cat = r?.category ? ` (${CATEGORY_LABELS[r.category] || r.category})` : "";
      lines.push(`## ${name}${cat}\n`);
      if (rp.latency_ms !== undefined) {
        lines.push(`> 耗时: ${rp.latency_ms}ms\n`);
      }
      if (rp.error) {
        lines.push(`**错误**: ${rp.error}\n`);
      }
      if (rp.content) {
        lines.push(rp.content + "\n");
      }
      lines.push("---\n");
    }
    const md = lines.join("\n");
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const date = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `flow-${flow?.name || "output"}-${date}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Top toolbar */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 16px", borderBottom: "1px solid #f0f0f0", flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 600 }}>多智能体编排</span>
          <Tag color="blue">{roles.length} 个角色已加载</Tag>
          <Tag color="purple">{flows.length} 个流程</Tag>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <Button size="small" icon={<GithubOutlined />} onClick={() => setImportModalOpen(true)}>
            导入 Skill
          </Button>
          <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => openComposer()}>
            新建流程
          </Button>
        </div>
      </div>

      {/* Body — split: left flow list, right runner */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* ── Flow list ── */}
        <div style={{
          width: 280, borderRight: "1px solid #f0f0f0", overflow: "auto",
          background: "#fafafa", padding: "8px 0",
        }}>
          {flows.length === 0 ? (
            <Empty description="暂无流程，点击新建" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 40 }} />
          ) : (
            flows.map((f) => {
              const isActive = activeFlowId === f.id;
              return (
                <div
                  key={f.id}
                  onClick={() => selectFlow(f.id)}
                  style={{
                    margin: "4px 8px", padding: "8px 10px",
                    borderRadius: 6, cursor: "pointer",
                    background: isActive ? "#e6f4ff" : "#fff",
                    border: `1px solid ${isActive ? "#91caff" : "#f0f0f0"}`,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {f.name}
                      </div>
                      <div style={{ fontSize: 11, color: "#8c8c8c", marginTop: 2 }}>
                        <Tag style={{ fontSize: 10, lineHeight: "16px" }} color={f.flow_type === "sequential" ? "geekblue" : "magenta"}>
                          {f.flow_type === "sequential" ? "顺序" : "并行"}
                        </Tag>
                        {(f.role_ids || []).length} 个角色
                      </div>
                      {f.description && (
                        <div style={{ fontSize: 11, color: "#8c8c8c", marginTop: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {f.description}
                        </div>
                      )}
                    </div>
                    <div onClick={(e) => e.stopPropagation()} style={{ display: "flex", gap: 2 }}>
                      <Tooltip title="编辑">
                        <Button size="small" type="text" icon={<EditOutlined />}
                          onClick={() => openComposer(f)}
                          style={{ height: 22, padding: "0 4px" }} />
                      </Tooltip>
                      <Popconfirm title="删除该流程？" onConfirm={() => deleteFlow(f.id)} okText="删除" cancelText="取消">
                        <Button size="small" type="text" danger icon={<DeleteOutlined />}
                          style={{ height: 22, padding: "0 4px" }} />
                      </Popconfirm>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* ── Runner / detail ── */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {!activeFlow ? (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Empty description="选择左侧流程或新建一个流程开始运行" />
            </div>
          ) : (
            <>
              {/* Header */}
              <div style={{ padding: "12px 20px", borderBottom: "1px solid #f0f0f0" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <ThunderboltOutlined style={{ color: "#2468f2" }} />
                  <span style={{ fontSize: 16, fontWeight: 600 }}>{activeFlow.name}</span>
                  <Tag color={activeFlow.flow_type === "sequential" ? "geekblue" : "magenta"}>
                    {activeFlow.flow_type === "sequential" ? "顺序执行" : "并行执行"}
                  </Tag>
                  {activeFlow.scenario_id && (
                    <Tag color="cyan">
                      场景：{scenarios.find((s) => s.id === activeFlow.scenario_id)?.name || activeFlow.scenario_id}
                    </Tag>
                  )}
                </div>
                {activeFlow.description && (
                  <div style={{ fontSize: 12, color: "#8c8c8c", marginTop: 4 }}>{activeFlow.description}</div>
                )}
                <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {(activeFlow.role_ids || []).map((rid, idx) => {
                    const r = roleById(rid);
                    return (
                      <Tag key={rid} style={{ margin: 0 }}>
                        {idx + 1}. {r?.name || rid}
                      </Tag>
                    );
                  })}
                </div>
              </div>

              {/* Input + run */}
              <div style={{ padding: "12px 20px", borderBottom: "1px solid #f0f0f0", flexShrink: 0 }}>
                <Input.TextArea
                  value={runInput}
                  onChange={(e) => setRunInput(e.target.value)}
                  placeholder="输入要让多智能体协作处理的内容..."
                  autoSize={{ minRows: 2, maxRows: 6 }}
                  disabled={running}
                />
                {attachedFiles.length > 0 && (
                  <div style={{ marginTop: 6, display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {attachedFiles.map((f, i) => (
                      <Tag
                        key={i}
                        closable
                        onClose={() => setAttachedFiles((prev) => prev.filter((_, idx) => idx !== i))}
                      >
                        <PaperClipOutlined /> {f.name} ({(f.content.length / 1024).toFixed(1)}KB)
                      </Tag>
                    ))}
                  </div>
                )}
                <div style={{ marginTop: 8, display: "flex", gap: 6, justifyContent: "flex-end" }}>
                  <Upload
                    accept=".md,.txt,.markdown"
                    multiple
                    showUploadList={false}
                    beforeUpload={(file) => {
                      const reader = new FileReader();
                      reader.onload = (e) => {
                        const content = e.target?.result as string;
                        if (content) {
                          setAttachedFiles((prev) => [...prev, { name: file.name, content }]);
                        }
                      };
                      reader.readAsText(file);
                      return false; // prevent actual upload
                    }}
                    disabled={running}
                  >
                    <Button icon={<PaperClipOutlined />} disabled={running}>
                      附件
                    </Button>
                  </Upload>
                  {running ? (
                    <Button danger icon={<StopOutlined />} onClick={cancelRun}>
                      取消
                    </Button>
                  ) : (
                    <Button
                      type="primary"
                      icon={<PlayCircleOutlined />}
                      onClick={startRun}
                      disabled={!runInput.trim() && attachedFiles.length === 0}
                    >
                      开始运行
                    </Button>
                  )}
                  <Button icon={<ClearOutlined />} onClick={() => { setRunRoles([]); setRunError(""); }} disabled={running}>
                    清空输出
                  </Button>
                  <Button
                    icon={<DownloadOutlined />}
                    onClick={exportRunToMd}
                    disabled={!runRoles.some((rp) => rp.status === "completed")}
                  >
                    导出 MD
                  </Button>
                </div>
              </div>

              {/* Output panels */}
              <div style={{ flex: 1, overflow: "auto", padding: "12px 20px" }}>
                {runRoles.some((rp) => rp.status === "completed") && (
                  <div style={{ marginBottom: 12, display: "flex", justifyContent: "flex-end" }}>
                    <Button type="primary" ghost icon={<DownloadOutlined />} onClick={exportRunToMd}>
                      导出 MD
                    </Button>
                  </div>
                )}
                {runError && (
                  <div style={{
                    padding: "8px 12px", marginBottom: 12,
                    background: "#fff2f0", border: "1px solid #ffccc7",
                    borderRadius: 6, color: "#a8071a", fontSize: 12,
                  }}>
                    <WarningFilled /> {runError}
                  </div>
                )}

                {runRoles.length === 0 ? (
                  <Tabs
                    defaultActiveKey="history"
                    items={[
                      {
                        key: "history",
                        label: `历史运行 (${pastRuns.length})`,
                        children: pastRuns.length === 0 ? (
                          <Empty description="暂无运行记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                        ) : (
                          <div>
                            {pastRuns.map((r) => (
                              <div key={r.id} style={{
                                padding: "10px 12px", marginBottom: 8,
                                border: "1px solid #f0f0f0", borderRadius: 6,
                              }}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                  <span style={{ fontWeight: 600, fontSize: 13 }}>Run #{r.id}</span>
                                  <Tag color={
                                    r.status === "succeeded" ? "green" :
                                    r.status === "failed" ? "red" :
                                    r.status === "running" ? "blue" : "default"
                                  }>{r.status}</Tag>
                                </div>
                                <div style={{ fontSize: 11, color: "#8c8c8c", marginTop: 4 }}>
                                  {new Date(r.started_at).toLocaleString("zh-CN")} · {(r.outputs || []).length} 个角色输出
                                </div>
                              </div>
                            ))}
                          </div>
                        ),
                      },
                    ]}
                  />
                ) : (
                  <div>
                    {runRoles.map((rp) => {
                      const r = roleById(rp.role_id);
                      return (
                        <div key={rp.role_id} style={{
                          marginBottom: 16, border: "1px solid #f0f0f0",
                          borderRadius: 8, overflow: "hidden",
                        }}>
                          <div style={{
                            padding: "8px 14px", background: "#fafafa",
                            borderBottom: "1px solid #f0f0f0",
                            display: "flex", alignItems: "center", gap: 8,
                          }}>
                            {rp.status === "running" && <Spin size="small" />}
                            {rp.status === "completed" && <CheckCircleFilled style={{ color: "#52c41a" }} />}
                            {rp.status === "failed" && <WarningFilled style={{ color: "#ff4d4f" }} />}
                            {rp.status === "pending" && <span style={{ width: 14, height: 14, borderRadius: 7, background: "#d9d9d9", display: "inline-block" }} />}
                            <span style={{ fontWeight: 600 }}>{r?.name || rp.role_id}</span>
                            <Tag style={{ fontSize: 10 }}>{r?.category && CATEGORY_LABELS[r.category]}</Tag>
                            {rp.latency_ms !== undefined && (
                              <span style={{ fontSize: 11, color: "#8c8c8c", marginLeft: "auto" }}>
                                {rp.latency_ms} ms
                              </span>
                            )}
                          </div>
                          <div style={{ padding: "10px 14px", fontSize: 13, lineHeight: 1.7 }}>
                            {rp.error && (
                              <div style={{ color: "#a8071a", whiteSpace: "pre-wrap" }}>{rp.error}</div>
                            )}
                            {rp.content ? (
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{rp.content}</ReactMarkdown>
                            ) : !rp.error && rp.status === "running" ? (
                              <span style={{ color: "#8c8c8c" }}>正在生成...</span>
                            ) : !rp.error && rp.status === "pending" ? (
                              <span style={{ color: "#bfbfbf" }}>等待中</span>
                            ) : null}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Composer Modal ── */}
      <Modal
        title={editingFlow ? "编辑流程" : "新建流程"}
        open={composerOpen}
        onCancel={closeComposer}
        width={1000}
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button onClick={closeComposer}>取消</Button>
            <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={saveFlow}>
              保存
            </Button>
          </div>
        }
      >
        <div style={{ display: "grid", gridTemplateColumns: "420px 1fr", gap: 20 }}>
          {/* Left — basic + scenario + selected order */}
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>流程名称</div>
            <Input value={flowName} onChange={(e) => setFlowName(e.target.value)} placeholder="例如：代码评审小组" />

            <div style={{ fontSize: 12, color: "#8c8c8c", marginTop: 12, marginBottom: 4 }}>描述</div>
            <Input.TextArea value={flowDesc} onChange={(e) => setFlowDesc(e.target.value)}
              autoSize={{ minRows: 1, maxRows: 2 }} placeholder="可选" />

            <div style={{ fontSize: 12, color: "#8c8c8c", marginTop: 12, marginBottom: 4 }}>执行模式</div>
            <Radio.Group value={flowType} onChange={(e) => setFlowType(e.target.value)} size="small">
              <Radio value="sequential">顺序</Radio>
              <Radio value="parallel">并行</Radio>
            </Radio.Group>

            <div style={{ fontSize: 12, color: "#8c8c8c", marginTop: 12, marginBottom: 4 }}>模型</div>
            <Select
              value={selectedModel}
              onChange={setSelectedModel}
              size="small"
              style={{ width: "100%" }}
              options={[
                { value: "deepseek-v4-flash", label: "DeepSeek Flash (V4 极速)" },
                { value: "deepseek-v4-pro", label: "DeepSeek Pro (V4 最强推理)" },
                { value: "deepseek-reasoner", label: "DeepSeek Reasoner (R1 深度思考)" },
              ]}
            />

            <div style={{ fontSize: 12, color: "#8c8c8c", marginTop: 12, marginBottom: 4 }}>场景</div>
            <Select
              value={selectedScenario || undefined}
              onChange={handleScenarioChange}
              allowClear
              placeholder="选择典型场景（可选）"
              size="small"
              style={{ width: "100%" }}
              options={scenarios.map((s) => ({
                value: s.id,
                label: s.name,
              }))}
            />

            <div style={{ fontSize: 12, color: "#8c8c8c", marginTop: 8, marginBottom: 4 }}>提示词模板</div>
            <Input.TextArea
              value={promptTemplate}
              onChange={(e) => setPromptTemplate(e.target.value)}
              autoSize={{ minRows: 2, maxRows: 4 }}
              placeholder="留空使用默认模板"
            />

            <div style={{ fontSize: 12, color: "#8c8c8c", marginTop: 12, marginBottom: 4 }}>
              已选角色（{selectedRoles.length}）{flowType === "sequential" && " ↑↓ 排序"}
            </div>
            <div style={{
              border: "1px solid #f0f0f0", borderRadius: 6, padding: 4,
              minHeight: 80, maxHeight: 200, overflow: "auto", background: "#fafafa",
            }}>
              {selectedRoles.length === 0 ? (
                <div style={{ color: "#bfbfbf", fontSize: 12, textAlign: "center", padding: 16 }}>
                  从右侧勾选角色
                </div>
              ) : (
                selectedRoles.map((rid, idx) => {
                  const r = roleById(rid);
                  return (
                    <div key={rid} style={{
                      display: "flex", alignItems: "center", gap: 4,
                      padding: "2px 6px", marginBottom: 2,
                      background: "#fff", borderRadius: 4, border: "1px solid #f0f0f0",
                    }}>
                      <span style={{ fontSize: 11, color: "#bfbfbf", width: 14 }}>{idx + 1}</span>
                      <span style={{ flex: 1, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r?.name || rid}</span>
                      {flowType === "sequential" && (
                        <>
                          <Button size="small" type="text" disabled={idx === 0}
                            onClick={() => moveRole(idx, -1)} style={{ height: 20, padding: "0 2px", fontSize: 11 }}>↑</Button>
                          <Button size="small" type="text" disabled={idx === selectedRoles.length - 1}
                            onClick={() => moveRole(idx, 1)} style={{ height: 20, padding: "0 2px", fontSize: 11 }}>↓</Button>
                        </>
                      )}
                      <Button size="small" type="text" danger icon={<DeleteOutlined />}
                        onClick={() => toggleRole(rid)} style={{ height: 20, padding: "0 2px" }} />
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Right — role picker with tab switching */}
          <div style={{ minWidth: 0 }}>
            {/* Tab switcher */}
            <div style={{ display: "flex", gap: 4, marginBottom: 8, flexWrap: "wrap", alignItems: "center" }}>
              {skillTabs.map((t) => (
                <Button
                  key={t.id}
                  size="small"
                  type={activeTab === t.id ? "primary" : "default"}
                  onClick={() => handleTabSwitch(t.id)}
                  style={{ fontSize: 12 }}
                >
                  {t.name}
                </Button>
              ))}
              <Button
                size="small"
                type="dashed"
                icon={<PlusOutlined />}
                onClick={() => setImportModalOpen(true)}
                style={{ fontSize: 12 }}
              >
                新增
              </Button>
            </div>

            <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
              <Input
                size="small"
                prefix={<SearchOutlined />}
                placeholder="搜索角色"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                allowClear
                style={{ flex: 1 }}
              />
              <Select
                size="small"
                value={filterCategory}
                onChange={setFilterCategory}
                style={{ width: 100 }}
                options={[
                  { value: "all", label: "全部分类" },
                  ...CATEGORY_ORDER.map((c) => ({ value: c, label: CATEGORY_LABELS[c] })),
                ]}
              />
            </div>

            <div style={{ border: "1px solid #f0f0f0", borderRadius: 6, padding: 4, height: 400, overflow: "auto" }}>
              {activeTab === "software-engineering" ? (
                /* Gstack roles (builtin) */
                filteredRoles.length === 0 ? (
                  <Empty description="无匹配角色" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 60 }} />
                ) : (
                  CATEGORY_ORDER.filter((c) => rolesByCategory[c]?.length).map((c) => (
                    <div key={c} style={{ marginBottom: 6 }}>
                      <div style={{
                        fontSize: 11, color: "#8c8c8c", padding: "1px 6px",
                        background: "#fafafa", borderRadius: 4, marginBottom: 2,
                      }}>
                        {CATEGORY_LABELS[c]} · {rolesByCategory[c].length}
                      </div>
                      {rolesByCategory[c].map((r) => {
                        const checked = selectedRoles.includes(r.id);
                        return (
                          <Tooltip key={r.id} title={r.description} placement="left">
                            <div style={{
                              display: "flex", alignItems: "center", gap: 4,
                              padding: "2px 6px", borderRadius: 4, cursor: "pointer",
                              background: checked ? "#e6f4ff" : "transparent",
                            }}>
                              <Checkbox
                                checked={checked}
                                onChange={() => toggleRole(r.id)}
                              />
                              <span style={{ flex: 1, fontSize: 12, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.name}</span>
                            </div>
                          </Tooltip>
                        );
                      })}
                    </div>
                  ))
                )
              ) : (
                /* Tab roles (imported from GitHub) */
                tabRoles.length === 0 ? (
                  <Empty description="该 Tab 暂无角色" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 60 }} />
                ) : (
                  ["planning", "implementation"].map((cls) => {
                    const clsRoles = tabRoles.filter((r) => r.classification === cls);
                    if (clsRoles.length === 0) return null;
                    return (
                      <div key={cls} style={{ marginBottom: 6 }}>
                        <div style={{
                          fontSize: 11, color: "#8c8c8c", padding: "1px 6px",
                          background: "#fafafa", borderRadius: 4, marginBottom: 2,
                        }}>
                          {cls === "planning" ? "规划" : "实现"} · {clsRoles.length}
                        </div>
                        {clsRoles.map((r) => {
                          const checked = selectedRoles.includes(r.role_id);
                          return (
                            <Tooltip key={r.id} title={r.description} placement="left">
                              <div style={{
                                display: "flex", alignItems: "center", gap: 4,
                                padding: "2px 6px", borderRadius: 4, cursor: "pointer",
                                background: checked ? "#e6f4ff" : "transparent",
                              }}>
                                <Checkbox
                                  checked={checked}
                                  onChange={() => toggleRole(r.role_id)}
                                />
                                <span style={{ flex: 1, fontSize: 12, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                  {r.display_name || r.role_id}
                                </span>
                                <Tag style={{ fontSize: 10, lineHeight: "16px", margin: 0 }} color={cls === "planning" ? "blue" : "green"}>
                                  {r.category}
                                </Tag>
                              </div>
                            </Tooltip>
                          );
                        })}
                      </div>
                    );
                  })
                )
              )}
            </div>
          </div>
        </div>
      </Modal>

      {/* Import Modal */}
      <ImportSkillModal
        open={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onSuccess={loadAll}
      />
    </div>
  );
}
