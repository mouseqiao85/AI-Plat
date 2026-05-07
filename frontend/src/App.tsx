import { useState, useEffect, useCallback } from "react";
import {
  Avatar, Button, Switch, Tag, Collapse, Empty, Tooltip,
  Input, Popconfirm, message, Spin, Modal, Descriptions,
} from "antd";
import {
  PlusOutlined, DeleteOutlined, ExperimentOutlined,
  LogoutOutlined, LoginOutlined, ReloadOutlined,
  CheckCircleFilled, CloseCircleFilled, WarningFilled,
  ThunderboltOutlined, MenuOutlined,
  MessageOutlined, DownOutlined, RightOutlined,
  EditOutlined, UserOutlined, ClearOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { useAppStore } from "./stores/appStore";
import { authApi, skillApi, conversationApi, adminApi, chatApi } from "./services/api";
import ChatPanel from "./components/ChatPanel";
import LoginModal from "./components/LoginModal";
import type { Skill, Conversation, UserProfile, LlmProvider } from "./types";
export default function App() {
  const {
    user, token, logout, setAuth,
    skills, setSkills, selectedSkill, setSelectedSkill,
    conversations, setConversations, currentConversationId,
    setCurrentConversationId, removeConversation, updateConversationTitle,
    clearMessages, addMessage, setMessages,
    theme, toggleTheme,
  } = useAppStore();

  const [loginOpen, setLoginOpen] = useState(false);
  const [loadingSkill, setLoadingSkill] = useState<string | null>(null);
  const [showAddInput, setShowAddInput] = useState(false);
  const [addPath, setAddPath] = useState("");
  const [adding, setAdding] = useState(false);
  const [loadingSkills, setLoadingSkills] = useState(false);
  const [activeTab, setActiveTab] = useState<"chat" | "skills">("chat");
  const [skillGroupOpen, setSkillGroupOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
  const [_editingProvider, setEditingProvider] = useState<LlmProvider | null>(null);
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

  // Dev auto-login
  useEffect(() => {
    if (!import.meta.env.DEV) return;
    authApi.devLogin().then((res) => {
      setAuth(
        { id: res.user.id, nickname: res.user.nickname, membership_tier: res.user.membership_tier || "free", role: res.user.role || "admin" },
        res.access_token,
      );
    }).catch(() => {});
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
    setLoadingSkills(true);
    try {
      const res = await skillApi.list();
      setSkills(res.skills || []);
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : "加载技能失败");
    } finally {
      setLoadingSkills(false);
    }
  }, []);

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
      setUserProfile(res.profile);
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

  const enabledCount = skills.filter((s) => s.enabled).length;

  const renderSkillItem = (skill: Skill) => {
    const isSelected = selectedSkill === skill.name;
    return (
      <div
        key={skill.name}
        className={`skill-item${isSelected ? " selected" : ""}${!skill.enabled ? " disabled" : ""}`}
        onClick={() => { if (skill.enabled) setSelectedSkill(isSelected ? null : skill.name); }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div className="skill-item-name">{skill.name}</div>
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
        <div className="skill-item-desc">{skill.description}</div>
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
              label: <span style={{ fontSize: 12 }}>{t.name}</span>,
              children: <span style={{ fontSize: 11, color: "#8c8c8c" }}>{t.description}</span>,
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
            <Tooltip title="刷新">
              <Button type="text" size="small" icon={<ReloadOutlined />}
                onClick={loadConversations}
                style={{ fontSize: 11, padding: "0 2px", height: 18 }} />
            </Tooltip>
          </div>

          {conversations.length === 0 ? (
            <div style={{ padding: "16px 12px", textAlign: "center" }}>
              <Empty description="暂无历史对话" image={Empty.PRESENTED_IMAGE_SIMPLE}
                style={{ margin: 0 }} styles={{ image: { height: 32 } }} />
            </div>
          ) : (
            conversations.map((conv) => (
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
                    {conv.title}
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
            当前技能：<strong>{selectedSkill}</strong>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="app-layout">
      {/* ── Top Header ── */}
      <header className="app-header">
        <div className="header-logo">
          <div className="header-logo-icon">
            <ThunderboltOutlined />
          </div>
          <span className="header-logo-text">超级助理</span>
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
        </nav>

        <div className="header-actions">
          <Button
            type="text" size="small" icon={<MenuOutlined />}
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            style={{ display: "none" }}
            className="mobile-menu-btn"
          />

          <Tooltip title={theme === "dark" ? "切换亮色模式" : "切换暗色模式"}>
            <button className="theme-toggle" onClick={toggleTheme}>
              {theme === "dark" ? "☀️" : "🌙"}
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

        <div className="main-content">
          <div className="page-header" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
            <span className="page-title">
              {activeTab === "chat"
                ? (currentConversationId
                    ? (conversations.find((c) => c.id === currentConversationId)?.title || "智能对话")
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
              {userProfile.preferences.language_style && (
                <Descriptions.Item label="语言风格">
                  {userProfile.preferences.language_style}
                </Descriptions.Item>
              )}
              {userProfile.preferences.verbosity && (
                <Descriptions.Item label="回答详度">
                  {userProfile.preferences.verbosity}
                </Descriptions.Item>
              )}
              {userProfile.key_facts.profession && (
                <Descriptions.Item label="职业">
                  {userProfile.key_facts.profession}
                </Descriptions.Item>
              )}
              {userProfile.key_facts.interests.length > 0 && (
                <Descriptions.Item label="兴趣">
                  {userProfile.key_facts.interests.map((i) => (
                    <Tag key={i} style={{ fontSize: 11, marginBottom: 2 }}>{i}</Tag>
                  ))}
                </Descriptions.Item>
              )}
              {userProfile.key_facts.domain_knowledge.length > 0 && (
                <Descriptions.Item label="领域知识">
                  {userProfile.key_facts.domain_knowledge.map((d) => (
                    <Tag key={d} color="blue" style={{ fontSize: 11, marginBottom: 2 }}>{d}</Tag>
                  ))}
                </Descriptions.Item>
              )}
              {userProfile.interaction_stats.tools_used.length > 0 && (
                <Descriptions.Item label="常用工具">
                  {userProfile.interaction_stats.tools_used.map((t) => (
                    <Tag key={t} color="green" style={{ fontSize: 11, marginBottom: 2 }}>{t}</Tag>
                  ))}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="对话次数">
                {userProfile.interaction_stats.total_sessions} 次
              </Descriptions.Item>
              {userProfile.interaction_stats.last_active && (
                <Descriptions.Item label="最后活跃">
                  {new Date(userProfile.interaction_stats.last_active).toLocaleString("zh-CN")}
                </Descriptions.Item>
              )}
            </Descriptions>
            <div style={{ fontSize: 11, color: "#bfbfbf", marginTop: 10, textAlign: "right" }}>
              档案版本 v{userProfile.version} · {new Date(userProfile.updated_at).toLocaleString("zh-CN")} 更新
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
