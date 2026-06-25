import { Suspense, lazy, useState, useEffect, useCallback } from "react";
import {
  Avatar, Button, Switch, Tag, Collapse, Empty, Tooltip,
  Input, Popconfirm, message, Spin, Modal, Descriptions,
} from "antd";
import {
  PlusOutlined, DeleteOutlined, ExperimentOutlined,
  LogoutOutlined, LoginOutlined, ReloadOutlined,
  CheckCircleFilled, CloseCircleFilled, WarningFilled,
  RobotOutlined, MenuOutlined,
  MessageOutlined, DownOutlined, RightOutlined,
  EditOutlined, UserOutlined, ClearOutlined,
  SettingOutlined, ShopOutlined, ApartmentOutlined,
  UploadOutlined, NodeIndexOutlined, SearchOutlined,
} from "@ant-design/icons";
import { useAppStore } from "./stores/appStore";
import { authApi, skillApi, conversationApi, adminApi, chatApi } from "./services/api";
import ChatPanel from "./components/ChatPanel";
import LoginModal from "./components/LoginModal";
import type { Skill, Conversation, UserProfile, LlmProvider } from "./types";

const MarketSidebar = lazy(() => import("./components/MarketSidebar"));
const AgentMarketPage = lazy(() => import("./components/AgentMarketPage"));
const FlowsPage = lazy(() => import("./components/FlowsPage"));
const KnowledgeGraphPage = lazy(() => import("./components/KnowledgeGraphPage"));

const SKILL_ZH: Record<string, { name: string; description: string }> = {
  "3-statement-model": { name: "三大财务报表模型", description: "填充并联动利润表、资产负债表和现金流量表模板。" },
  "academic-paper": { name: "学术论文写作", description: "多智能体论文写作流水线，支持大纲、修订、摘要、文献综述、引用检查和格式转换。" },
  "academic-paper-reviewer": { name: "学术论文评审", description: "模拟主编、同行评审和反方审稿人，从多角度评审论文质量。" },
  "academic-pipeline": { name: "学术研究全流程", description: "串联研究、写作、诚信检查、评审、修订和最终定稿的端到端论文流程。" },
  "accrual-schedule": { name: "计提明细表", description: "生成期末计提明细、计算分录并引用支持材料。" },
  "audit-xls": { name: "Excel 公式审计", description: "检查电子表格公式、平衡关系、现金流勾稽和模型逻辑错误。" },
  brainstorming: { name: "需求头脑风暴", description: "在创意、功能或行为变更前澄清意图、需求和设计方向。" },
  "break-trace": { name: "差异追踪", description: "沿审计轨迹追踪对账差异到源交易或入账记录。" },
  "client-report": { name: "客户报告", description: "生成客户沟通和会议使用的专业报告材料。" },
  "client-review": { name: "客户资料审阅", description: "审阅客户材料，提炼风险点、机会和待确认事项。" },
  "competitive-analysis": { name: "竞争格局分析", description: "构建竞品研究、市场定位、同业对比和战略洞察。" },
  "comps-analysis": { name: "可比公司分析", description: "整理可比公司、估值倍数和同业基准分析。" },
  "dcf-model": { name: "DCF 估值模型", description: "基于现金流预测、WACC 和敏感性分析构建 DCF 估值模型。" },
  "deck-refresh": { name: "演示文稿数据刷新", description: "用最新季度、财务或市场数据更新既有演示文稿。" },
  "deep-research": { name: "深度研究", description: "多智能体严谨研究流程，支持文献综述、事实核查、系统综述和研究报告。" },
  "dispatching-parallel-agents": { name: "并行智能体调度", description: "将多个互不依赖的任务分派给并行智能体执行。" },
  "earnings-analysis": { name: "财报业绩分析", description: "生成季度业绩更新报告，分析超预期/低预期、关键指标和投资观点变化。" },
  "earnings-preview": { name: "财报前瞻", description: "在财报发布前整理市场预期、关键指标、催化剂和风险点。" },
  "executing-plans": { name: "执行实施计划", description: "根据已批准的实施计划分阶段执行，并在检查点复核。" },
  "famou-experiment-manager": { name: "Famou 实验管理", description: "提交、查看、删除和获取 Famou 平台实验及配置。" },
  "finishing-a-development-branch": { name: "开发分支收尾", description: "在实现和测试完成后，辅助选择合并、PR 或清理方案。" },
  "gl-recon": { name: "总账对账", description: "按交易日或期间核对总账与明细账，识别并分类差异。" },
  "ib-check-deck": { name: "投行材料质检", description: "检查 Pitch Deck 的数字一致性、叙事匹配、语言和版式质量。" },
  "ic-memo": { name: "投委会备忘录", description: "生成投资委员会审议所需的交易、估值、风险和建议材料。" },
  "idea-generation": { name: "投资想法生成", description: "围绕行业、公司或主题生成可研究的投资想法。" },
  "investment-proposal": { name: "投资建议书", description: "生成面向客户或内部审批的投资建议和论证材料。" },
  "kyc-doc-parse": { name: "KYC 文件解析", description: "从开户或尽调材料中抽取身份、受益所有人、资金来源和文件清单。" },
  "kyc-rules": { name: "KYC/AML 规则评分", description: "根据规则网格对 KYC 记录评级、列出命中规则并标记缺失项。" },
  "lbo-model": { name: "LBO 杠杆收购模型", description: "填充和校验私募股权交易的 LBO Excel 模型模板。" },
  "model-update": { name: "模型更新", description: "根据最新数据和假设更新财务模型。" },
  "morning-note": { name: "晨会纪要", description: "生成市场、行业和公司动态晨会材料。" },
  "nav-tieout": { name: "NAV 勾稽", description: "将 LP 报表与基金 NAV 包重新计算勾稽并标记不一致项目。" },
  "pitch-deck": { name: "Pitch Deck 填充", description: "把 Excel/CSV 等源数据填入既有投行演示文稿模板。" },
  "portfolio-monitoring": { name: "组合监控", description: "跟踪投资组合表现、风险暴露、估值和关键事件。" },
  "pptx-author": { name: "PPTX 文件生成", description: "在无 Office 界面的环境中生成 .pptx 文件。" },
  "receiving-code-review": { name: "处理代码评审", description: "在实现评审意见前进行技术核验，避免盲目修改。" },
  "requesting-code-review": { name: "请求代码评审", description: "在任务完成或合并前检查实现是否满足要求。" },
  "returns-analysis": { name: "收益归因分析", description: "分析投资回报、收益来源、风险调整表现和驱动因素。" },
  "roll-forward": { name: "余额滚动表", description: "生成期初余额、期间活动、转回和期末余额的滚动明细。" },
  "sector-overview": { name: "行业概览", description: "生成行业规模、格局、趋势、驱动因素和风险综述。" },
  "skill-creator": { name: "技能创建器", description: "创建、修改和优化平台技能，并校验技能结构和说明。" },
  stock_analysis_with_api: { name: "股票综合分析", description: "结合基本面、技术面、估值和量化信号进行股票分析。" },
  "subagent-driven-development": { name: "子智能体驱动开发", description: "用多个子智能体执行当前会话中的独立开发任务。" },
  "systematic-debugging": { name: "系统化调试", description: "遇到 bug、测试失败或异常行为时进行结构化排查。" },
  "test-driven-development": { name: "测试驱动开发", description: "在实现功能或修复缺陷前先设计测试与验收条件。" },
  "using-git-worktrees": { name: "Git Worktree 隔离开发", description: "为功能开发创建隔离工作区，避免污染当前工作树。" },
  "using-superpowers": { name: "技能使用规范", description: "建立技能发现和调用规则，确保在合适场景使用专业技能。" },
  "variance-commentary": { name: "差异分析评论", description: "为损益表和资产负债表差异撰写管理层解释。" },
  "verification-before-completion": { name: "完成前验证", description: "在宣称完成、修复或通过前运行验证命令并提供证据。" },
  "writing-plans": { name: "编写实施计划", description: "在动手改代码前为多步骤任务编写清晰计划。" },
  "writing-skills": { name: "编写技能", description: "创建、编辑和验证技能的完整工作流。" },
  "xlsx-author": { name: "XLSX 文件生成", description: "在无 Excel 界面的环境中生成 .xlsx 工作簿文件。" },
};

