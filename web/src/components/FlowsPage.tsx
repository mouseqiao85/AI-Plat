import { lazy, Suspense, useCallback, useEffect, useMemo, useState, useRef } from "react";
import {
  Button, Input, Select, Tag, Empty, Spin, message, Modal, Popconfirm, Tooltip, Tabs, Upload, Tree,
} from "antd";
import {
  PlusOutlined, DeleteOutlined, PlayCircleOutlined,
  SaveOutlined, EditOutlined, SearchOutlined, ThunderboltOutlined, CheckCircleFilled,
  WarningFilled, StopOutlined, ClearOutlined, GithubOutlined, DownloadOutlined, PaperClipOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import { hermesApi, skillApi, tabsApi, streamRunEvents } from "../services/api";
import type {
  ExpertRole, ToolScenario, DialogFlow, FlowType, RunEvent, FlowRun,
  Skill, SkillTab, TabRole, CollaborationMessage, DagFlowEdge, DagFlowSpec, DagFlowNode,
} from "../types";
import { useAppStore } from "../stores/appStore";
import ImportSkillModal from "./ImportSkillModal";
import { InlineFileDownloadCard } from "./FileDownloadCard";
import { inferredOutputFilename, isDownloadableOutputContent } from "../utils/fileOutput";
import type { Key } from "react";

const MarkdownContent = lazy(() => import("./MarkdownContent"));
const SkillFlowCanvas = lazy(() => import("./SkillFlowCanvas"));

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
const CATEGORY_ORDER = ["plan", "implement", "release", "ops", "safety", "other"];
const MANAGED_SKILLS_TAB_ID = "managed-skills";
const MANAGED_SKILLS_TAB: SkillTab = {
  id: MANAGED_SKILLS_TAB_ID,
  name: "技能管理",
  description: "技能管理页面已导入的 Skill",
  source_type: "builtin",
  source_url: "",
  branch: "",
  sub_path: "",
  imported_at: "",
  updated_at: "",
  role_count: 0,
  icon: "",
  tab_order: 1,
};

const FLOW_ROLE_FILTER_VERSION = "pm-dev-consulting-20260606";
const DEFAULT_BRAVE_SEARCH_ROLE_ID = "brave-search";
const DEFAULT_FLOW_ROLE_IDS = [DEFAULT_BRAVE_SEARCH_ROLE_ID];

const FLOW_ROLE_ALLOWED_IDS = new Set([
  "office-hours",
  "plan-ceo-review",
  "plan-eng-review",
  "plan-design-review",
  "plan-devex-review",
  "plan-tune",
  "autoplan",
  "design-consultation",
  "review",
  "codex",
  "investigate",
  "design-review",
  "design-shotgun",
  "design-html",
  "devex-review",
  "qa",
  "qa-only",
  "skillify",
  "ship",
  "land-and-deploy",
  "canary",
  "landing-report",
  "document-release",
  "setup-deploy",
  "gstack-upgrade",
  "context-save",
  "context-restore",
  "learn",
  "retro",
  "health",
  "benchmark",
  "benchmark-models",
  "cso",
  "setup-gbrain",
  "sync-gbrain",
  "pair-agent",
  "careful",
  "freeze",
  "guard",
  "unfreeze",
  DEFAULT_BRAVE_SEARCH_ROLE_ID,
  "brainstorming",
  "deep-research",
  "dispatching-parallel-agents",
  "executing-plans",
  "finishing-a-development-branch",
  "receiving-code-review",
  "requesting-code-review",
  "subagent-driven-development",
  "systematic-debugging",
  "test-driven-development",
  "using-git-worktrees",
  "verification-before-completion",
  "writing-plans",
  "skill-creator",
  "writing-skills",
  "competitive-analysis",
  "sector-overview",
  "client-report",
  "client-review",
]);

const FLOW_ROLE_ALWAYS_ALLOW_IDS = new Set([DEFAULT_BRAVE_SEARCH_ROLE_ID]);
const FLOW_ROLE_ALLOWED_BUILTIN_CATEGORIES = new Set(["plan", "implement", "release", "ops", "safety"]);
const FLOW_ROLE_BLOCKED_CATEGORIES = new Set(["browser"]);

const FLOW_ROLE_BLOCKED_IDS = new Set([
  "browse",
  "scrape",
  "open-gstack-browser",
  "setup-browser-cookies",
  "make-pdf",
  "3-statement-model",
  "academic-paper",
  "academic-paper-reviewer",
  "academic-pipeline",
  "accrual-schedule",
  "audit-xls",
  "break-trace",
  "comps-analysis",
  "dcf-model",
  "deck-refresh",
  "earnings-analysis",
  "earnings-preview",
  "famou-experiment-manager",
  "gl-recon",
  "ib-check-deck",
  "ic-memo",
  "idea-generation",
  "investment-proposal",
  "kyc-doc-parse",
  "kyc-rules",
  "lbo-model",
  "model-update",
  "morning-note",
  "nav-tieout",
  "pitch-deck",
  "portfolio-monitoring",
  "pptx-author",
  "returns-analysis",
  "roll-forward",
  "stock_analysis_with_api",
  "using-superpowers",
  "variance-commentary",
  "xlsx-author",
]);

const FLOW_ROLE_BLOCKED_PHRASES = [
  "browser",
  "browse",
  "scrape",
  "crawler",
  "webpage",
  "web page",
  "cookie",
  "cookies",
  "浏览器",
  "网页",
  "抓取",
  "爬取",
  "cookie",
  "学术",
  "论文",
  "academic",
  "paper",
  "thesis",
  "citation",
  "finance",
  "financial",
  "investment",
  "investor",
  "stock",
  "equity",
  "valuation",
  "dcf",
  "lbo",
  "kyc",
  "aml",
  "audit",
  "accounting",
  "accrual",
  "ledger",
  "earnings",
  "portfolio",
  "returns",
  "pptx",
  "xlsx",
  "excel",
  "powerpoint",
  "pitch deck",
  "投行",
  "投资",
  "股票",
  "财务",
  "估值",
  "审计",
  "对账",
];

const FLOW_ROLE_RELEVANT_PHRASES = [
  "project",
  "product",
  "plan",
  "planning",
  "manager",
  "management",
  "delivery",
  "software",
  "engineering",
  "development",
  "frontend",
  "backend",
  "code",
  "debug",
  "test",
  "review",
  "deploy",
  "release",
  "ops",
  "devex",
  "consult",
  "consulting",
  "industry",
  "sector",
  "competitive",
  "market",
  "research",
  "strategy",
  "client",
  "项目",
  "产品",
  "规划",
  "管理",
  "交付",
  "软件",
  "研发",
  "开发",
  "代码",
  "调试",
  "测试",
  "评审",
  "部署",
  "运维",
  "咨询",
  "行业",
  "竞品",
  "市场",
  "调研",
  "研究",
  "客户",
];

type RoleFilterInput = {
  id: string;
  name?: string;
  description?: string;
  category?: string;
  classification?: string;
  source?: string;
  author?: string;
  triggers?: string[];
  keywords?: string[];
  capabilities?: string[];
  recommendedTools?: string[];
  allowedTools?: string[];
  tools?: { name?: string; description?: string }[];
  allowBuiltInCategory?: boolean;
};

const normalizeRoleToken = (value?: string) => (value || "").trim().toLowerCase();

const roleFilterText = (role: RoleFilterInput, includeGrouping = true) => [
  role.id,
  role.name,
  role.description,
  ...(includeGrouping ? [role.category, role.classification] : []),
  role.source,
  role.author,
  ...(role.triggers || []),
  ...(role.keywords || []),
  ...(role.capabilities || []),
  ...(role.recommendedTools || []),
  ...(role.allowedTools || []),
  ...(role.tools || []).flatMap((tool) => [tool.name, tool.description]),
].filter(Boolean).join(" ").toLowerCase();

const hasAnyPhrase = (text: string, phrases: string[]) => phrases.some((phrase) => text.includes(phrase));

const isRelevantFlowRole = (role: RoleFilterInput) => {
  const id = normalizeRoleToken(role.id);
  const category = normalizeRoleToken(role.category);
  const blockedText = roleFilterText(role);
  const relevantText = roleFilterText(role, false);

  if (FLOW_ROLE_ALWAYS_ALLOW_IDS.has(id)) return true;
  if (FLOW_ROLE_BLOCKED_IDS.has(id)) return false;
  if (FLOW_ROLE_BLOCKED_CATEGORIES.has(category)) return false;
  if (hasAnyPhrase(blockedText, FLOW_ROLE_BLOCKED_PHRASES)) return false;
  if (FLOW_ROLE_ALLOWED_IDS.has(id)) return true;
  if (role.allowBuiltInCategory && FLOW_ROLE_ALLOWED_BUILTIN_CATEGORIES.has(category)) return true;
  return hasAnyPhrase(relevantText, FLOW_ROLE_RELEVANT_PHRASES);
};

const isExplicitlyBlockedRoleId = (roleId: string) => {
  const id = normalizeRoleToken(roleId);
  return FLOW_ROLE_BLOCKED_IDS.has(id) || hasAnyPhrase(id, FLOW_ROLE_BLOCKED_PHRASES);
};

const expertRoleFilterInput = (role: ExpertRole): RoleFilterInput => ({
  id: role.id,
  name: role.name,
  description: role.description,
  category: role.category,
  source: role.source,
  triggers: role.triggers,
  allowedTools: role.allowed_tools,
  allowBuiltInCategory: true,
});

const isRelevantExpertRole = (role: ExpertRole) => isRelevantFlowRole(expertRoleFilterInput(role));

const parseServerTimestamp = (value?: string | null) => {
  if (!value) return null;
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(normalized);
  const date = new Date(hasTimezone ? normalized : `${normalized}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
};

const formatServerDateTime = (value?: string | null) => {
  const date = parseServerTimestamp(value);
  return date ? date.toLocaleString("zh-CN") : "";
};

const formatServerTime = (value?: string | null) => {
  const date = parseServerTimestamp(value);
  return date ? date.toLocaleTimeString("zh-CN") : "";
};

const FLOW_TYPE_META: Record<FlowType, { label: string; detail: string; color: string }> = {
  sequential: { label: "顺序", detail: "顺序执行", color: "geekblue" },
  parallel: { label: "并行", detail: "并行执行", color: "magenta" },
  hierarchical: { label: "主从", detail: "主从协作", color: "purple" },
  competitive: { label: "竞争", detail: "竞争评审", color: "orange" },
  pipeline: { label: "流水线", detail: "队列流水线", color: "cyan" },
  peer_to_peer: { label: "对等", detail: "对等协作", color: "green" },
  dag: { label: "DAG", detail: "DAG 编排", color: "gold" },
};

const ROLE_ZH: Record<string, { name: string; description: string }> = {
  "office-hours": { name: "方案答疑", description: "在规划早期进行技术答疑、风险提示和方案校准。" },
  "plan-ceo-review": { name: "CEO 方案评审", description: "从业务目标、优先级和投入产出角度评审方案。" },
  "plan-eng-review": { name: "工程方案评审", description: "从架构、可维护性、复杂度和落地风险角度评审方案。" },
  "plan-design-review": { name: "设计方案评审", description: "从体验、信息架构和视觉一致性角度评审方案。" },
  "plan-devex-review": { name: "开发体验评审", description: "从工具链、调试体验、交付效率和工程流程角度评审方案。" },
  "plan-tune": { name: "方案调优", description: "压缩范围、补齐验收标准并优化实施路径。" },
  autoplan: { name: "自动规划", description: "拆解目标、生成实施步骤并识别关键依赖。" },
  "design-consultation": { name: "设计咨询", description: "提供产品设计、交互和信息架构建议。" },
  review: { name: "代码评审", description: "检查当前改动中的正确性、可靠性和可维护性问题。" },
  codex: { name: "代码实现", description: "执行软件开发、修复和重构任务。" },
  investigate: { name: "问题排查", description: "定位异常、失败原因和系统行为差异。" },
  "design-review": { name: "设计评审", description: "评审界面、交互和设计还原质量。" },
  "design-shotgun": { name: "多方案设计", description: "快速生成多个设计方向并比较取舍。" },
  "design-html": { name: "HTML 设计实现", description: "将设计意图落地为 HTML/CSS 原型或页面。" },
  "devex-review": { name: "工程体验评审", description: "评审开发体验、脚手架、文档和自动化流程。" },
  qa: { name: "质量测试", description: "执行功能验证、边界测试和回归检查。" },
  "qa-only": { name: "独立测试", description: "只做验证和问题复现，不修改实现。" },
  scrape: { name: "网页抓取", description: "抓取网页内容、提取结构化信息并整理结果。" },
  skillify: { name: "技能化", description: "将流程、经验或工具封装成可复用技能。" },
  ship: { name: "发布准备", description: "整理变更、验证结果并准备发布。" },
  "land-and-deploy": { name: "合并部署", description: "完成合并、部署和上线后的基础检查。" },
  canary: { name: "灰度验证", description: "执行灰度发布检查、观察信号并判断是否推进。" },
  "landing-report": { name: "落地报告", description: "总结实施、验证、风险和后续事项。" },
  "document-release": { name: "发布文档", description: "编写发布说明、变更记录和使用说明。" },
  "setup-deploy": { name: "部署配置", description: "准备部署配置、环境变量和运行脚本。" },
  "gstack-upgrade": { name: "工具栈升级", description: "升级 gstack 相关技能、配置和依赖。" },
  "context-save": { name: "上下文保存", description: "保存当前任务上下文、决策和后续步骤。" },
  "context-restore": { name: "上下文恢复", description: "恢复已保存上下文并继续推进任务。" },
  learn: { name: "经验沉淀", description: "将任务经验整理为可复用知识。" },
  retro: { name: "复盘", description: "复盘过程、问题、改进点和后续行动。" },
  health: { name: "健康检查", description: "检查系统、配置和关键流程是否正常。" },
  benchmark: { name: "基准测试", description: "运行性能或质量基准并汇总结果。" },
  "benchmark-models": { name: "模型基准测试", description: "比较不同模型在指定任务上的表现。" },
  cso: { name: "安全负责人", description: "从安全、合规和风险控制角度审视方案。" },
  "setup-gbrain": { name: "知识库配置", description: "配置团队知识库或记忆系统。" },
  "sync-gbrain": { name: "知识库同步", description: "同步知识库内容并更新索引。" },
  browse: { name: "浏览器操作", description: "使用浏览器查看页面、验证交互或收集信息。" },
  "open-gstack-browser": { name: "打开浏览器", description: "启动或连接 gstack 浏览器环境。" },
  "setup-browser-cookies": { name: "浏览器登录配置", description: "配置浏览器 Cookie 或登录态。" },
  "pair-agent": { name: "结对智能体", description: "与另一个智能体协作完成检查或实现。" },
  careful: { name: "谨慎模式", description: "高风险操作前加强确认、审查和回滚意识。" },
  freeze: { name: "冻结变更", description: "暂停变更并保护当前状态。" },
  guard: { name: "安全护栏", description: "检查危险操作、越权行为和不安全路径。" },
  unfreeze: { name: "解除冻结", description: "在确认后恢复变更能力。" },
  "make-pdf": { name: "PDF 生成", description: "将内容整理并导出为 PDF。" },
  "3-statement-model": { name: "三大财务报表模型", description: "填充并联动利润表、资产负债表和现金流量表模板。" },
  "academic-paper": { name: "学术论文写作", description: "论文写作流水线，支持大纲、修订、摘要、文献综述、引用检查和格式转换。" },
  "academic-paper-reviewer": { name: "学术论文评审", description: "模拟主编、同行评审和反方审稿人，从多角度评审论文质量。" },
  "academic-pipeline": { name: "学术研究全流程", description: "串联研究、写作、诚信检查、评审、修订和定稿。" },
  "accrual-schedule": { name: "计提明细表", description: "生成期末计提明细、计算分录并引用支持材料。" },
  "audit-xls": { name: "Excel 公式审计", description: "检查电子表格公式、平衡关系和模型逻辑错误。" },
  brainstorming: { name: "需求头脑风暴", description: "在创意、功能或行为变更前澄清意图、需求和设计方向。" },
  "break-trace": { name: "差异追踪", description: "沿审计轨迹追踪对账差异到源交易或入账记录。" },
  "client-report": { name: "客户报告", description: "生成客户沟通和会议使用的专业报告材料。" },
  "client-review": { name: "客户资料审阅", description: "审阅客户材料，提炼风险点、机会和待确认事项。" },
  "competitive-analysis": { name: "竞争格局分析", description: "构建竞品研究、市场定位、同业对比和战略洞察。" },
  "comps-analysis": { name: "可比公司分析", description: "整理可比公司、估值倍数和同业基准分析。" },
  "dcf-model": { name: "DCF 估值模型", description: "基于现金流预测、WACC 和敏感性分析构建 DCF 估值模型。" },
  "deck-refresh": { name: "演示文稿数据刷新", description: "用最新季度、财务或市场数据更新既有演示文稿。" },
  "deep-research": { name: "深度研究", description: "多智能体严谨研究流程，支持文献综述、事实核查和研究报告。" },
  "dispatching-parallel-agents": { name: "并行智能体调度", description: "将多个互不依赖的任务分派给并行智能体执行。" },
  "earnings-analysis": { name: "财报业绩分析", description: "生成季度业绩更新报告，分析关键指标和投资观点变化。" },
  "earnings-preview": { name: "财报前瞻", description: "在财报发布前整理市场预期、关键指标、催化剂和风险点。" },
  "executing-plans": { name: "执行实施计划", description: "根据已批准的实施计划分阶段执行，并在检查点复核。" },
  "famou-experiment-manager": { name: "Famou 实验管理", description: "提交、查看、删除和获取 Famou 平台实验及配置。" },
  "finishing-a-development-branch": { name: "开发分支收尾", description: "在实现和测试完成后，辅助选择合并、PR 或清理方案。" },
  "gl-recon": { name: "总账对账", description: "核对总账与明细账，识别并分类差异。" },
  "ib-check-deck": { name: "投行材料质检", description: "检查 Pitch Deck 的数字一致性、叙事匹配、语言和版式质量。" },
  "ic-memo": { name: "投委会备忘录", description: "生成投委会审议所需的交易、估值、风险和建议材料。" },
  "idea-generation": { name: "投资想法生成", description: "围绕行业、公司或主题生成可研究的投资想法。" },
  "investment-proposal": { name: "投资建议书", description: "生成面向客户或内部审批的投资建议和论证材料。" },
  "kyc-doc-parse": { name: "KYC 文件解析", description: "从开户或尽调材料中抽取身份、受益所有人、资金来源和文件清单。" },
  "kyc-rules": { name: "KYC/AML 规则评分", description: "根据规则网格对 KYC 记录评级、列出命中规则并标记缺失项。" },
  "lbo-model": { name: "LBO 杠杆收购模型", description: "填充和校验私募股权交易的 LBO Excel 模型模板。" },
  "model-update": { name: "模型更新", description: "根据最新数据和假设更新财务模型。" },
  "morning-note": { name: "晨会纪要", description: "生成市场、行业和公司动态晨会材料。" },
  "nav-tieout": { name: "NAV 勾稽", description: "将 LP 报表与基金 NAV 包重新计算勾稽并标记不一致项目。" },
  "pitch-deck": { name: "Pitch Deck 填充", description: "把源数据填入既有投行演示文稿模板。" },
  "portfolio-monitoring": { name: "组合监控", description: "跟踪投资组合表现、风险暴露、估值和关键事件。" },
  "pptx-author": { name: "PPTX 文件生成", description: "在无 Office 界面的环境中生成 .pptx 文件。" },
  "receiving-code-review": { name: "处理代码评审", description: "在实现评审意见前进行技术核验。" },
  "requesting-code-review": { name: "请求代码评审", description: "在任务完成或合并前检查实现是否满足要求。" },
  "returns-analysis": { name: "收益归因分析", description: "分析投资回报、收益来源和驱动因素。" },
  "roll-forward": { name: "余额滚动表", description: "生成期初余额、期间活动、转回和期末余额的滚动明细。" },
  "sector-overview": { name: "行业概览", description: "生成行业规模、格局、趋势、驱动因素和风险综述。" },
  "skill-creator": { name: "技能创建器", description: "创建、修改和优化平台技能。" },
  stock_analysis_with_api: { name: "股票综合分析", description: "结合基本面、技术面、估值和量化信号进行股票分析。" },
  "subagent-driven-development": { name: "子智能体驱动开发", description: "用多个子智能体执行当前会话中的独立开发任务。" },
  "systematic-debugging": { name: "系统化调试", description: "遇到 bug、测试失败或异常行为时进行结构化排查。" },
  "test-driven-development": { name: "测试驱动开发", description: "在实现功能或修复缺陷前先设计测试与验收条件。" },
  "using-git-worktrees": { name: "Git Worktree 隔离开发", description: "为功能开发创建隔离工作区。" },
  "using-superpowers": { name: "技能使用规范", description: "建立技能发现和调用规则。" },
  "variance-commentary": { name: "差异分析评论", description: "为损益表和资产负债表差异撰写管理层解释。" },
  "verification-before-completion": { name: "完成前验证", description: "在宣称完成前运行验证命令并提供证据。" },
  "writing-plans": { name: "编写实施计划", description: "在动手改代码前为多步骤任务编写清晰计划。" },
  "writing-skills": { name: "编写技能", description: "创建、编辑和验证技能的完整工作流。" },
  "xlsx-author": { name: "XLSX 文件生成", description: "在无 Excel 界面的环境中生成 .xlsx 工作簿文件。" },
};

const TAB_ZH: Record<string, string> = {
  "software-engineering": "软件开发",
  "software engineering": "软件开发",
  "software-development": "软件开发",
  "software development": "软件开发",
  [MANAGED_SKILLS_TAB_ID]: "技能管理",
  engineering: "工程研发",
  finance: "金融分析",
  research: "研究写作",
  productivity: "效率工具",
};

const CATEGORY_ZH: Record<string, string> = {
  planning: "规划",
  implementation: "实现",
  frontend: "前端",
  backend: "后端",
  testing: "测试",
  review: "评审",
  deploy: "部署",
  ops: "运维",
  other: "其他",
};

const humanizeRoleName = (name: string) => name.replace(/[-_]+/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
const roleZh = (roleId: string, fallbackName?: string, fallbackDescription?: string) => {
  const hit = ROLE_ZH[roleId] || ROLE_ZH[fallbackName || ""];
  return {
    name: hit?.name || fallbackName || humanizeRoleName(roleId),
    description: hit?.description || fallbackDescription || "暂无中文说明",
  };
};
const tabDisplayName = (tab: SkillTab) => TAB_ZH[tab.id] || TAB_ZH[tab.name?.toLowerCase()] || tab.name || humanizeRoleName(tab.id);
const categoryDisplayName = (category?: string) => {
  if (!category) return "其他";
  const key = category.toLowerCase();
  return CATEGORY_ZH[key] || category;
};

interface ProductDeliveryStagePreset {
  name: string;
  description: string;
  flowType: FlowType;
  roles: string[];
  minRoles?: number;
}

const PRODUCT_DELIVERY_STAGES: ProductDeliveryStagePreset[] = [
  { name: "行业背景研究", description: "梳理行业现状、用户/客户画像、竞品与政策/技术趋势。", flowType: "parallel", roles: [DEFAULT_BRAVE_SEARCH_ROLE_ID, "deep-research", "sector-overview", "investigate"] },
  { name: "需求调研", description: "形成访谈问题、调研对象、调研结论和证据清单。", flowType: "parallel", roles: [DEFAULT_BRAVE_SEARCH_ROLE_ID, "office-hours", "design-consultation", "client-review"] },
  { name: "需求分析", description: "沉淀核心痛点、用户故事、优先级、约束与验收标准。", flowType: "sequential", roles: ["plan-ceo-review", "plan-eng-review", "plan-tune"] },
  { name: "产品匹配度分析", description: "评估现有产品/平台能力与需求的匹配度、差距和改造范围。", flowType: "competitive", roles: [DEFAULT_BRAVE_SEARCH_ROLE_ID, "plan-design-review", "design-review", "devex-review"], minRoles: 2 },
  { name: "PRD 设计", description: "输出产品目标、范围、功能清单、流程、权限、数据和验收标准。", flowType: "sequential", roles: ["design-consultation", "document-release", "plan-design-review"] },
  { name: "MVP 设计", description: "定义最小可用版本、关键路径、原型/交互、里程碑和风险。", flowType: "sequential", roles: ["autoplan", "design-shotgun", "design-html"] },
  { name: "技术开发与单元测试", description: "输出技术实现方案、接口/数据结构、开发任务拆解和单元测试策略。", flowType: "pipeline", roles: ["codex", "review", "qa"], minRoles: 2 },
  { name: "UAT 测试", description: "输出 UAT 场景、测试用例、验收清单、缺陷分级和修复建议。", flowType: "parallel", roles: ["qa-only", "qa", "verification-before-completion"] },
  { name: "部署", description: "输出部署方案、环境配置、发布步骤、回滚方案和发布检查表。", flowType: "sequential", roles: ["setup-deploy", "ship", "land-and-deploy"] },
  { name: "运维", description: "输出监控指标、告警规则、巡检项、SLA、知识库和持续优化计划。", flowType: "sequential", roles: ["health", "canary", "retro"] },
];

const productDeliveryPrompt = (stage: ProductDeliveryStagePreset, index: number) => `你正在执行垂类智能体产品交付流程中的独立阶段：${index + 1}. ${stage.name}。

阶段职责：${stage.description}

用户输入：
{input}

上游材料 / 相关流程输出：
{prior}

输出要求：
- 请基于你当前 skill / 角色职责背景完成“${stage.name}”阶段，不要泛泛而谈。
- 输出本阶段关键结论、交付物、待确认问题、风险与下一阶段输入。
- 如果上游材料不足，请给出可执行的补充信息清单。
- 使用结构化 Markdown，便于复制给下一个流程继续执行。`;

interface RunRolePanel {
  role_id: string;
  node_id?: string;
  node_type?: DagFlowNode["type"];
  label?: string;
  status: "pending" | "running" | "completed" | "failed";
  content: string;
  error?: string;
  latency_ms?: number;
}

interface FlowAttachment {
  name: string;
  content: string;
  inline: boolean;
  size: number;
}

type RoleContractDraft = {
  stance_name?: string;
  objective?: string;
  must_defend?: string;
  must_challenge?: string;
  evidence_standard?: string;
  risk_bias?: string;
  forbidden_overlap?: string;
  output_schema?: string;
};

type AdjudicationDraft = {
  decision_rule?: string;
  rubric?: string;
  required_output_sections?: string;
};

const TEXT_ATTACHMENT_EXTENSIONS = new Set(["txt", "md", "markdown", "csv", "json", "yaml", "yml"]);
const MAX_INLINE_ATTACHMENT_CHARS = 20000;

const asPlainRecord = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};

const textValue = (value: unknown) => {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.filter((item) => typeof item === "string").join("\n");
  return "";
};

const cleanText = (value?: string) => (value || "").trim();

const splitListText = (value?: string) =>
  (value || "")
    .split(/[\n,，]+/)
    .map((item) => item.trim())
    .filter(Boolean);

const readRoleContracts = (flow?: DialogFlow | null): Record<string, RoleContractDraft> => {
  const spec = asPlainRecord(flow?.flow_spec);
  const contracts = asPlainRecord(spec.role_contracts || spec.roles);
  const drafts: Record<string, RoleContractDraft> = {};
  for (const [roleId, raw] of Object.entries(contracts)) {
    const item = asPlainRecord(raw);
    drafts[roleId] = {
      stance_name: textValue(item.stance_name),
      objective: textValue(item.objective),
      must_defend: textValue(item.must_defend),
      must_challenge: textValue(item.must_challenge),
      evidence_standard: textValue(item.evidence_standard),
      risk_bias: textValue(item.risk_bias),
      forbidden_overlap: textValue(item.forbidden_overlap),
      output_schema: textValue(item.output_schema),
    };
  }
  return drafts;
};

const readAdjudication = (flow?: DialogFlow | null): AdjudicationDraft => {
  const spec = asPlainRecord(flow?.flow_spec);
  const item = asPlainRecord(spec.adjudication || spec.judge);
  return {
    decision_rule: textValue(item.decision_rule),
    rubric: textValue(item.rubric),
    required_output_sections: textValue(item.required_output_sections),
  };
};

const serializeRoleContract = (draft?: RoleContractDraft): Record<string, unknown> => {
  const contract: Record<string, unknown> = {};
  const scalarFields: Array<keyof Omit<RoleContractDraft, "output_schema">> = [
    "stance_name",
    "objective",
    "must_defend",
    "must_challenge",
    "evidence_standard",
    "risk_bias",
    "forbidden_overlap",
  ];
  for (const field of scalarFields) {
    const value = cleanText(draft?.[field]);
    if (value) contract[field] = value;
  }
  const outputSchema = splitListText(draft?.output_schema);
  if (outputSchema.length > 0) contract.output_schema = outputSchema;
  return contract;
};

const serializeAdjudication = (draft: AdjudicationDraft): Record<string, unknown> => {
  const contract: Record<string, unknown> = {};
  const decisionRule = cleanText(draft.decision_rule);
  const rubric = splitListText(draft.rubric);
  const requiredSections = splitListText(draft.required_output_sections);
  if (decisionRule) contract.decision_rule = decisionRule;
  if (rubric.length > 0) contract.rubric = rubric;
  if (requiredSections.length > 0) contract.required_output_sections = requiredSections;
  return contract;
};

const buildCollaborationSpec = (
  roleIds: string[],
  roleContracts: Record<string, RoleContractDraft>,
  adjudication: AdjudicationDraft,
): Record<string, unknown> => {
  const spec: Record<string, unknown> = {};
  const contracts: Record<string, unknown> = {};
  for (const roleId of roleIds) {
    const contract = serializeRoleContract(roleContracts[roleId]);
    if (Object.keys(contract).length > 0) contracts[roleId] = contract;
  }
  if (Object.keys(contracts).length > 0) spec.role_contracts = contracts;
  const judge = serializeAdjudication(adjudication);
  if (Object.keys(judge).length > 0) spec.adjudication = judge;
  return spec;
};

const isTextAttachment = (file: File) => {
  const ext = file.name.split(".").pop()?.toLowerCase() || "";
  return file.type.startsWith("text/") || TEXT_ATTACHMENT_EXTENSIONS.has(ext);
};

const attachmentMessagePart = (file: FlowAttachment) => {
  if (!file.inline) {
    return `\n\n---\n**附件: ${file.name}**\n\n[该附件为二进制/富文档文件，未直接内联到提示词中。请先将文件内容转为文本、Markdown，或导入知识库后再运行流程。]`;
  }
  const content = file.content.length > MAX_INLINE_ATTACHMENT_CHARS
    ? `${file.content.slice(0, MAX_INLINE_ATTACHMENT_CHARS)}\n\n[附件内容已截断：原始 ${file.content.length} 字符]`
    : file.content;
  return `\n\n---\n**附件: ${file.name}**\n\n${content}`;
};

const roleToDagNodeId = (roleId: string, index: number) => {
  const safe = roleId.replace(/[^A-Za-z0-9_-]/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
  return safe || `node-${index + 1}`;
};

const graphRagRoleId = (nodeId: string) => `graphrag:${nodeId}`;

const dagNodeActorId = (node: DagFlowNode) =>
  node.type === "graphrag" ? graphRagRoleId(node.id) : node.role_id || node.id;

const buildDagSpec = (roleIds: string[], edges: DagFlowEdge[], extraNodes: DagFlowNode[] = []): DagFlowSpec => {
  const nodes = roleIds.map((roleId, index) => ({
    id: roleToDagNodeId(roleId, index),
    type: "role" as const,
    role_id: roleId,
    label: roleId,
  }));
  const roleNodeIds = new Set(nodes.map((node) => node.id));
  const cleanExtraNodes = extraNodes
    .filter((node) => node?.type === "graphrag" && typeof node.id === "string" && node.id.trim())
    .map((node) => ({
      id: node.id.trim(),
      type: "graphrag" as const,
      role_id: graphRagRoleId(node.id.trim()),
      label: node.label || "GraphRAG",
      query_template: node.query_template || "{input}",
      max_hits: Math.max(1, Math.min(Number(node.max_hits || 3), 10)),
    }))
    .filter((node, index, all) =>
      !roleNodeIds.has(node.id) && all.findIndex((item) => item.id === node.id) === index
    );
  const allNodes = [...nodes, ...cleanExtraNodes];
  const validIds = new Set(allNodes.map((node) => node.id));
  const seen = new Set<string>();
  const cleanEdges = edges.filter((edge) => {
    if (!validIds.has(edge.from) || !validIds.has(edge.to) || edge.from === edge.to) return false;
    const key = `${edge.from}->${edge.to}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  return { nodes: allNodes, edges: cleanEdges };
};

const readDagSpec = (flow?: DialogFlow | null): DagFlowSpec => {
  const spec = (flow?.flow_spec || {}) as Partial<DagFlowSpec>;
  const fallback = buildDagSpec(flow?.role_ids || [], []);
  if (!Array.isArray(spec.nodes)) return fallback;
  const nodes = spec.nodes
    .filter((node) =>
      node && typeof node.id === "string" &&
      (node.type === "graphrag" || typeof node.role_id === "string")
    )
    .map((node) => ({
      id: node.id,
      type: node.type === "graphrag" ? "graphrag" as const : "role" as const,
      role_id: node.type === "graphrag" ? (node.role_id || graphRagRoleId(node.id)) : node.role_id,
      label: node.label || node.id,
      prompt_template: node.prompt_template || "",
      query_template: node.query_template || "{input}",
      max_hits: Number(node.max_hits || 3),
    }));
  const ids = new Set(nodes.map((node) => node.id));
  const edges = Array.isArray(spec.edges)
    ? spec.edges.filter((edge) => ids.has(edge.from) && ids.has(edge.to) && edge.from !== edge.to)
    : [];
  return { nodes: nodes.length ? nodes : fallback.nodes, edges };
};

const runPanelsForFlow = (flow: DialogFlow): RunRolePanel[] => {
  if (flow.flow_type === "dag") {
    return readDagSpec(flow).nodes.map((node) => ({
      role_id: dagNodeActorId(node),
      node_id: node.id,
      node_type: node.type || "role",
      label: node.label || dagNodeActorId(node),
      status: "pending" as const,
      content: "",
    }));
  }
  return (flow.role_ids || []).map((rid) => ({ role_id: rid, status: "pending" as const, content: "" }));
};

const hydratedRunPanels = (
  flow: DialogFlow,
  run: FlowRun,
  currentPanels: RunRolePanel[] = [],
): RunRolePanel[] => {
  const next = (currentPanels.length > 0 ? currentPanels : runPanelsForFlow(flow)).map((panel) => ({ ...panel }));
  const used = new Set<number>();

  const findPanelForOutput = (roleId: string, outputIndex: number) => {
    if (outputIndex >= 0 && outputIndex < next.length && next[outputIndex].role_id === roleId && !used.has(outputIndex)) {
      return outputIndex;
    }
    const emptyMatch = next.findIndex((panel, index) =>
      !used.has(index) &&
      panel.role_id === roleId &&
      !panel.content &&
      !panel.error &&
      (panel.status === "pending" || panel.status === "running")
    );
    if (emptyMatch >= 0) return emptyMatch;
    return next.findIndex((panel, index) => !used.has(index) && panel.role_id === roleId);
  };

  (run.outputs || []).forEach((output, outputIndex) => {
    const roleId = output.role_id || `output-${outputIndex + 1}`;
    const panelIndex = findPanelForOutput(roleId, outputIndex);
    const status: RunRolePanel["status"] = output.error ? "failed" : "completed";
    const latency = typeof output.latency_ms === "number" ? output.latency_ms : undefined;
    const patch: RunRolePanel = {
      role_id: roleId,
      status,
      content: output.content || "",
      error: output.error || undefined,
      latency_ms: latency,
    };

    if (panelIndex >= 0) {
      used.add(panelIndex);
      next[panelIndex] = { ...next[panelIndex], ...patch };
      return;
    }

    next.push({
      ...patch,
      node_id: roleId.startsWith("graphrag:") ? roleId.slice("graphrag:".length) : undefined,
      node_type: roleId.startsWith("graphrag:") ? "graphrag" : "role",
      label: roleId.startsWith("graphrag:") ? "GraphRAG" : roleId,
    });
    used.add(next.length - 1);
  });

  return next;
};

export default function FlowsPage() {
  const { user } = useAppStore();

  /* ── Data ── */
  const [roles, setRoles] = useState<ExpertRole[]>([]);
  const [managedSkills, setManagedSkills] = useState<Skill[]>([]);
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
  const [dagEdges, setDagEdges] = useState<DagFlowEdge[]>([]);
  const [dagExtraNodes, setDagExtraNodes] = useState<DagFlowNode[]>([]);
  const [roleContracts, setRoleContracts] = useState<Record<string, RoleContractDraft>>({});
  const [adjudication, setAdjudication] = useState<AdjudicationDraft>({});
  const [activeContractRoleId, setActiveContractRoleId] = useState<string>("");
  const [searchKeyword, setSearchKeyword] = useState("");
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [saving, setSaving] = useState(false);

  /* ── Run state ── */
  const [activeFlowId, setActiveFlowId] = useState<number | null>(null);
  const [runInput, setRunInput] = useState("");
  const [running, setRunning] = useState(false);
  const [runRoles, setRunRoles] = useState<RunRolePanel[]>([]);
  const [runError, setRunError] = useState<string>("");
  const [pastRuns, setPastRuns] = useState<FlowRun[]>([]);
  const [currentRunId, setCurrentRunId] = useState<number | null>(null);
  const [currentRunSucceeded, setCurrentRunSucceeded] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<FlowAttachment[]>([]);
  const [collaborationMessages, setCollaborationMessages] = useState<CollaborationMessage[]>([]);
  const [collabLoading, setCollabLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const lastSeqRef = useRef(0);
  const lastCollabSeqRef = useRef(0);
  const stopStreamRef = useRef(false);

  /* ── Tab state ── */
  const [skillTabs, setSkillTabs] = useState<SkillTab[]>([]);
  const [activeTab, setActiveTab] = useState<string>("software-engineering");
  const [tabRoles, setTabRoles] = useState<TabRole[]>([]);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [deletingTabId, setDeletingTabId] = useState<string | null>(null);

  /* ── Load data ── */
  const refreshManagedSkills = async () => {
    try {
      const res = await skillApi.list();
      setManagedSkills(res.skills || []);
    } catch {
      setManagedSkills([]);
    }
  };

  const loadAll = async () => {
    setLoading(true);
    try {
      const [r, managed, s, f, t] = await Promise.all([
        hermesApi.listRoles(),
        skillApi.list().catch(() => ({ skills: [] as Skill[] })),
        hermesApi.listScenarios(),
        hermesApi.listFlows(user?.id),
        tabsApi.listTabs(),
      ]);
      setRoles(r.roles || []);
      setManagedSkills(managed.skills || []);
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

  const relevantRoles = useMemo(() => roles.filter(isRelevantExpertRole), [roles]);
  const relevantManagedSkills = useMemo(
    () => managedSkills.filter((skill) => skill.enabled),
    [managedSkills],
  );
  const relevantTabRoles = useMemo(() => tabRoles, [tabRoles]);

  const allowedRoleIds = useMemo(() => {
    const ids = new Set<string>();
    relevantRoles.forEach((role) => ids.add(role.id));
    relevantManagedSkills.forEach((skill) => ids.add(skill.name));
    relevantTabRoles.forEach((role) => ids.add(role.role_id));
    return ids;
  }, [relevantRoles, relevantManagedSkills, relevantTabRoles]);

  const defaultFlowRoleIds = useMemo(
    () => DEFAULT_FLOW_ROLE_IDS.filter((roleId) => allowedRoleIds.has(roleId)),
    [allowedRoleIds],
  );

  const keepAllowedOrUnknownRole = useCallback((roleId: string) => {
    if (allowedRoleIds.has(roleId)) return true;
    if (isExplicitlyBlockedRoleId(roleId)) return false;
    return !roles.some((role) => role.id === roleId) &&
      !managedSkills.some((skill) => skill.name === roleId) &&
      !tabRoles.some((role) => role.role_id === roleId);
  }, [allowedRoleIds, managedSkills, roles, tabRoles]);

  useEffect(() => {
    if (!composerOpen) return;
    setSelectedRoles((prev) => prev.filter(keepAllowedOrUnknownRole));
  }, [composerOpen, keepAllowedOrUnknownRole]);

  useEffect(() => {
    if (flowType !== "dag") return;
    const validIds = new Set(buildDagSpec(selectedRoles, [], dagExtraNodes).nodes.map((node) => node.id));
    setDagEdges((prev) => prev.filter((edge) =>
      validIds.has(edge.from) && validIds.has(edge.to) && edge.from !== edge.to
    ));
  }, [flowType, selectedRoles, dagExtraNodes]);

  useEffect(() => {
    if (!composerOpen) return;
    const validRoleIds = new Set(selectedRoles);
    setRoleContracts((prev) => Object.fromEntries(
      Object.entries(prev).filter(([roleId]) => validRoleIds.has(roleId))
    ));
    setActiveContractRoleId((prev) => {
      if (prev && validRoleIds.has(prev)) return prev;
      return selectedRoles[0] || "";
    });
  }, [composerOpen, selectedRoles]);

  const loadTabRoles = async (tabId: string) => {
    if (tabId === MANAGED_SKILLS_TAB_ID) {
      setTabRoles([]);
      void refreshManagedSkills();
      return;
    }
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
    setFilterCategory("all");
    loadTabRoles(tabId);
  };

  const handleDeleteSkillTab = async (tab: SkillTab) => {
    if (tab.source_type === "builtin" || tab.id === "software-engineering" || tab.id === MANAGED_SKILLS_TAB_ID) {
      message.warning("内置 Skill Tab 不支持删除");
      return;
    }

    setDeletingTabId(tab.id);
    try {
      const res = await tabsApi.listTabRoles(tab.id);
      const removedRoleIds = new Set((res.roles || []).map((role) => role.role_id));
      await tabsApi.deleteTab(tab.id);

      setSkillTabs((prev) => prev.filter((item) => item.id !== tab.id));
      setSelectedRoles((prev) => prev.filter((roleId) => !removedRoleIds.has(roleId)));

      if (activeTab === tab.id) {
        setActiveTab("software-engineering");
        setTabRoles([]);
        setSearchKeyword("");
        setFilterCategory("all");
      }

      message.success(`已删除 ${tabDisplayName(tab)}，并移除 ${removedRoleIds.size} 个 Skill`);
    } catch (e) {
      message.error("删除失败：" + (e instanceof Error ? e.message : "网络错误"));
    } finally {
      setDeletingTabId(null);
    }
  };

  /* ── Composer helpers ── */

  const openComposer = (flow?: DialogFlow) => {
    if (flow) {
      setEditingFlow(flow);
      setFlowName(flow.name || "");
      setFlowDesc(flow.description || "");
      setFlowType(flow.flow_type || "sequential");
      setSelectedRoles([...(flow.role_ids || [])].filter(keepAllowedOrUnknownRole));
      setSelectedScenario(flow.scenario_id || "");
      setPromptTemplate(flow.prompt_template || "");
      setSelectedModel(flow.model || "deepseek-v4-flash");
      const dagSpec = readDagSpec(flow);
      setDagEdges(dagSpec.edges);
      setDagExtraNodes(dagSpec.nodes.filter((node) => node.type === "graphrag"));
      setRoleContracts(readRoleContracts(flow));
      setAdjudication(readAdjudication(flow));
      setActiveContractRoleId((flow.role_ids || [])[0] || "");
    } else {
      setEditingFlow(null);
      setFlowName("");
      setFlowDesc("");
      setFlowType("dag");
      setSelectedRoles(defaultFlowRoleIds);
      setSelectedScenario("");
      setPromptTemplate("");
      setSelectedModel("deepseek-v4-flash");
      setDagEdges([]);
      setDagExtraNodes([]);
      setRoleContracts({});
      setAdjudication({});
      setActiveContractRoleId(defaultFlowRoleIds[0] || "");
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
    const installed = new Set(allowedRoleIds);
    const recommended = (sc.recommended_roles || []).filter((rid) => installed.has(rid));
    if (recommended.length > 0) {
      setSelectedRoles((prev) => Array.from(new Set([...prev, ...recommended])));
    }
  };

  const createProductDeliveryFlows = async () => {
    const installed = new Set(allowedRoleIds);
    const prepared = PRODUCT_DELIVERY_STAGES.map((stage, index) => {
      const matched = stage.roles.filter((rid) => installed.has(rid));
      const fallback = matched.length === 0
        ? (defaultFlowRoleIds.length ? defaultFlowRoleIds : relevantRoles[0]?.id ? [relevantRoles[0].id] : [])
        : [];
      const roleIds = matched.length > 0 ? matched : fallback;
      const flowType = roleIds.length < (stage.minRoles || 1) ? "sequential" : stage.flowType;
      return { stage, index, roleIds, flowType };
    }).filter((item) => item.roleIds.length > 0);

    if (prepared.length === 0) {
      message.warning("未找到可用的软件开发角色，请先加载或导入相关 Skill");
      return;
    }

    setSaving(true);
    try {
      for (const item of prepared) {
        await hermesApi.createFlow({
          name: `${String(item.index + 1).padStart(2, "0")}. ${item.stage.name}`,
          description: item.stage.description,
          flow_type: item.flowType,
          role_ids: item.roleIds,
          scenario_id: "",
          prompt_template: productDeliveryPrompt(item.stage, item.index),
          model: "deepseek-v4-pro",
          owner_id: user?.id || 0,
          flow_spec: {
            preset: "product-delivery",
            stage_index: item.index + 1,
            stage_name: item.stage.name,
            original_flow_type: item.stage.flowType,
          },
        });
      }
      message.success(`已创建 ${prepared.length} 个独立流程`);
      closeComposer();
      await loadAll();
    } catch (e) {
      message.error("创建流程失败：" + (e instanceof Error ? e.message : "未知错误"));
    } finally {
      setSaving(false);
    }
  };

  const previewProductDeliveryStage = (stage: ProductDeliveryStagePreset, index: number) => {
    const installed = new Set(allowedRoleIds);
    const matched = stage.roles.filter((rid) => installed.has(rid));
    setEditingFlow(null);
    setFlowName(`${String(index + 1).padStart(2, "0")}. ${stage.name}`);
    setFlowDesc(stage.description);
    setFlowType(matched.length < (stage.minRoles || 1) ? "sequential" : stage.flowType);
    setSelectedRoles(matched.length > 0 ? matched : defaultFlowRoleIds.length ? defaultFlowRoleIds : relevantRoles[0]?.id ? [relevantRoles[0].id] : []);
    setSelectedScenario("");
    setPromptTemplate(productDeliveryPrompt(stage, index));
    setSelectedModel("deepseek-v4-pro");
    setDagEdges([]);
    setDagExtraNodes([]);
    setRoleContracts({});
    setAdjudication({});
    setActiveContractRoleId((matched.length > 0 ? matched : defaultFlowRoleIds)[0] || "");
    setSearchKeyword("");
    setFilterCategory("all");
    void handleTabSwitch("software-engineering");
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
    return relevantRoles.filter((r) => {
      if (filterCategory !== "all" && r.category !== filterCategory) return false;
      if (!kw) return true;
      return (
        r.id.toLowerCase().includes(kw) ||
        r.name.toLowerCase().includes(kw) ||
        (r.description || "").toLowerCase().includes(kw) ||
        (r.triggers || []).some((t) => t.toLowerCase().includes(kw))
      );
    });
  }, [relevantRoles, searchKeyword, filterCategory]);

  const rolesByCategory = useMemo(() => {
    const m: Record<string, ExpertRole[]> = {};
    for (const r of filteredRoles) {
      const c = r.category || "other";
      if (!m[c]) m[c] = [];
      m[c].push(r);
    }
    return m;
  }, [filteredRoles]);

  const filteredManagedSkills = useMemo(() => {
    const kw = searchKeyword.trim().toLowerCase();
    return relevantManagedSkills.filter((skill) => {
      if (!kw) return true;
      return (
        skill.name.toLowerCase().includes(kw) ||
        (skill.description || "").toLowerCase().includes(kw) ||
        (skill.author || "").toLowerCase().includes(kw) ||
        (skill.keywords || []).some((item) => item.toLowerCase().includes(kw)) ||
        (skill.tools || []).some((tool) =>
          tool.name.toLowerCase().includes(kw) || (tool.description || "").toLowerCase().includes(kw)
        )
      );
    });
  }, [relevantManagedSkills, searchKeyword]);

  const roleMetaById = useMemo(() => {
    const m = new Map<string, { name?: string; description?: string; category?: string }>();
    for (const role of roles) {
      m.set(role.id, { name: role.name, description: role.description, category: role.category });
    }
    for (const skill of managedSkills) {
      m.set(skill.name, { name: skill.name, description: skill.description, category: "技能管理" });
    }
    for (const role of tabRoles) {
      m.set(role.role_id, { name: role.display_name, description: role.description, category: role.category || "导入角色" });
    }
    return m;
  }, [roles, managedSkills, tabRoles]);

  const canvasRolesById = useMemo(() => {
    const m = new Map<string, { id: string; name: string; description: string; category: string }>();
    for (const rid of selectedRoles) {
      const meta = roleMetaById.get(rid);
      const zh = roleZh(rid, meta?.name, meta?.description);
      m.set(rid, {
        id: rid,
        name: zh.name,
        description: zh.description,
        category: meta?.category || "skill",
      });
    }
    return m;
  }, [roleMetaById, selectedRoles]);

  const filteredTabRoles = useMemo(() => {
    const kw = searchKeyword.trim().toLowerCase();
    return relevantTabRoles.filter((r) => {
      if (!kw) return true;
      return (
        r.role_id.toLowerCase().includes(kw) ||
        r.display_name.toLowerCase().includes(kw) ||
        (r.description || "").toLowerCase().includes(kw) ||
        (r.category || "").toLowerCase().includes(kw) ||
        (r.capabilities || []).some((item) => item.toLowerCase().includes(kw))
      );
    });
  }, [relevantTabRoles, searchKeyword]);

  const roleTreeData = useMemo(() => {
    if (activeTab === "software-engineering") {
      return CATEGORY_ORDER.filter((c) => rolesByCategory[c]?.length).map((c) => ({
        key: `category:${c}`,
        title: `${CATEGORY_LABELS[c]} (${rolesByCategory[c].length})`,
        selectable: false,
        children: rolesByCategory[c].map((r) => {
          const zh = roleZh(r.id, r.name, r.description);
          return {
            key: r.id,
            title: (
              <Tooltip title={zh.description} placement="left">
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6, maxWidth: "100%" }}>
                  <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {zh.name}
                  </span>
                  <Tag style={{ fontSize: 10, lineHeight: "16px", margin: 0 }}>{CATEGORY_LABELS[r.category] || "其他"}</Tag>
                </span>
              </Tooltip>
            ),
          };
        }),
      }));
    }

    if (activeTab === MANAGED_SKILLS_TAB_ID) {
      return [
        { key: "enabled", title: `已启用 (${filteredManagedSkills.length})`, skills: filteredManagedSkills },
      ].filter((group) => group.skills.length > 0).map((group) => ({
        key: `managed-skill:${group.key}`,
        title: group.title,
        selectable: false,
        children: group.skills.map((skill) => ({
          key: skill.name,
          title: (
            <Tooltip title={skill.description || "暂无中文说明"} placement="left">
              <span style={{ display: "inline-flex", alignItems: "center", gap: 6, maxWidth: "100%" }}>
                <span style={{
                  minWidth: 0,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  color: skill.enabled ? undefined : "#8c8c8c",
                }}>
                  {roleZh(skill.name, skill.name, skill.description).name}
                </span>
                <Tag style={{ fontSize: 10, lineHeight: "16px", margin: 0 }} color="cyan">
                  已启用
                </Tag>
              </span>
            </Tooltip>
          ),
        })),
      }));
    }

    const groups = Array.from(new Set(filteredTabRoles.map((r) => r.classification || "other")));
    return groups.map((group) => {
      const groupRoles = filteredTabRoles.filter((r) => (r.classification || "other") === group);
      return {
        key: `tab-category:${group}`,
        title: `${categoryDisplayName(group)} (${groupRoles.length})`,
        selectable: false,
        children: groupRoles.map((r) => {
          const zh = roleZh(r.role_id, r.display_name, r.description);
          return {
            key: r.role_id,
            title: (
              <Tooltip title={zh.description} placement="left">
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6, maxWidth: "100%" }}>
                  <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {zh.name}
                  </span>
                  <Tag style={{ fontSize: 10, lineHeight: "16px", margin: 0 }} color={group === "planning" ? "blue" : "green"}>
                    {categoryDisplayName(r.category)}
                  </Tag>
                </span>
              </Tooltip>
            ),
          };
        }),
      };
    }).filter((group) => group.children.length > 0);
  }, [activeTab, filteredManagedSkills, filteredTabRoles, rolesByCategory]);

  const visibleRoleIds = useMemo(() => {
    if (activeTab === "software-engineering") return new Set(filteredRoles.map((r) => r.id));
    if (activeTab === MANAGED_SKILLS_TAB_ID) {
      return new Set(filteredManagedSkills.map((skill) => skill.name));
    }
    return new Set(filteredTabRoles.map((r) => r.role_id));
  }, [activeTab, filteredManagedSkills, filteredRoles, filteredTabRoles]);

  const handleRoleTreeCheck = (checked: Key[] | { checked: Key[]; halfChecked: Key[] }) => {
    const checkedKeys = Array.isArray(checked) ? checked : checked.checked;
    const nextVisible = new Set(checkedKeys.map(String).filter((key) => visibleRoleIds.has(key)));
    setSelectedRoles((prev) => {
      const hiddenSelections = prev.filter((id) => !visibleRoleIds.has(id));
      return [...hiddenSelections, ...Array.from(nextVisible)];
    });
  };

  const displayedSkillTabs = useMemo(() => {
    const tabs = skillTabs.filter((tab) => tab.id !== MANAGED_SKILLS_TAB_ID);
    const builtInIndex = tabs.findIndex((tab) => tab.id === "software-engineering");
    const managedTab = { ...MANAGED_SKILLS_TAB, role_count: relevantManagedSkills.length };
    if (builtInIndex < 0) return [managedTab, ...tabs];
    return [
      ...tabs.slice(0, builtInIndex + 1),
      managedTab,
      ...tabs.slice(builtInIndex + 1),
    ];
  }, [relevantManagedSkills.length, skillTabs]);

  const roleInventoryStats = useMemo(() => {
    const importedTabRoles = skillTabs.reduce((sum, tab) => {
      if (tab.id === "software-engineering" || tab.id === MANAGED_SKILLS_TAB_ID) return sum;
      return sum + Number(tab.role_count || 0);
    }, 0);
    const managedSkillRoles = relevantManagedSkills.length;
    const baseRoles = roles.length;
    return {
      baseRoles,
      importedTabRoles,
      managedSkillRoles,
      total: baseRoles + importedTabRoles + managedSkillRoles,
    };
  }, [relevantManagedSkills.length, roles.length, skillTabs]);

  const saveFlow = async () => {
    const saveRoleIds = selectedRoles.filter(keepAllowedOrUnknownRole);
    if (saveRoleIds.length === 0) { message.warning("Please select at least 1 role"); return; }
    if (!flowName.trim()) { message.warning("请填写流程名称"); return; }
    if (selectedRoles.length === 0) { message.warning("至少选择 1 个角色"); return; }
    if (flowType === "hierarchical" && saveRoleIds.length < 2) {
      message.warning("主从模式至少需要 1 个主控角色和 1 个 worker 角色");
      return;
    }
    if (flowType === "competitive" && saveRoleIds.length < 2) {
      message.warning("竞争模式至少需要 1 个裁决角色和 1 个候选角色");
      return;
    }
    if (flowType === "pipeline" && saveRoleIds.length < 2) {
      message.warning("流水线模式至少需要 2 个阶段角色");
      return;
    }
    if (flowType === "peer_to_peer" && saveRoleIds.length < 2) {
      message.warning("对等协作至少需要 2 个角色");
      return;
    }
    const previousSpec = asPlainRecord(editingFlow?.flow_spec);
    const baseSpec = { ...previousSpec };
    delete baseSpec.nodes;
    delete baseSpec.edges;
    delete baseSpec.role_contracts;
    delete baseSpec.roles;
    delete baseSpec.adjudication;
    delete baseSpec.judge;
    if (flowType === "dag") {
      Object.assign(baseSpec, buildDagSpec(saveRoleIds, dagEdges, dagExtraNodes) as unknown as Record<string, unknown>);
    }
    Object.assign(baseSpec, buildCollaborationSpec(saveRoleIds, roleContracts, adjudication));
    const flowSpec = Object.keys(baseSpec).length > 0 ? baseSpec : {};
    setSaving(true);
    try {
      if (editingFlow) {
        await hermesApi.updateFlow(editingFlow.id, {
          name: flowName.trim(),
          description: flowDesc,
          flow_type: flowType,
          role_ids: saveRoleIds,
          scenario_id: selectedScenario,
          prompt_template: promptTemplate,
          model: selectedModel,
          flow_spec: flowSpec,
        });
        message.success("流程已更新");
      } else {
        await hermesApi.createFlow({
          name: flowName.trim(),
          description: flowDesc,
          flow_type: flowType,
          role_ids: saveRoleIds,
          scenario_id: selectedScenario,
          prompt_template: promptTemplate,
          model: selectedModel,
          owner_id: user?.id || 0,
          flow_spec: flowSpec,
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

  const resetCollaborationState = () => {
    setCollaborationMessages([]);
    lastCollabSeqRef.current = 0;
  };

  const refreshCollaborationMessages = async (runId: number) => {
    setCollabLoading(true);
    try {
      const res = await hermesApi.listCollaborationMessages(runId, lastCollabSeqRef.current);
      const messages = res.messages || [];
      if (messages.length > 0) {
        setCollaborationMessages((prev) => [...prev, ...messages]);
        lastCollabSeqRef.current = Math.max(
          lastCollabSeqRef.current,
          ...messages.map((m) => m.seq || 0),
        );
      }
    } catch {
      /* best-effort collaboration trace */
    } finally {
      setCollabLoading(false);
    }
  };

  const selectFlow = async (id: number) => {
    setActiveFlowId(id);
    setRunRoles([]);
    setRunError("");
    setRunInput("");
    setCurrentRunId(null);
    setCurrentRunSucceeded(false);
    resetCollaborationState();
    setPastRuns([]);
    try {
      const r = await hermesApi.listRuns(id);
      setPastRuns((r.runs || []).slice(0, 10));
    } catch { /* ignore */ }
  };

  const startRun = async () => {
    const flow = flows.find((f) => f.id === activeFlowId);
    if (!flow) { message.warning("先选择一个流程"); return; }
    if (!runInput.trim() && attachedFiles.length === 0) { message.warning("请输入运行内容或上传附件"); return; }
    setRunning(true);
    setRunError("");
    setCurrentRunId(null);
    setCurrentRunSucceeded(false);
    setRunRoles(runPanelsForFlow(flow));
    lastSeqRef.current = 0;
    resetCollaborationState();
    stopStreamRef.current = false;

    let fullMessage = runInput.trim();
    if (attachedFiles.length > 0) {
      const fileParts = attachedFiles.map(attachmentMessagePart).join("");
      fullMessage = fullMessage ? fullMessage + fileParts : fileParts.trim();
    }

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const started = await hermesApi.startFlowRun(flow.id, fullMessage, ctrl.signal);
      setCurrentRunId(started.run_id);
      await attachRunStream(started.run_id, flow, ctrl);
    } catch (e) {
      if (e instanceof Error && e.name !== "AbortError") {
        setRunError(e.message);
        message.error("启动失败：" + e.message);
        setRunning(false);
      }
    } finally {
      abortRef.current = null;
      try {
        const r = await hermesApi.listRuns(flow.id);
        setPastRuns((r.runs || []).slice(0, 10));
      } catch { /* ignore */ }
    }
  };

  const isTerminalRunEvent = (ev: RunEvent) =>
    ev.type === "run_completed" || ev.type === "run_failed" || ev.type === "run_cancelled";

  const isTerminalRunStatus = (status: FlowRun["status"]) =>
    status === "succeeded" || status === "failed" || status === "cancelled";

  const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  const hydrateRunFromSnapshot = (run: FlowRun, flow: DialogFlow) => {
    setCurrentRunId(run.id);
    setCurrentRunSucceeded(run.status === "succeeded");
    setRunError(
      run.status === "failed" ? (run.error || "Run failed") :
      run.status === "cancelled" ? (run.error || "Cancelled") :
      ""
    );
    setRunning(run.status === "pending" || run.status === "running");
    setRunRoles((prev) => hydratedRunPanels(flow, run, prev));
  };

  const replayRunEvents = async (runId: number) => {
    while (true) {
      const res = await hermesApi.listRunEvents(runId, lastSeqRef.current);
      const events = res.events || [];
      if (events.length === 0) return;

      let maxSeq = lastSeqRef.current;
      let hasCollaborationEvent = false;
      for (const ev of events) {
        applyRunEvent(ev);
        if (ev.type !== "role_output") hasCollaborationEvent = true;
        if (typeof ev.seq === "number") maxSeq = Math.max(maxSeq, ev.seq);
      }
      if (maxSeq <= lastSeqRef.current) return;
      lastSeqRef.current = maxSeq;
      if (hasCollaborationEvent) void refreshCollaborationMessages(runId);
      if (events.length < 500) return;
    }
  };

  const attachRunStream = async (runId: number, flow: DialogFlow, ctrl: AbortController) => {
    let attempt = 0;
    while (!stopStreamRef.current && !ctrl.signal.aborted) {
      try {
        for await (const ev of streamRunEvents(runId, lastSeqRef.current, ctrl.signal)) {
          if (typeof ev.seq === "number") lastSeqRef.current = ev.seq;
          applyRunEvent(ev);
          if (ev.type !== "role_output") {
            void refreshCollaborationMessages(runId);
          }
          if (isTerminalRunEvent(ev)) {
            await refreshCollaborationMessages(runId);
            const run = await hermesApi.getRun(runId);
            hydrateRunFromSnapshot(run, flow);
            return;
          }
        }
        await replayRunEvents(runId);
        const run = await hermesApi.getRun(runId);
        if (isTerminalRunStatus(run.status)) {
          hydrateRunFromSnapshot(run, flow);
          return;
        }
      } catch (e) {
        if (ctrl.signal.aborted || stopStreamRef.current) return;
        try {
          await replayRunEvents(runId);
          const run = await hermesApi.getRun(runId);
          if (isTerminalRunStatus(run.status)) {
            hydrateRunFromSnapshot(run, flow);
            return;
          }
        } catch {
          /* keep reconnecting */
        }
        attempt += 1;
        message.warning("连接中断，任务仍在后台运行，正在重连...");
        await sleep(Math.min(1000 * 2 ** Math.min(attempt - 1, 4), 15000));
        continue;
      }
      attempt = 0;
      await sleep(1000);
    }
    try {
      const r = await hermesApi.listRuns(flow.id);
      setPastRuns((r.runs || []).slice(0, 10));
    } catch { /* ignore */ }
  };

  const applyRunEvent = (ev: RunEvent) => {
    setRunRoles((prev) => {
      const next = [...prev];
      const findIdx = (rid?: string, idx?: number) => {
        if ("node_id" in ev && ev.node_id) {
          const byNode = next.findIndex((p) => p.node_id === ev.node_id);
          if (byNode >= 0) return byNode;
        }
        if (idx !== undefined && idx >= 0 && idx < next.length && next[idx].role_id === rid) return idx;
        return next.findIndex((p) => p.role_id === rid);
      };
      const ensurePanel = (rid?: string, idx?: number) => {
        const i = findIdx(rid, idx);
        if (i >= 0) return i;
        if (!rid) return -1;
        next.push({
          role_id: rid,
          node_id: "node_id" in ev ? ev.node_id : undefined,
          node_type: rid.startsWith("graphrag:") ? "graphrag" : "role",
          label: rid.startsWith("graphrag:") ? "GraphRAG" : rid,
          status: "pending",
          content: "",
        });
        return next.length - 1;
      };
      switch (ev.type) {
        case "run_started":
          setCurrentRunId(ev.run_id);
          setCurrentRunSucceeded(false);
          if (ev.flow_type === "dag" && Array.isArray(ev.dag_nodes) && ev.dag_nodes.length > 0) {
            return ev.dag_nodes.map((node) => ({
              role_id: dagNodeActorId(node),
              node_id: node.id,
              node_type: node.type || "role",
              label: node.label || dagNodeActorId(node),
              status: "pending" as const,
              content: "",
            }));
          }
          break;
        case "role_started": {
          const i = ensurePanel(ev.role_id, ev.index);
          if (i >= 0) next[i] = { ...next[i], status: "running" };
          break;
        }
        case "role_output": {
          // Streaming text chunk — append to current role content
          const i = ensurePanel(ev.role_id, ev.index);
          if (i >= 0) next[i] = {
            ...next[i], status: "running",
            content: (next[i].content || "") + (ev.content || ""),
          };
          break;
        }
        case "role_completed": {
          const i = ensurePanel(ev.role_id, ev.index);
          if (i >= 0) next[i] = {
            ...next[i], status: "completed",
            content: ev.content, latency_ms: ev.latency_ms,
          };
          break;
        }
        case "conflict_resolved": {
          const resolverId = ev.role_id || "orchestrator/resolver";
          const i = next.findIndex((p) => p.role_id === resolverId);
          const panel = {
            role_id: resolverId,
            status: "completed" as const,
            content: ev.content || "",
            latency_ms: ev.latency_ms || 0,
          };
          if (i >= 0) next[i] = panel;
          else next.push(panel);
          break;
        }
        case "role_failed": {
          const i = ensurePanel(ev.role_id, ev.index);
          if (i >= 0) next[i] = {
            ...next[i], status: "failed",
            error: ev.error, latency_ms: ev.latency_ms,
          };
          break;
        }
        case "run_completed":
          setCurrentRunSucceeded(true);
          setRunning(false);
          break;
        case "run_failed":
          setCurrentRunSucceeded(false);
          setRunError(ev.error);
          setRunning(false);
          break;
        case "run_cancelled":
          setCurrentRunSucceeded(false);
          setRunError(ev.error || "已取消");
          setRunning(false);
          break;
        case "error":
          setCurrentRunSucceeded(false);
          setRunError(ev.error);
          break;
      }
      return next;
    });
  };

  const cancelRun = async () => {
    stopStreamRef.current = true;
    if (currentRunId) {
      try {
        await hermesApi.cancelRun(currentRunId);
        message.info("已取消");
      } catch (e) {
        message.error("取消失败：" + (e instanceof Error ? e.message : "未知错误"));
      }
    }
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setRunning(false);
  };

  const downloadRunArtifacts = async (runId: number) => {
    try {
      await hermesApi.downloadRunArtifacts(runId);
    } catch (e) {
      message.error("下载失败：" + (e instanceof Error ? e.message : "未知错误"));
    }
  };

  const viewRunOutputs = async (run: FlowRun) => {
    const flow = flows.find((f) => f.id === run.flow_id) || flows.find((f) => f.id === activeFlowId);
    if (!flow) return;
    stopStreamRef.current = true;
    setRunError("");
    setCurrentRunId(run.id);
    lastSeqRef.current = 0;
    resetCollaborationState();
    try {
      const latest = await hermesApi.getRun(run.id);
      hydrateRunFromSnapshot(latest, flow);
      await refreshCollaborationMessages(run.id);
    } catch (e) {
      message.error("Failed to load outputs: " + (e instanceof Error ? e.message : "Unknown error"));
    }
  };

  const deleteRun = async (runId: number) => {
    try {
      await hermesApi.deleteRun(runId);
      setPastRuns((prev) => prev.filter((r) => r.id !== runId));
      if (currentRunId === runId) {
        setCurrentRunId(null);
        setCurrentRunSucceeded(false);
        setRunRoles([]);
        setRunError("");
        resetCollaborationState();
      }
      message.success("任务已删除，工作目录已清理");
    } catch (e) {
      message.error("删除任务失败：" + (e instanceof Error ? e.message : "未知错误"));
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
  const roleMetaByRoleId = (id: string) => roleMetaById.get(id);
  const roleStatusById = new Map(runRoles.map((rp) => [rp.role_id, rp.status]));
  const activeRoleContract = activeContractRoleId ? roleContracts[activeContractRoleId] || {} : {};

  const updateActiveRoleContract = (field: keyof RoleContractDraft, value: string) => {
    if (!activeContractRoleId) return;
    setRoleContracts((prev) => ({
      ...prev,
      [activeContractRoleId]: {
        ...(prev[activeContractRoleId] || {}),
        [field]: value,
      },
    }));
  };

  const updateAdjudication = (field: keyof AdjudicationDraft, value: string) => {
    setAdjudication((prev) => ({ ...prev, [field]: value }));
  };

  const roleModeLabel = (flowType: FlowType, index: number) => {
    if (flowType === "hierarchical") return index === 0 ? "主控" : "执行者";
    if (flowType === "competitive") return index === 0 ? "裁决" : "候选";
    if (flowType === "pipeline") return `阶段 ${index + 1}`;
    if (flowType === "peer_to_peer") return "对等";
    if (flowType === "dag") return `节点 ${index + 1}`;
    return "";
  };

  const roleStatusColor = (status?: RunRolePanel["status"]) => {
    if (status === "running") return "blue";
    if (status === "completed") return "green";
    if (status === "failed") return "red";
    return "default";
  };

  const messageStatusColor = (status: CollaborationMessage["status"]) => {
    if (status === "sent") return "blue";
    if (status === "received") return "green";
    if (status === "failed") return "red";
    if (status === "timed_out") return "orange";
    return "default";
  };

  const flowMode总结 = (flow: DialogFlow) => {
    if (flow.flow_type === "hierarchical") return "主控角色负责任务拆解与最终总结，执行者并行处理子任务。";
    if (flow.flow_type === "competitive") return "候选角色并行给出方案，裁决角色汇总评审并输出选择依据。";
    if (flow.flow_type === "pipeline") return "各阶段通过队列逐段交接，上游输出作为下游输入。";
    if (flow.flow_type === "peer_to_peer") return "对等角色先独立回答，再相互广播评审，最后生成冲突解决结果。";
    if (flow.flow_type === "dag") return "按 DAG 依赖拓扑执行：根节点可并行运行，下游节点收到所有上游输出后启动。";
    if (flow.flow_type === "parallel") return "所有角色并行处理同一输入，结果独立返回。";
    return "角色按顺序依次处理，上一个成功输出作为后续上下文。";
  };

  const roleChip = (flow: DialogFlow, rid: string, idx: number) => {
    const r = roleMetaByRoleId(rid);
    const modeLabel = roleModeLabel(flow.flow_type, idx);
    const status = roleStatusById.get(rid);
    return (
      <Tag key={`${rid}-${idx}`} color={roleStatusColor(status)} style={{ margin: 0 }}>
        {idx + 1}. {roleZh(rid, r?.name, r?.description).name}{modeLabel && ` · ${modeLabel}`}
      </Tag>
    );
  };

  const dagNodeChip = (flow: DialogFlow, node: DagFlowNode, idx: number) => {
    if (node.type !== "graphrag") {
      return roleChip(flow, node.role_id || node.id, idx);
    }
    const actorId = dagNodeActorId(node);
    const status = roleStatusById.get(actorId);
    return (
      <Tag key={`${node.id}-${idx}`} color={roleStatusColor(status) || "gold"} style={{ margin: 0 }}>
        {idx + 1}. {node.label || "GraphRAG"} / KG
      </Tag>
    );
  };

  const relationshipView = (flow: DialogFlow) => {
    const ids = flow.role_ids || [];
    if (ids.length === 0) return null;
    const arrow = <span style={{ color: "#bfbfbf" }}>→</span>;
    let content;
    if (flow.flow_type === "hierarchical") {
      content = <>{roleChip(flow, ids[0], 0)}{arrow}<span>{ids.slice(1).map((rid, i) => roleChip(flow, rid, i + 1))}</span>{arrow}<Tag color="purple" style={{ margin: 0 }}>总结</Tag></>;
    } else if (flow.flow_type === "competitive") {
      content = <><span>{ids.slice(1).map((rid, i) => roleChip(flow, rid, i + 1))}</span>{arrow}{roleChip(flow, ids[0], 0)}</>;
    } else if (flow.flow_type === "parallel") {
      content = <><Tag color="blue" style={{ margin: 0 }}>输入</Tag>{arrow}<span>{ids.map((rid, i) => roleChip(flow, rid, i))}</span></>;
    } else if (flow.flow_type === "pipeline") {
      content = <><Tag color="cyan" style={{ margin: 0 }}>输入</Tag>{arrow}{ids.map((rid, i) => <span key={rid} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>{roleChip(flow, rid, i)}{i < ids.length - 1 && <><Tag color="cyan" style={{ margin: 0 }}>队列</Tag>{arrow}</>}</span>)}<Tag color="cyan" style={{ margin: 0 }}>输出</Tag></>;
    } else if (flow.flow_type === "peer_to_peer") {
      content = <><Tag color="green" style={{ margin: 0 }}>对等网络</Tag>{arrow}<span>{ids.map((rid, i) => roleChip(flow, rid, i))}</span>{arrow}<Tag color="green" style={{ margin: 0 }}>广播评审</Tag>{arrow}<Tag color="green" style={{ margin: 0 }}>冲突解决</Tag></>;
    } else if (flow.flow_type === "dag") {
      const spec = readDagSpec(flow);
      content = spec.edges.length === 0
        ? <><Tag color="gold" style={{ margin: 0 }}>输入</Tag>{arrow}<span>{ids.map((rid, i) => roleChip(flow, rid, i))}</span></>
        : <span>{spec.edges.map((edge, idx) => {
            const fromNode = spec.nodes.find((node) => node.id === edge.from);
            const toNode = spec.nodes.find((node) => node.id === edge.to);
            if (!fromNode || !toNode) return null;
            const fromIdx = spec.nodes.findIndex((node) => node.id === fromNode.id);
            const toIdx = spec.nodes.findIndex((node) => node.id === toNode.id);
            return (
              <span key={`${edge.from}-${edge.to}-${idx}`} style={{ display: "inline-flex", alignItems: "center", gap: 6, marginRight: 6 }}>
                {dagNodeChip(flow, fromNode, fromIdx >= 0 ? fromIdx : 0)}
                {arrow}
                {dagNodeChip(flow, toNode, toIdx >= 0 ? toIdx : 0)}
              </span>
            );
          })}</span>;
    } else {
      content = <>{ids.map((rid, i) => <span key={rid} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>{roleChip(flow, rid, i)}{i < ids.length - 1 && arrow}</span>)}</>;
    }
    return (
      <div style={{ padding: "8px 10px", background: "#fafafa", border: "1px solid #f0f0f0", borderRadius: 8, marginBottom: 12 }}>
        <div style={{ fontSize: 12, color: "#595959", marginBottom: 6 }}>{flowMode总结(flow)}</div>
        <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 6 }}>{content}</div>
      </div>
    );
  };

  const payloadPreview = (payload: Record<string, unknown>) => {
    const error = payload.error;
    if (typeof error === "string" && error) return error;
    const details = ["phase", "round", "queue", "strategy", "winner"]
      .map((key) => {
        const value = payload[key];
        return value !== undefined && value !== null && value !== "" ? `${key}: ${String(value)}` : "";
      })
      .filter(Boolean);
    for (const key of ["content_preview", "task_preview", "summary", "result", "content"]) {
      const value = payload[key];
      if (typeof value === "string" && value) return [...details, value].join("\n");
    }
    try {
      const raw = JSON.stringify(payload, null, 2);
      return raw.length > 500 ? raw.slice(0, 500) + "…" : raw;
    } catch {
      return "";
    }
  };

  return (
    <div
      data-flow-role-filter={FLOW_ROLE_FILTER_VERSION}
      style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}
    >
      {/* Top toolbar */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 16px", borderBottom: "1px solid #f0f0f0", flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 600 }}>多智能体编排</span>
          <Tooltip
            title={`基础角色 ${roleInventoryStats.baseRoles} / 导入 Skill Tab 角色 ${roleInventoryStats.importedTabRoles} / 技能管理 ${roleInventoryStats.managedSkillRoles}`}
          >
            <Tag color="blue">{roleInventoryStats.total} 个可用角色</Tag>
          </Tooltip>
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
                        <Tag style={{ fontSize: 10, lineHeight: "16px" }} color={FLOW_TYPE_META[f.flow_type].color}>
                          {FLOW_TYPE_META[f.flow_type].label}
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
                  <Tag color={FLOW_TYPE_META[activeFlow.flow_type].color}>
                    {FLOW_TYPE_META[activeFlow.flow_type].detail}
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
                    const r = roleMetaByRoleId(rid);
                    return (
                      <Tag key={rid} style={{ margin: 0 }}>
                        {idx + 1}. {roleZh(rid, r?.name, r?.description).name}
                      </Tag>
                    );
                  })}
                </div>
              </div>

              {/* 输入 + run */}
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
                        <PaperClipOutlined /> {f.name} ({(f.size / 1024).toFixed(1)}KB{f.inline ? "" : " / 未内联"})
                      </Tag>
                    ))}
                  </div>
                )}
                <div style={{ marginTop: 8, display: "flex", gap: 6, justifyContent: "flex-end" }}>
                  <Upload
                    accept=".md,.txt,.markdown,.csv,.json,.yaml,.yml,.doc,.docx,.pdf,.ppt,.pptx,.xls,.xlsx"
                    multiple
                    showUploadList={false}
                    beforeUpload={(file) => {
                      if (!isTextAttachment(file)) {
                        setAttachedFiles((prev) => [...prev, { name: file.name, content: "", inline: false, size: file.size }]);
                        message.warning(`${file.name} 是二进制/富文档文件，已作为附件名记录，未内联内容`);
                        return false;
                      }
                      const reader = new FileReader();
                      reader.onload = (e) => {
                        const content = e.target?.result as string;
                        if (content) {
                          setAttachedFiles((prev) => [...prev, { name: file.name, content, inline: true, size: file.size }]);
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
                  <Button icon={<ClearOutlined />} onClick={() => { setRunRoles([]); setRunError(""); resetCollaborationState(); }} disabled={running}>
                    清空输出
                  </Button>
                  {currentRunId && currentRunSucceeded && (
                    <Button icon={<DownloadOutlined />} onClick={() => downloadRunArtifacts(currentRunId)}>
                      下载材料
                    </Button>
                  )}
                  {currentRunId && !running && (
                    <Popconfirm
                      title="删除该任务并清理工作目录？"
                      okText="删除"
                      cancelText="取消"
                      onConfirm={() => deleteRun(currentRunId)}
                    >
                      <Button danger icon={<DeleteOutlined />}>删除任务</Button>
                    </Popconfirm>
                  )}
                </div>
              </div>

              {/* 输出 panels */}
              <div style={{ flex: 1, overflow: "auto", padding: "12px 20px" }}>
                {runRoles.some((rp) => rp.status === "completed") && (
                  <div style={{ marginBottom: 12, display: "flex", justifyContent: "flex-end", gap: 6 }}>
                    {currentRunId && currentRunSucceeded && (
                      <Button icon={<DownloadOutlined />} onClick={() => downloadRunArtifacts(currentRunId)}>
                        下载材料
                      </Button>
                    )}
                    {currentRunId && !running && (
                      <Popconfirm
                        title="删除该任务并清理工作目录？"
                        okText="删除"
                        cancelText="取消"
                        onConfirm={() => deleteRun(currentRunId)}
                      >
                        <Button danger icon={<DeleteOutlined />}>删除任务</Button>
                      </Popconfirm>
                    )}
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
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                                  <span style={{ fontWeight: 600, fontSize: 13 }}>Run #{r.id}</span>
                                  <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                    {r.status === "succeeded" && (
                                      <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadRunArtifacts(r.id)}>
                                        下载材料
                                      </Button>
                                    )}
                                    {(r.outputs || []).length > 0 && (
                                      <Button size="small" icon={<EyeOutlined />} onClick={() => viewRunOutputs(r)}>
                                        View output
                                      </Button>
                                    )}
                                    <Popconfirm
                                      title="删除该任务并清理工作目录？"
                                      okText="删除"
                                      cancelText="取消"
                                      onConfirm={() => deleteRun(r.id)}
                                      disabled={r.status === "running" || r.status === "pending"}
                                    >
                                      <Button
                                        size="small"
                                        danger
                                        icon={<DeleteOutlined />}
                                        disabled={r.status === "running" || r.status === "pending"}
                                      >
                                        删除任务
                                      </Button>
                                    </Popconfirm>
                                    <Tag color={
                                      r.status === "succeeded" ? "green" :
                                      r.status === "failed" ? "red" :
                                      r.status === "running" ? "blue" : "default"
                                    }>{r.status}</Tag>
                                  </div>
                                </div>
                                <div style={{ fontSize: 11, color: "#8c8c8c", marginTop: 4 }}>
                                  {formatServerDateTime(r.started_at)} · {(r.outputs || []).length} 个角色输出
                                </div>
                              </div>
                            ))}
                          </div>
                        ),
                      },
                    ]}
                  />
                ) : (
                  <Tabs
                    defaultActiveKey="outputs"
                    items={[
                      {
                        key: "outputs",
                        label: "角色输出",
                        children: (
                          <div>
                            {activeFlow && relationshipView(activeFlow)}
                            {runRoles.map((rp) => {
                              const r = roleMetaByRoleId(rp.role_id);
                              const activeIndex = activeFlow?.role_ids?.indexOf(rp.role_id) ?? -1;
                              const modeLabel = activeFlow && activeIndex >= 0 ? roleModeLabel(activeFlow.flow_type, activeIndex) : "";
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
                                    <span style={{ fontWeight: 600 }}>{roleZh(rp.role_id, r?.name, r?.description).name}</span>
                                    {modeLabel && <Tag color={FLOW_TYPE_META[activeFlow!.flow_type].color} style={{ fontSize: 10 }}>{modeLabel}</Tag>}
                                    <Tag style={{ fontSize: 10 }}>{r?.category ? CATEGORY_LABELS[r.category] : "导入角色"}</Tag>
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
                                      isDownloadableOutputContent(rp.content) ? (
                                        <div>
                                          <div style={{ marginBottom: 8, color: "#595959" }}>
                                            已生成文件：{inferredOutputFilename(rp.content)}
                                          </div>
                                          <InlineFileDownloadCard content={rp.content} />
                                        </div>
                                      ) : (
                                        <Suspense fallback={<div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{rp.content}</div>}>
                                          <MarkdownContent content={rp.content} />
                                        </Suspense>
                                      )
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
                        ),
                      },
                      {
                        key: "messages",
                        label: `协作消息 (${collaborationMessages.length})`,
                        children: collabLoading && collaborationMessages.length === 0 ? (
                          <div style={{ padding: 20, textAlign: "center" }}><Spin tip="加载协作消息..." /></div>
                        ) : collaborationMessages.length === 0 ? (
                          <Empty description="暂无协作消息" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                        ) : (
                          <div>
                            {collaborationMessages.map((msg) => {
                              const preview = payloadPreview(msg.payload || {});
                              return (
                                <div key={msg.id || `${msg.run_id}-${msg.seq}`} style={{
                                  padding: "10px 12px", marginBottom: 8,
                                  border: "1px solid #f0f0f0", borderRadius: 8,
                                  background: msg.status === "failed" ? "#fff2f0" : "#fff",
                                }}>
                                  <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                                    <Tag style={{ margin: 0 }}>#{msg.seq || "-"}</Tag>
                                    <Tag color={FLOW_TYPE_META[(activeFlow?.flow_type || "sequential") as FlowType].color} style={{ margin: 0 }}>{msg.type}</Tag>
                                    <Tag color={messageStatusColor(msg.status)} style={{ margin: 0 }}>{msg.status}</Tag>
                                    {msg.role_id && <Tag style={{ margin: 0 }}>{msg.role_id}</Tag>}
                                    <span style={{ fontSize: 12, color: "#595959" }}>{msg.from_agent} → {msg.to_agent}</span>
                                    {msg.created_at && (
                                      <span style={{ fontSize: 11, color: "#bfbfbf", marginLeft: "auto" }}>
                                        {formatServerTime(msg.created_at)}
                                      </span>
                                    )}
                                  </div>
                                  {preview && (
                                    <pre style={{
                                      margin: "8px 0 0", padding: 8,
                                      background: "#fafafa", borderRadius: 6,
                                      maxHeight: 120, overflow: "auto",
                                      whiteSpace: "pre-wrap", fontSize: 12,
                                    }}>{preview}</pre>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        ),
                      },
                    ]}
                  />
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Composer Modal ── */}
      <Modal
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span>{editingFlow ? "编辑流程" : "新建流程"}</span>
            <Tag color="gold" style={{ margin: 0 }}>DAG</Tag>
          </div>
        }
        open={composerOpen}
        onCancel={closeComposer}
        width="calc(100vw - 40px)"
        style={{ top: 18, maxWidth: 1560 }}
        styles={{ body: { padding: 0, height: "calc(100vh - 166px)", minHeight: 620 } }}
        footer={
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
            <div style={{ display: "flex", gap: 6 }}>
              {!editingFlow && (
                <>
                  <Button size="small" onClick={() => previewProductDeliveryStage(PRODUCT_DELIVERY_STAGES[0], 0)}>
                    预览模板
                  </Button>
                  <Button size="small" onClick={createProductDeliveryFlows} loading={saving}>
                    批量创建
                  </Button>
                </>
              )}
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <Button onClick={closeComposer}>取消</Button>
              <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={saveFlow}>
                保存
              </Button>
            </div>
          </div>
        }
      >
        <div className="flow-composer-layout">
          <aside className="flow-composer-panel flow-composer-left" style={{
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
            gap: 12,
            padding: 14,
            overflow: "auto",
            borderRight: "1px solid #e8e8e8",
            background: "#fff",
          }}>
            <section>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>流程配置</div>
              <div style={{ display: "grid", gap: 10 }}>
                <div>
                  <div style={{ fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>名称</div>
                  <Input value={flowName} onChange={(e) => setFlowName(e.target.value)} placeholder="例如：需求分析 DAG" />
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>描述</div>
                  <Input.TextArea
                    value={flowDesc}
                    onChange={(e) => setFlowDesc(e.target.value)}
                    autoSize={{ minRows: 2, maxRows: 3 }}
                    placeholder="可选"
                  />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <div>
                    <div style={{ fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>模式</div>
                    <Select
                      value={flowType}
                      onChange={setFlowType}
                      size="small"
                      style={{ width: "100%" }}
                      options={[
                        { value: "dag", label: "DAG 编排" },
                        { value: "sequential", label: "顺序" },
                        { value: "parallel", label: "并行" },
                        { value: "hierarchical", label: "主从" },
                        { value: "competitive", label: "竞争" },
                        { value: "pipeline", label: "流水线" },
                        { value: "peer_to_peer", label: "对等" },
                      ]}
                    />
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>模型</div>
                    <Select
                      value={selectedModel}
                      onChange={setSelectedModel}
                      size="small"
                      style={{ width: "100%" }}
                      options={[
                        { value: "deepseek-v4-flash", label: "Flash" },
                        { value: "deepseek-v4-pro", label: "Pro" },
                        { value: "deepseek-reasoner", label: "Reasoner" },
                      ]}
                    />
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, color: "#8c8c8c", marginBottom: 4 }}>场景</div>
                  <Select
                    value={selectedScenario || undefined}
                    onChange={handleScenarioChange}
                    allowClear
                    placeholder="可选"
                    size="small"
                    style={{ width: "100%" }}
                    options={scenarios.map((s) => ({ value: s.id, label: s.name }))}
                  />
                </div>
              </div>
            </section>

            <section style={{ flexShrink: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Prompt</div>
              <Input.TextArea
                value={promptTemplate}
                onChange={(e) => setPromptTemplate(e.target.value)}
                autoSize={{ minRows: 8, maxRows: 12 }}
                placeholder="留空使用默认模板"
              />
            </section>

            <section className="flow-selected-roles-section">
              <div className="flow-selected-roles-header">
                <div className="flow-section-title">已选角色</div>
                <Tag style={{ margin: 0 }}>{selectedRoles.length}</Tag>
              </div>
              <div className="flow-selected-roles-list">
                {selectedRoles.length === 0 ? (
                  <Empty description="从右侧选择角色" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ margin: "18px 0" }} />
                ) : selectedRoles.map((rid, idx) => {
                  const r = roleMetaByRoleId(rid);
                  return (
                    <div key={rid} className="flow-selected-role-row">
                      <span style={{ fontSize: 11, color: "#8c8c8c" }}>{idx + 1}</span>
                      <span className="flow-selected-role-name">
                        {roleZh(rid, r?.name, r?.description).name}
                      </span>
                      <span className="flow-role-actions">
                        <Button size="small" type="text" disabled={idx === 0}
                          onClick={() => moveRole(idx, -1)} style={{ height: 22, width: 22, padding: 0 }}>↑</Button>
                        <Button size="small" type="text" disabled={idx === selectedRoles.length - 1}
                          onClick={() => moveRole(idx, 1)} style={{ height: 22, width: 22, padding: 0 }}>↓</Button>
                        <Button size="small" type="text" danger icon={<DeleteOutlined />}
                          onClick={() => toggleRole(rid)} style={{ height: 22, width: 22, padding: 0 }} />
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="flow-collaboration-section">
              <div className="flow-collaboration-header">
                <div className="flow-section-title">协作约束</div>
                <Tag color={Object.keys(buildCollaborationSpec(selectedRoles, roleContracts, adjudication)).length > 0 ? "blue" : "default"} style={{ margin: 0 }}>
                  Flow Spec
                </Tag>
              </div>
              <Tabs
                className="flow-collaboration-tabs"
                size="small"
                defaultActiveKey="roles"
                items={[
                  {
                    key: "roles",
                    label: "角色立场",
                    children: selectedRoles.length === 0 ? (
                      <Empty description="先选择角色" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ margin: "12px 0" }} />
                    ) : (
                      <div className="flow-contract-form">
                        <Select
                          size="small"
                          value={activeContractRoleId || undefined}
                          onChange={setActiveContractRoleId}
                          style={{ width: "100%" }}
                          options={selectedRoles.map((rid, index) => {
                            const r = roleMetaByRoleId(rid);
                            return {
                              value: rid,
                              label: `${index + 1}. ${roleZh(rid, r?.name, r?.description).name}`,
                            };
                          })}
                        />
                        <div className="flow-contract-field">
                          <div className="flow-contract-field-label">立场名称</div>
                          <Input
                            size="small"
                            value={activeRoleContract.stance_name || ""}
                            onChange={(e) => updateActiveRoleContract("stance_name", e.target.value)}
                            placeholder="例如：风险审查方"
                          />
                        </div>
                        <div className="flow-contract-field">
                          <div className="flow-contract-field-label">目标</div>
                          <Input.TextArea
                            value={activeRoleContract.objective || ""}
                            onChange={(e) => updateActiveRoleContract("objective", e.target.value)}
                            autoSize={{ minRows: 1, maxRows: 2 }}
                            placeholder="该角色在本流程里的独立目标"
                          />
                        </div>
                        <div className="flow-contract-field">
                          <div className="flow-contract-field-label">必须捍卫</div>
                          <Input.TextArea
                            value={activeRoleContract.must_defend || ""}
                            onChange={(e) => updateActiveRoleContract("must_defend", e.target.value)}
                            autoSize={{ minRows: 1, maxRows: 2 }}
                            placeholder="必须坚持的判断标准或立场"
                          />
                        </div>
                        <div className="flow-contract-field">
                          <div className="flow-contract-field-label">必须挑战</div>
                          <Input.TextArea
                            value={activeRoleContract.must_challenge || ""}
                            onChange={(e) => updateActiveRoleContract("must_challenge", e.target.value)}
                            autoSize={{ minRows: 1, maxRows: 2 }}
                            placeholder="必须质疑的假设、方案或风险盲区"
                          />
                        </div>
                        <div className="flow-contract-two-col">
                          <div className="flow-contract-field">
                            <div className="flow-contract-field-label">证据标准</div>
                            <Input
                              size="small"
                              value={activeRoleContract.evidence_standard || ""}
                              onChange={(e) => updateActiveRoleContract("evidence_standard", e.target.value)}
                              placeholder="证据优先级"
                            />
                          </div>
                          <div className="flow-contract-field">
                            <div className="flow-contract-field-label">风险偏好</div>
                            <Input
                              size="small"
                              value={activeRoleContract.risk_bias || ""}
                              onChange={(e) => updateActiveRoleContract("risk_bias", e.target.value)}
                              placeholder="保守 / 激进"
                            />
                          </div>
                        </div>
                        <div className="flow-contract-field">
                          <div className="flow-contract-field-label">禁止重叠</div>
                          <Input
                            size="small"
                            value={activeRoleContract.forbidden_overlap || ""}
                            onChange={(e) => updateActiveRoleContract("forbidden_overlap", e.target.value)}
                            placeholder="不要重复承担的其他角色职责"
                          />
                        </div>
                        <div className="flow-contract-field">
                          <div className="flow-contract-field-label">输出章节</div>
                          <Input.TextArea
                            value={activeRoleContract.output_schema || ""}
                            onChange={(e) => updateActiveRoleContract("output_schema", e.target.value)}
                            autoSize={{ minRows: 2, maxRows: 3 }}
                            placeholder={"每行一个章节，例如：\n立场结论\n证据\n反方意见"}
                          />
                        </div>
                      </div>
                    ),
                  },
                  {
                    key: "adjudication",
                    label: "裁决规则",
                    children: (
                      <div className="flow-contract-form">
                        <div className="flow-contract-field">
                          <div className="flow-contract-field-label">决策规则</div>
                          <Input.TextArea
                            value={adjudication.decision_rule || ""}
                            onChange={(e) => updateAdjudication("decision_rule", e.target.value)}
                            autoSize={{ minRows: 2, maxRows: 3 }}
                            placeholder="例如：优先选择证据最强、迁移风险最低的方案"
                          />
                        </div>
                        <div className="flow-contract-field">
                          <div className="flow-contract-field-label">评分维度</div>
                          <Input.TextArea
                            value={adjudication.rubric || ""}
                            onChange={(e) => updateAdjudication("rubric", e.target.value)}
                            autoSize={{ minRows: 2, maxRows: 3 }}
                            placeholder={"每行一个维度，例如：\n证据质量\n用户价值\n实施风险"}
                          />
                        </div>
                        <div className="flow-contract-field">
                          <div className="flow-contract-field-label">必需输出章节</div>
                          <Input.TextArea
                            value={adjudication.required_output_sections || ""}
                            onChange={(e) => updateAdjudication("required_output_sections", e.target.value)}
                            autoSize={{ minRows: 2, maxRows: 3 }}
                            placeholder={"每行一个章节，例如：\n最终决策\n评分矩阵\n少数意见"}
                          />
                        </div>
                      </div>
                    ),
                  },
                ]}
              />
            </section>
          </aside>

          <main className="flow-composer-canvas" style={{ minWidth: 0, padding: 14, overflow: "hidden", display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, marginBottom: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                <span style={{ fontSize: 14, fontWeight: 800 }}>DAG 画布</span>
                <Tag color="blue" style={{ margin: 0 }}>{selectedRoles.length + dagExtraNodes.length} 节点</Tag>
                <Tag color="purple" style={{ margin: 0 }}>{dagEdges.length} 依赖</Tag>
              </div>
              {flowType !== "dag" && (
                <Button size="small" type="primary" ghost onClick={() => setFlowType("dag")}>
                  切换为 DAG
                </Button>
              )}
            </div>
            <Suspense fallback={<div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#8c8c8c" }}><Spin size="small" /></div>}>
              <SkillFlowCanvas
                roleIds={selectedRoles}
                extraNodes={dagExtraNodes}
                edges={dagEdges}
                onEdgesChange={setDagEdges}
                onExtraNodesChange={setDagExtraNodes}
                rolesById={canvasRolesById}
                height="100%"
              />
            </Suspense>
          </main>

          <aside className="flow-composer-panel flow-role-library" style={{
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
            padding: 14,
            borderLeft: "1px solid #e8e8e8",
            background: "#fff",
            overflow: "hidden",
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 10 }}>
              <div style={{ fontSize: 13, fontWeight: 700 }}>Skill / 角色</div>
              <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={() => setImportModalOpen(true)}>
                导入
              </Button>
            </div>

            <div style={{ display: "flex", gap: 4, marginBottom: 10, overflowX: "auto", paddingBottom: 2 }}>
              {displayedSkillTabs.map((t) => {
                const canDeleteTab = t.source_type !== "builtin" && t.id !== "software-engineering" && t.id !== MANAGED_SKILLS_TAB_ID;
                return (
                  <span
                    key={t.id}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      flexShrink: 0,
                      border: "1px solid #d9d9d9",
                      borderRadius: 6,
                      overflow: "hidden",
                      background: activeTab === t.id ? "#1677ff" : "#fff",
                    }}
                  >
                    <Button
                      size="small"
                      type={activeTab === t.id ? "primary" : "default"}
                      onClick={() => handleTabSwitch(t.id)}
                      style={{
                        fontSize: 12,
                        border: 0,
                        borderRadius: 0,
                        boxShadow: "none",
                        maxWidth: 120,
                      }}
                    >
                      <span style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {tabDisplayName(t)}
                      </span>
                    </Button>
                    {canDeleteTab && (
                      <Popconfirm
                        title="删除 Skill Tab"
                        description={`确认删除“${tabDisplayName(t)}”及其下属所有 Skill？`}
                        okText="删除"
                        cancelText="取消"
                        okButtonProps={{ danger: true, loading: deletingTabId === t.id }}
                        onConfirm={() => handleDeleteSkillTab(t)}
                      >
                        <Tooltip title="删除 Tab 及下属 Skill">
                          <Button
                            size="small"
                            type={activeTab === t.id ? "primary" : "text"}
                            danger
                            icon={<DeleteOutlined />}
                            loading={deletingTabId === t.id}
                            onClick={(e) => e.stopPropagation()}
                            style={{
                              width: 26,
                              border: 0,
                              borderRadius: 0,
                              boxShadow: "none",
                            }}
                          />
                        </Tooltip>
                      </Popconfirm>
                    )}
                  </span>
                );
              })}
            </div>

            <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
              <Input
                size="small"
                prefix={<SearchOutlined />}
                placeholder="搜索角色"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                allowClear
                style={{ flex: 1 }}
              />
              {activeTab === "software-engineering" && (
                <Select
                  size="small"
                  value={filterCategory}
                  onChange={setFilterCategory}
                  style={{ width: 96 }}
                  options={[
                    { value: "all", label: "全部" },
                    ...CATEGORY_ORDER.map((c) => ({ value: c, label: CATEGORY_LABELS[c] })),
                  ]}
                />
              )}
              {activeTab === MANAGED_SKILLS_TAB_ID && (
                <Button size="small" onClick={refreshManagedSkills}>
                  刷新
                </Button>
              )}
            </div>

            <div style={{ flex: 1, minHeight: 0, overflow: "auto", border: "1px solid #f0f0f0", borderRadius: 6, padding: 6 }}>
              {roleTreeData.length === 0 ? (
                <Empty
                  description={
                    activeTab === "software-engineering"
                      ? "无匹配角色"
                      : activeTab === MANAGED_SKILLS_TAB_ID
                        ? "暂无技能管理 Skill"
                        : "该 Tab 暂无角色"
                  }
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  style={{ marginTop: 80 }}
                />
              ) : (
                <Tree
                  checkable
                  defaultExpandAll
                  blockNode
                  treeData={roleTreeData}
                  checkedKeys={selectedRoles.filter((id) => visibleRoleIds.has(id))}
                  onCheck={handleRoleTreeCheck}
                />
              )}
            </div>
          </aside>
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