const humanizeSkillName = (name: string) =>
  name.replace(/[-_]+/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase());

const skillDisplayName = (skill: Skill) => SKILL_ZH[skill.name]?.name || humanizeSkillName(skill.name);
const skillDisplayDescription = (skill: Skill) => SKILL_ZH[skill.name]?.description || skill.description || "暂无中文说明";
const displayConversationTitle = (title: string) => {
  const cleaned = (title || "").replace(/^\[智能搜索 \/ GraphRAG\]\s*/u, "").replace(/\s+/g, " ").trim();
  const chars = [...cleaned];
  const bad = chars.filter((ch) => ch === "?" || ch === "\uFFFD").length;
  return !cleaned || (bad >= 3 && bad * 2 >= chars.length) ? "新对话" : cleaned;
};
const toolDisplayName = (name: string) => {
  if (name.endsWith("_run")) return "运行技能";
  if (name.endsWith("_ref")) return "查看参考资料";
  return humanizeSkillName(name);
};
const toolDisplayDescription = (tool: { name: string; description: string }) => {
  if (tool.name.endsWith("_run")) return "执行该技能的主流程。";
  if (tool.name.endsWith("_ref")) return "读取该技能的说明、参考资料或配置。";
  return tool.description || "暂无中文说明";
};

export default function App() {
  const {
    user, token, logout, setAuth,
    skills, setSkills, selectedSkill, setSelectedSkill,
    conversations, setConversations, currentConversationId,
    setCurrentConversationId, removeConversation, updateConversationTitle,
    clearMessages, addMessage: _addMessage, setMessages,
    theme, toggleTheme,
  } = useAppStore();

  const [loginOpen, setLoginOpen] = useState(false);
  const [loadingSkill, setLoadingSkill] = useState<string | null>(null);
  const [showAddInput, setShowAddInput] = useState(false);
  const [addPath, setAddPath] = useState("");
  const [adding, setAdding] = useState(false);
  const [uploadingZip, setUploadingZip] = useState(false);
  const [loadingSkills, setLoadingSkills] = useState(false);
  const [activeTab, setActiveTab] = useState<"chat" | "skills" | "market" | "flows" | "knowledge">("chat");
  const [skillGroupOpen, setSkillGroupOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Vertical agents navigation
  const [marketSidebarCollapsed, setMarketSidebarCollapsed] = useState(false);
  const [marketActiveKey, setMarketActiveKey] = useState("project-management");

  // Conversation rename state
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");

  // User profile modal
  const [profileOpen, setProfileOpen] = useState(false);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [clearingProfile, setClearingProfile] = useState(false);

  // Admin LLM provider management
  const [adminOpen, setAdminOpen] = useState(false);
  const [adminProviders, setAdminProviders] = useState<LlmProvider[]>([]);
  const [adminStaticCount, setAdminStaticCount] = useState(0);
  const [adminLoading, setAdminLoading] = useState(false);
  const [newProvider, setNewProvider] = useState<Partial<LlmProvider>>({ id: "", name: "", base_url: "", api_key: "", models: [""] });

  const loadAdminProviders = useCallback(async () => {
    setAdminLoading(true);
    try {
      const res = await adminApi.listProviders();
      setAdminProviders(res.providers);
      setAdminStaticCount(res.static_count ?? 0);
    } catch { /* ignore */ } finally {
      setAdminLoading(false);
    }
  }, []);

  const openAdminPanel = () => {
    setAdminOpen(true);
    loadAdminProviders();
  };

  useEffect(() => {
    const onAuthExpired = () => {
      logout();
      setLoginOpen(true);
      message.warning("登录已过期，请重新登录");
    };
    window.addEventListener("agent-platform:auth-expired", onAuthExpired);
    return () => window.removeEventListener("agent-platform:auth-expired", onAuthExpired);
  }, [logout]);

  const handleAddProvider = async () => {
    if (!newProvider.id || !newProvider.name || !newProvider.base_url || !newProvider.api_key || !newProvider.models?.filter(Boolean).length) return;
    try {
      await adminApi.addProvider({
        id: newProvider.id!,
        name: newProvider.name!,
        base_url: newProvider.base_url!,
        api_key: newProvider.api_key!,
        custom_header: newProvider.custom_header || "",
        models: newProvider.models!.filter(Boolean),
      });
      setNewProvider({ id: "", name: "", base_url: "", api_key: "", models: [""] });
      await loadAdminProviders();
      // Refresh providers in the store for the chat selector
      chatApi.listProviders().then((r) => useAppStore.getState().setProviders(r.providers)).catch(() => {});
      message.success("添加成功");
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : "添加失败");
    }
  };

  const handleDeleteProvider = async (id: string) => {
    try {
      await adminApi.deleteProvider(id);
      await loadAdminProviders();
      chatApi.listProviders().then((r) => useAppStore.getState().setProviders(r.providers)).catch(() => {});
      message.success("删除成功");
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : "删除失败");
    }
  };

  // Auto-login only in local development. Production should always require an
  // explicit login or an existing token.
  useEffect(() => {
    if (localStorage.getItem("token")) return;
    const host = window.location.hostname;
    const isLocalhost = host === "localhost" || host === "127.0.0.1" || host === "::1";
    if (!isLocalhost) return;

    authApi.devLogin().then((res) => {
      setAuth(
        { id: res.user.id, nickname: res.user.nickname, membership_tier: res.user.membership_tier || "free", role: res.user.role || "admin" },
        res.access_token,
      );
    }).catch(() => {
      // Dev-login failed (not in debug mode) — user needs to login manually
    });
  }, []);

  // Load conversations when user logs in
  const loadConversations = useCallback(async () => {
    if (!token) return;
    try {
      const convs = await conversationApi.list();
      setConversations(convs);
    } catch { /* ignore */ }
  }, [token]);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  const loadSkills = useCallback(async () => {
    if (!token) return;
    setLoadingSkills(true);
    try {
      const res = await skillApi.list();
      setSkills(res.skills || []);
    } catch { /* ignore — silently fail if not authed */ } finally {
      setLoadingSkills(false);
    }
  }, [token]);

  useEffect(() => { loadSkills(); }, [loadSkills]);

  /* ── Conversation actions ── */

  const handleNewConversation = () => {
    setCurrentConversationId(null);
    clearMessages();
  };

  const handleSelectConversation = async (conv: Conversation) => {
    if (currentConversationId === conv.id) return;
    setCurrentConversationId(conv.id);
    clearMessages();
    setMobileMenuOpen(false);
    // Load message history from backend (batch set to avoid O(n²) array copies)
    try {
      const msgs = await conversationApi.messages(conv.id);
      const chatMsgs = msgs
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({
          id: `hist-${conv.id}-${m.id}`,
          role: m.role as "user" | "assistant",
          content: m.content || "",
          timestamp: new Date(m.created_at).getTime(),
          fileDownloads: m.file_downloads || undefined,
        }));
      setMessages(chatMsgs);
    } catch { /* ignore — messages stay empty */ }
  };

  /** Reload messages for the currently open conversation (used by ChatPanel refresh button) */
  const reloadCurrentMessages = useCallback(async () => {
    if (!currentConversationId) return;
    try {
      const msgs = await conversationApi.messages(currentConversationId);
      const chatMsgs = msgs
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({
          id: `hist-${currentConversationId}-${m.id}`,
          role: m.role as "user" | "assistant",
          content: m.content || "",
          timestamp: new Date(m.created_at).getTime(),
          fileDownloads: m.file_downloads || undefined,
        }));
      setMessages(chatMsgs);
      // Scroll to bottom after messages load
      setTimeout(() => {
        const el = document.querySelector(".chat-area") as HTMLElement | null;
        if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
      }, 120);
    } catch { /* ignore */ }
  }, [currentConversationId, setMessages]);

  const clearCurrentContext = useCallback(async () => {
    if (!currentConversationId) return;
    try {
      await conversationApi.clearMessages(currentConversationId);
      clearMessages();
      message.success("已清除当前会话上下文");
    } catch (err) {
      message.error("清除失败: " + (err instanceof Error ? err.message : "未知错误"));
    }
  }, [currentConversationId, clearMessages]);

  const handleDeleteConversation = async (id: number) => {
    try {
      await conversationApi.remove(id);
      removeConversation(id);
      message.success("已删除");
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : "删除失败");
    }
  };

  const handleStartRename = (conv: Conversation) => {
    setRenamingId(conv.id);
    setRenameValue(conv.title);
  };

  const handleConfirmRename = async (id: number) => {
    const title = renameValue.trim();
    if (!title) { setRenamingId(null); return; }
    try {
      await conversationApi.rename(id, title);
      updateConversationTitle(id, title);
    } catch { /* ignore */ } finally {
      setRenamingId(null);
    }
  };

  /* ── User profile (long-term memory) ── */

  const openUserProfile = async () => {
    setProfileOpen(true);
    setProfileLoading(true);
    try {
      const res = await conversationApi.getUserProfile();
      // API nests memory data under res.profile.memory
      setUserProfile(res.profile?.memory ?? null);
    } catch { setUserProfile(null); } finally {
      setProfileLoading(false);
    }
  };

  const handleClearProfile = async () => {
    setClearingProfile(true);
    try {
      await conversationApi.clearUserProfile();
      setUserProfile(null);
      message.success("记忆已清除");
    } catch { /* ignore */ } finally {
      setClearingProfile(false);
    }
  };

  /* ── Skills ── */

  const toggleSkill = async (name: string, enable: boolean) => {
    setLoadingSkill(name);
    try {
      if (enable) await skillApi.enable(name);
      else {
        await skillApi.disable(name);
        if (selectedSkill === name) setSelectedSkill(null);
      }
      await loadSkills();
    } catch { /* ignore */ } finally {
      setLoadingSkill(null);
    }
  };

  const handleAddSkill = async () => {
    const path = addPath.trim();
    if (!path) return;
    setAdding(true);
    try {
      const result = await skillApi.add(path);
      await loadSkills();
      const v = (result as unknown as Record<string, unknown>).validation as {
        fixed?: boolean; issues?: string[]; fixes?: string[];
      } | undefined;
      if (v?.fixed && v.fixes?.length) {
        message.warning({ content: `技能添加成功，已自动修复 ${v.fixes.length} 个问题`, duration: 5 });
      } else {
        message.success("技能添加成功");
      }
      setAddPath(""); setShowAddInput(false);
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : "添加失败");
    } finally {
      setAdding(false);
    }
  };

  const handleUploadZip = async (file: File) => {
    setUploadingZip(true);
    try {
      await skillApi.uploadZip(file);
      await loadSkills();
      message.success(`技能包 "${file.name}" 上传成功`);
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : "上传失败");
    } finally {
      setUploadingZip(false);
    }
  };

  const handleRemoveSkill = async (name: string) => {
    try {
      await skillApi.remove(name);
      message.success(`已移除：${name}`);
      if (selectedSkill === name) setSelectedSkill(null);
      await loadSkills();
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : "移除失败");
    }
  };

  const enabledCount = (skills || []).filter((s) => s.enabled).length;

  const renderSkillItem = (skill: Skill) => {
    const isSelected = selectedSkill === skill.name;
    return (
      <div
        key={skill.name}
        className={`skill-item${isSelected ? " selected" : ""}${!skill.enabled ? " disabled" : ""}`}
        onClick={() => { if (skill.enabled) setSelectedSkill(isSelected ? null : skill.name); }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <Tooltip title={skill.name !== skillDisplayName(skill) ? skill.name : undefined}>
            <div className="skill-item-name">{skillDisplayName(skill)}</div>
          </Tooltip>
          <div style={{ display: "flex", alignItems: "center", gap: 4, flexShrink: 0, marginLeft: 6 }}>
            <Switch
              size="small"
              checked={skill.enabled}
              loading={loadingSkill === skill.name}
              onClick={(_, e) => { e.stopPropagation(); toggleSkill(skill.name, !skill.enabled); }}
            />
            <Popconfirm
              title="确认移除该技能？"
              onConfirm={(e) => { e?.stopPropagation(); handleRemoveSkill(skill.name); }}
              onCancel={(e) => e?.stopPropagation()}
              okText="移除" cancelText="取消"
            >
              <Button type="text" size="small" danger icon={<DeleteOutlined />}
                onClick={(e) => e.stopPropagation()}
                style={{ fontSize: 11, padding: "0 4px", height: 20 }} />
            </Popconfirm>
          </div>
        </div>
        <div className="skill-item-desc">{skillDisplayDescription(skill)}</div>
        <div className="skill-item-meta">
          <Tag style={{ fontSize: 10, lineHeight: "16px", margin: 0 }}>v{skill.version}</Tag>
          {skill.enabled && skill.config_ok && <CheckCircleFilled style={{ color: "#52c41a", fontSize: 11 }} />}
          {skill.enabled && !skill.config_ok && <WarningFilled style={{ color: "#faad14", fontSize: 11 }} />}
          {!skill.enabled && <CloseCircleFilled style={{ color: "#bfbfbf", fontSize: 11 }} />}
          <span style={{ fontSize: 11, color: "#bfbfbf", marginLeft: "auto" }}>
            {skill.tools.length} 个工具
          </span>
        </div>
        {isSelected && skill.tools.length > 0 && (
          <Collapse size="small" ghost style={{ marginTop: 4 }}
            items={skill.tools.map((t) => ({
              key: t.name,
              label: <span style={{ fontSize: 12 }}>{toolDisplayName(t.name)}</span>,
              children: <span style={{ fontSize: 11, color: "#8c8c8c" }}>{toolDisplayDescription(t)}</span>,
            }))}
          />
        )}
      </div>
    );
  };

  /* ── Sidebar content by active tab ── */
  const renderSidebarBody = () => {
    if (activeTab === "chat") {
      return (
        <div className="sidebar-body">
          {/* New conversation button */}
          <div style={{ padding: "8px 12px 4px" }}>
            <Button
              type="dashed"
              size="small"
              icon={<PlusOutlined />}
              block
              onClick={handleNewConversation}
              style={{ fontSize: 12 }}
            >
              新对话
            </Button>
          </div>

          <div className="nav-group-title" style={{ fontSize: 11, marginTop: 4 }}>
            <span>历史对话</span>
            <div style={{ display: "flex", gap: 2 }}>
              <Tooltip title="刷新">
                <Button type="text" size="small" icon={<ReloadOutlined />}
                  onClick={loadConversations}
                  style={{ fontSize: 11, padding: "0 2px", height: 18 }} />
              </Tooltip>
              {conversations.length > 0 && (
                <Popconfirm
                  title="确认清空所有会话？"
                  description="此操作不可恢复"
                  onConfirm={async () => {
                    try {
                      await conversationApi.deleteAll();
                      setConversations([]);
                      setCurrentConversationId(null);
                      clearMessages();
                      message.success("已清空所有会话");
                    } catch { message.error("清空失败"); }
                  }}
                  okText="确认清空"
                  cancelText="取消"
                  okButtonProps={{ danger: true }}
                >
                  <Tooltip title="清空所有会话">
                    <Button type="text" size="small" danger icon={<DeleteOutlined />}
                      style={{ fontSize: 11, padding: "0 2px", height: 18 }} />
                  </Tooltip>
                </Popconfirm>
              )}
            </div>
          </div>

          {(conversations || []).length === 0 ? (
            <div style={{ padding: "16px 12px", textAlign: "center" }}>
              <Empty description="暂无历史对话" image={Empty.PRESENTED_IMAGE_SIMPLE}
                style={{ margin: 0 }} styles={{ image: { height: 32 } }} />
            </div>
          ) : (
            (conversations || []).map((conv) => (
              <div
                key={conv.id}
                className={`nav-item${currentConversationId === conv.id ? " active" : ""}`}
                onClick={() => handleSelectConversation(conv)}
                style={{ alignItems: "flex-start", gap: 6, paddingRight: 6 }}
              >
                <MessageOutlined className="nav-item-icon" style={{ marginTop: 2, flexShrink: 0 }} />

                {renamingId === conv.id ? (
                  <Input
                    size="small"
                    value={renameValue}
                    autoFocus
                    onChange={(e) => setRenameValue(e.target.value)}
                    onBlur={() => handleConfirmRename(conv.id)}
                    onPressEnter={() => handleConfirmRename(conv.id)}
                    onClick={(e) => e.stopPropagation()}
                    style={{ flex: 1, fontSize: 12, height: 22 }}
                  />
                ) : (
                  <span className="nav-item-text" style={{
                    flex: 1,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    fontSize: 12,
                  }}>
                    {displayConversationTitle(conv.title)}
                  </span>
                )}

                {/* Action buttons — only visible on hover or when active */}
                {renamingId !== conv.id && (
                  <div className="conv-actions" onClick={(e) => e.stopPropagation()}
                    style={{ display: "flex", gap: 2, flexShrink: 0 }}>
                    <Tooltip title="重命名">
                      <Button type="text" size="small" icon={<EditOutlined />}
                        onClick={() => handleStartRename(conv)}
                        style={{ fontSize: 11, padding: "0 2px", height: 18, color: "#8c8c8c" }} />
                    </Tooltip>
                    <Popconfirm
                      title="确认删除该对话？"
                      onConfirm={() => handleDeleteConversation(conv.id)}
                      okText="删除" cancelText="取消"
                      placement="right"
                    >
                      <Button type="text" size="small" danger icon={<DeleteOutlined />}
                        style={{ fontSize: 11, padding: "0 2px", height: 18 }} />
                    </Popconfirm>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      );
    }

    // Skills tab
    return (
      <div className="sidebar-body">
        {/* Group header */}
        <div
          className="nav-group-title"
          onClick={() => setSkillGroupOpen(!skillGroupOpen)}
          style={{ cursor: "pointer" }}
        >
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {skillGroupOpen ? <DownOutlined style={{ fontSize: 10 }} /> : <RightOutlined style={{ fontSize: 10 }} />}
            技能列表
          </span>
          <span style={{ fontSize: 11, color: "#bfbfbf", fontWeight: 400 }}>
            {enabledCount}/{skills.length}
          </span>
        </div>

        {skillGroupOpen && (
          <>
            <div style={{ padding: "0 12px 6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 12, color: "#8c8c8c" }}>
                {enabledCount} 个已启用
              </span>
              <div style={{ display: "flex", gap: 2 }}>
                <Tooltip title="刷新">
                  <Button type="text" size="small" icon={<ReloadOutlined />}
                    loading={loadingSkills} onClick={loadSkills}
                    style={{ fontSize: 12, padding: "0 4px", height: 22 }} />
                </Tooltip>
                <Tooltip title="添加技能">
                  <Button type="text" size="small" icon={<PlusOutlined />}
                    onClick={() => setShowAddInput(!showAddInput)}
                    style={{ fontSize: 12, padding: "0 4px", height: 22 }} />
                </Tooltip>
              </div>
            </div>

            {showAddInput && (
              <div style={{ padding: "0 12px 8px" }}>
                <Input.Search
                  placeholder="技能目录路径"
                  value={addPath}
                  onChange={(e) => setAddPath(e.target.value)}
                  onSearch={handleAddSkill}
                  loading={adding}
                  enterButton="添加"
                  size="small"
                />
                <div style={{ marginTop: 6 }}>
                  <Button
                    size="small"
                    icon={<UploadOutlined />}
                    loading={uploadingZip}
                    onClick={() => {
                      const input = document.createElement("input");
                      input.type = "file";
                      input.accept = ".zip";
                      input.onchange = (e) => {
                        const f = (e.target as HTMLInputElement).files?.[0];
                        if (f) handleUploadZip(f);
                      };
                      input.click();
                    }}
                    block
                  >
                    上传 Zip 技能包
                  </Button>
                </div>
              </div>
            )}

            {loadingSkills ? (
              <div style={{ textAlign: "center", padding: 20 }}><Spin size="small" /></div>
            ) : skills.length === 0 ? (
              <Empty description="暂无技能" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 20 }} />
            ) : (
              skills.map(renderSkillItem)
            )}
          </>
        )}

        {selectedSkill && (
          <div style={{ padding: "8px 16px", borderTop: "1px solid #f0f0f0", fontSize: 12, color: "#2468f2" }}>
            当前技能：<strong>{skillDisplayName(skills.find((s) => s.name === selectedSkill) || { name: selectedSkill, description: "", version: "", author: "", license: "", keywords: [], dependencies: [], tools: [], requires_config: [], optional_config: [], enabled: true, config_ok: true, path: "" })}</strong>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`app-layout app-tab-${activeTab}`}>
      {/* ── Top Header ── */}
      <header className="app-header">
        <div className="header-logo">
          <div className="header-logo-icon">
            <RobotOutlined />
          </div>
          <div className="header-logo-copy">
            <span className="header-logo-kicker">Agent Platform</span>
            <span className="header-logo-text">数字员工仿真平台</span>
          </div>
        </div>

        <nav className="header-tabs">
          <div
            className={`header-tab${activeTab === "chat" ? " active" : ""}`}
            onClick={() => setActiveTab("chat")}
          >
            <MessageOutlined style={{ fontSize: 13 }} />
            对话
          </div>
          <div
            className={`header-tab${activeTab === "skills" ? " active" : ""}`}
            onClick={() => setActiveTab("skills")}
          >
            <ExperimentOutlined style={{ fontSize: 13 }} />
            技能管理
            {enabledCount > 0 && <span className="header-tab-dot" />}
          </div>
          <div
            className={`header-tab${activeTab === "flows" ? " active" : ""}`}
            onClick={() => setActiveTab("flows")}
          >
            <ApartmentOutlined style={{ fontSize: 13 }} />
            多智能体
          </div>
          <div
            className={`header-tab${activeTab === "market" ? " active" : ""}`}
            onClick={() => setActiveTab("market")}
          >
            <ShopOutlined style={{ fontSize: 13 }} />
            垂类智能体
          </div>
          <div
            className={`header-tab${activeTab === "knowledge" ? " active" : ""}`}
            onClick={() => setActiveTab("knowledge")}
          >
            <NodeIndexOutlined style={{ fontSize: 13 }} />
            知识图谱
          </div>
        </nav>

        <div className="header-actions">
          <div className="header-search">
            <SearchOutlined />
            <span>搜索流程、Skill、知识实体或运行记录</span>
          </div>
          <span className={`header-status-pill${token ? "" : " muted"}`}>
            <span className="status-dot" />
            {token ? "Provider 已连接" : "未登录"}
          </span>
          <Button
            type="text" size="small" icon={<MenuOutlined />}
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            style={{ display: "none" }}
            className="mobile-menu-btn"
          />

          <Tooltip title={theme === "dark" ? "切换亮色模式" : "切换暗色模式"}>
            <button className="theme-toggle" onClick={toggleTheme}>
              <span className="theme-toggle-mark">{theme === "dark" ? "亮" : "暗"}</span>
            </button>
          </Tooltip>

          {user?.role === "admin" && (
            <Tooltip title="LLM 配置管理">
              <Button type="text" size="small" icon={<SettingOutlined />}
                onClick={openAdminPanel}
                style={{ color: "#8c8c8c" }} />
            </Tooltip>
          )}

          {user ? (
            <div className="header-user">
              <Tooltip title="查看记忆档案">
                <Avatar
                  size={24}
                  style={{ background: "linear-gradient(135deg,#2468f2,#4d8bf5)", fontSize: 12, flexShrink: 0, cursor: "pointer" }}
                  onClick={openUserProfile}
                >
                  {(user.nickname || "U")[0].toUpperCase()}
                </Avatar>
              </Tooltip>
              <span className="header-user-name">{user.nickname}</span>
              <span className="header-user-role">{user.role === "admin" ? "Admin" : "User"}</span>
              <Tooltip title="退出登录">
                <Button type="text" size="small" icon={<LogoutOutlined />}
                  onClick={logout} style={{ color: "#8c8c8c", padding: "0 4px" }} />
              </Tooltip>
            </div>
          ) : (
            <Button type="primary" size="small" icon={<LoginOutlined />}
              onClick={() => setLoginOpen(true)}>
              登录
            </Button>
          )}
        </div>
      </header>

      {/* ── Body ── */}
      <div className="app-body">
        {activeTab !== "market" && activeTab !== "flows" && activeTab !== "knowledge" && (
          <>
            <div className={`sidebar-overlay${mobileMenuOpen ? " active" : ""}`}
              onClick={() => setMobileMenuOpen(false)} />
            <div className={`sidebar${mobileMenuOpen ? " open" : ""}`}>
              {renderSidebarBody()}
              <div className="sidebar-footer">
                {user ? (
                  <div className="sidebar-user">
                    <Tooltip title="查看记忆档案">
                      <Avatar size={28}
                        style={{ background: "linear-gradient(135deg,#2468f2,#4d8bf5)", fontSize: 12, flexShrink: 0, cursor: "pointer" }}
                        onClick={openUserProfile}
                      >
                        {(user.nickname || "U")[0].toUpperCase()}
                      </Avatar>
                    </Tooltip>
                    <div className="sidebar-user-info">
                      <div className="sidebar-user-name">{user.nickname}</div>
                      <div className="sidebar-user-tier">{user.membership_tier || "free"}</div>
                    </div>
                    <Tooltip title="退出登录">
                      <Button type="text" size="small" icon={<LogoutOutlined />}
                        onClick={logout} style={{ color: "#bfbfbf", padding: "0 4px" }} />
                    </Tooltip>
                  </div>
                ) : (
                  <Button type="primary" size="small" icon={<LoginOutlined />}
                    onClick={() => setLoginOpen(true)} block>
                    登录
                  </Button>
                )}
              </div>
            </div>
          </>
        )}

        {activeTab === "market" ? (
          <Suspense fallback={<div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}><Spin /></div>}>
            <MarketSidebar
              collapsed={marketSidebarCollapsed}
              onToggleCollapse={() => setMarketSidebarCollapsed(!marketSidebarCollapsed)}
              activeKey={marketActiveKey}
              onSelect={setMarketActiveKey}
            />
            <AgentMarketPage
              activeCategory={
                marketActiveKey === "tech-development"
                  ? "技术开发"
                  : marketActiveKey === "deployment-ops"
                    ? "部署运维"
                    : "项目管理"
              }
            />
          </Suspense>
        ) : activeTab === "flows" ? (
          <Suspense fallback={<div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}><Spin /></div>}>
            <FlowsPage />
          </Suspense>
        ) : activeTab === "knowledge" ? (
          <Suspense fallback={<div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}><Spin /></div>}>
            <KnowledgeGraphPage />
          </Suspense>
        ) : (
          <div className="main-content">
            <div className="page-header" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
              <span className="page-title">
                {activeTab === "chat"
                  ? (currentConversationId
                      ? displayConversationTitle((conversations || []).find((c) => c.id === currentConversationId)?.title || "智能对话")
                      : "新对话")
                  : "技能管理"}
              </span>
              {activeTab === "chat" && currentConversationId && (
                <div style={{ display: "flex", gap: 4 }}>
                  <Tooltip title="清除上下文">
                    <Popconfirm
                      title="确认清除当前会话所有消息？"
                      description="清除后将重新开始对话，不可恢复"
                      onConfirm={clearCurrentContext}
                      okText="清除"
                      cancelText="取消"
                    >
                      <Button
                        type="text"
                        size="small"
                        icon={<ClearOutlined />}
                        style={{ color: "#8c8c8c", marginBottom: 14 }}
                      />
                    </Popconfirm>
                  </Tooltip>
                  <Tooltip title="刷新对话消息">
                    <Button
                      type="text"
                      size="small"
                      icon={<ReloadOutlined />}
                      onClick={reloadCurrentMessages}
                      style={{ color: "#8c8c8c", marginBottom: 14 }}
                    />
                  </Tooltip>
                </div>
              )}
            </div>
            <ChatPanel onConversationCreated={loadConversations} />
          </div>
        )}
      </div>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />

      {/* ── Admin LLM Config Modal ── */}
      <Modal
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <SettingOutlined style={{ color: "#1677ff" }} />
            <span>LLM 配置管理</span>
          </div>
        }
        open={adminOpen}
        onCancel={() => setAdminOpen(false)}
        footer={null}
        width={640}
      >
        {adminLoading ? (
          <div style={{ textAlign: "center", padding: 32 }}><Spin /></div>
        ) : (
          <div style={{ fontSize: 13 }}>
            {/* Existing providers */}
            {adminProviders.map((p, idx) => {
              const isStatic = idx < adminStaticCount;
              return (
              <div key={p.id} style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "8px 12px", marginBottom: 8,
                borderRadius: 8, border: "1px solid #f0f0f0",
                background: "#fafafa",
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>
                    {p.name} <Tag style={{ fontSize: 10 }}>{p.id}</Tag>
                    {isStatic && <Tag color="blue" style={{ fontSize: 10 }}>内置</Tag>}
                  </div>
                  <div style={{ fontSize: 11, color: "#8c8c8c", marginTop: 2 }}>
                    {p.base_url} · {p.models.join(", ")}
                  </div>
                  <div style={{ fontSize: 11, color: "#8c8c8c" }}>
                    API Key: {p.api_key}
                  </div>
                </div>
                {!isStatic && (
                  <Popconfirm
                    title={`确认删除 ${p.name}？`}
                    onConfirm={() => handleDeleteProvider(p.id)}
                    okText="删除" cancelText="取消"
                  >
                    <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                )}
              </div>
              );
            })}

            {/* Add new provider form */}
            <div style={{
              marginTop: 16, padding: "12px 14px",
              borderRadius: 8, border: "1px dashed #d9d9d9",
              background: "#fff",
            }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>添加新 Provider</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <Input size="small" placeholder="ID (如 openai)" value={newProvider.id}
                  onChange={(e) => setNewProvider({ ...newProvider, id: e.target.value })} />
                <Input size="small" placeholder="名称 (如 OpenAI)" value={newProvider.name}
                  onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })} />
                <Input size="small" placeholder="Base URL" value={newProvider.base_url}
                  onChange={(e) => setNewProvider({ ...newProvider, base_url: e.target.value })} />
                <Input size="small" placeholder="API Key" value={newProvider.api_key}
                  onChange={(e) => setNewProvider({ ...newProvider, api_key: e.target.value })} />
              </div>
              <div style={{ marginTop: 8 }}>
                <Input size="small" placeholder="模型列表 (逗号分隔)" value={newProvider.models?.join(",") || ""}
                  onChange={(e) => setNewProvider({ ...newProvider, models: e.target.value.split(",").filter(Boolean) })} />
              </div>
              <Button size="small" type="primary" icon={<PlusOutlined />}
                onClick={handleAddProvider}
                disabled={!newProvider.id || !newProvider.name || !newProvider.base_url || !newProvider.api_key}
                style={{ marginTop: 8 }}>
                添加
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* ── User Profile Modal ── */}
      <Modal
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <UserOutlined style={{ color: "#2468f2" }} />
            <span>记忆档案</span>
          </div>
        }
        open={profileOpen}
        onCancel={() => setProfileOpen(false)}
        footer={
          userProfile ? (
            <Popconfirm
              title="清除后 AI 将不再记住你的偏好，确认继续？"
              onConfirm={handleClearProfile}
              okText="清除" cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button danger icon={<ClearOutlined />} loading={clearingProfile} size="small">
                清除记忆
              </Button>
            </Popconfirm>
          ) : null
        }
        width={520}
      >
        {profileLoading ? (
          <div style={{ textAlign: "center", padding: 32 }}><Spin /></div>
        ) : !userProfile ? (
          <Empty description="暂无记忆数据，完成几次对话后将自动积累" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <div style={{ fontSize: 13 }}>
            {userProfile.profile_summary && (
              <div style={{
                background: "#f0f5ff",
                border: "1px solid #adc6ff",
                borderRadius: 8,
                padding: "10px 14px",
                marginBottom: 16,
                lineHeight: 1.7,
                color: "#1d3c85",
              }}>
                {userProfile.profile_summary}
              </div>
            )}

            <Descriptions column={1} size="small" bordered
              styles={{ label: { width: 90, fontSize: 12, color: "#8c8c8c" }, content: { fontSize: 12 } }}
            >
              {userProfile.preferences?.language_style && (
                <Descriptions.Item label="语言风格">
                  {userProfile.preferences.language_style}
                </Descriptions.Item>
              )}
              {userProfile.preferences?.verbosity && (
                <Descriptions.Item label="回答详度">
                  {userProfile.preferences.verbosity}
                </Descriptions.Item>
              )}
              {userProfile.key_facts?.profession && (
                <Descriptions.Item label="职业">
                  {userProfile.key_facts.profession}
                </Descriptions.Item>
              )}
              {(userProfile.key_facts?.interests?.length ?? 0) > 0 && (
                <Descriptions.Item label="兴趣">
                  {userProfile.key_facts.interests.map((i) => (
                    <Tag key={i} style={{ fontSize: 11, marginBottom: 2 }}>{i}</Tag>
                  ))}
                </Descriptions.Item>
              )}
              {(userProfile.key_facts?.domain_knowledge?.length ?? 0) > 0 && (
                <Descriptions.Item label="领域知识">
                  {userProfile.key_facts.domain_knowledge.map((d) => (
                    <Tag key={d} color="blue" style={{ fontSize: 11, marginBottom: 2 }}>{d}</Tag>
                  ))}
                </Descriptions.Item>
              )}
              {(userProfile.interaction_stats?.tools_used?.length ?? 0) > 0 && (
                <Descriptions.Item label="常用工具">
                  {userProfile.interaction_stats.tools_used.map((t) => (
                    <Tag key={t} color="green" style={{ fontSize: 11, marginBottom: 2 }}>{t}</Tag>
                  ))}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="对话次数">
                {userProfile.interaction_stats?.total_sessions ?? 0} 次
              </Descriptions.Item>
              {userProfile.interaction_stats?.last_active && (
                <Descriptions.Item label="最后活跃">
                  {new Date(userProfile.interaction_stats.last_active).toLocaleString("zh-CN")}
                </Descriptions.Item>
              )}
            </Descriptions>
            <div style={{ fontSize: 11, color: "#bfbfbf", marginTop: 10, textAlign: "right" }}>
              档案版本 v{userProfile.version ?? 1} · {userProfile.updated_at ? new Date(userProfile.updated_at).toLocaleString("zh-CN") : ""} 更新
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
