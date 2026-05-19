export interface ToolCallEntry {
  tool_name: string;
  tool_args?: Record<string, unknown>;
  result?: unknown;
  success?: boolean;
  started_at: number;
  completed_at?: number;
  status: "running" | "completed" | "failed";
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  cards?: CardData[];
  fileDownloads?: FileDownloadInfo[];
  plan?: PlanData;
  workers?: WorkerInfo[];
  toolCalls?: ToolCallEntry[];
  timestamp: number;
}

export interface CardData {
  type: string;
  data: Record<string, unknown>;
}

export interface FileDownloadInfo {
  file_id: string;
  filename: string;
  content_type: string;
  size: number;
  download_url: string;
}

export interface SkillTool {
  name: string;
  description: string;
}

export interface Skill {
  name: string;
  version: string;
  description: string;
  author: string;
  license: string;
  keywords: string[];
  dependencies: string[];
  tools: SkillTool[];
  requires_config: string[];
  optional_config: string[];
  enabled: boolean;
  config_ok: boolean;
  path: string;
}

export interface SkillGithubImportResult {
  success: boolean;
  scanned: number;
  imported: number;
  skills: Skill[];
  errors: string[];
}

export interface User {
  id: number;
  nickname: string;
  membership_tier: string;
  role?: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  id: number;
  role: "user" | "assistant";
  content: string | null;
  file_downloads?: FileDownloadInfo[];
  created_at: string;
}

export interface UserProfile {
  user_id: number;
  preferences: {
    language_style: string;
    verbosity: string;
    preferred_formats: string[];
    response_language: string;
  };
  key_facts: {
    profession: string;
    interests: string[];
    domain_knowledge: string[];
    mentioned_projects: string[];
  };
  interaction_stats: {
    total_sessions: number;
    total_messages: number;
    avg_session_length: number;
    last_active: string;
    tools_used: string[];
  };
  profile_summary: string;
  version: number;
  updated_at: string;
}

export interface PlanStep {
  step: number;
  action: string;
  description: string;
  status: "pending" | "running" | "completed" | "failed";
  result?: unknown;
  error?: string;
}

export interface PlanData {
  plan_id: string;
  steps: PlanStep[];
  needs_workers?: boolean;
}

export interface WorkerInfo {
  worker_id: string;
  task: string;
  status: "running" | "completed" | "failed";
  result_preview?: string;
}

export interface SkillNoticeData {
  skill: string;
  tools: string[];
  requires: string[];
  optional: string[];
  dependencies: string[];
  missing: string[];
  config_ok: boolean;
}

export interface MarketAgent {
  id: number;
  user_id: number;
  title: string;
  description: string;
  icon: string;
  tags: string;
  author: string;
  usage_count: number;
  category: string;
  featured: boolean;
  created_at: string;
  updated_at: string;
}

export interface LlmProvider {
  id: string;
  name: string;
  base_url: string;
  api_key: string;
  custom_header?: string;
  models: string[];
}

// ── Multi-agent orchestrator (hermes-bridge /api/v2) ────────────────────────

export interface ExpertRole {
  id: string;
  name: string;
  category: string;
  description: string;
  version: string;
  source: string;
  skill_md_path: string;
  allowed_tools: string[];
  triggers: string[];
  hermes_installed: boolean;
  install_error?: string | null;
  loaded_at: number;
}

export interface ToolScenario {
  id: string;
  name: string;
  description: string;
  tools: string[];
  recommended_roles: string[];
}

export type FlowType = "sequential" | "parallel";

export interface DialogFlow {
  id: number;
  owner_id: number;
  name: string;
  description: string;
  flow_type: FlowType;
  role_ids: string[];
  scenario_id: string;
  prompt_template: string;
  model: string;
  created_at: string;
  updated_at: string;
}

export interface FlowRunOutput {
  role_id: string;
  content: string;
  latency_ms: number;
  error?: string | null;
}

export interface FlowRun {
  id: number;
  flow_id: number;
  input_text: string;
  status: "pending" | "running" | "succeeded" | "failed" | "cancelled";
  error: string;
  outputs: FlowRunOutput[];
  started_at: string;
  finished_at: string | null;
  project_dir: string;
}

export type RunEvent =
  | { type: "run_started"; run_id: number; flow_id: number; flow_type: FlowType; role_ids: string[]; total: number; project_dir?: string }
  | { type: "role_started"; run_id: number; role_id: string; index: number; total: number }
  | { type: "role_output"; run_id: number; role_id: string; content: string; index: number; total: number }
  | { type: "role_completed"; run_id: number; role_id: string; content: string; latency_ms: number; index: number; total: number }
  | { type: "role_failed"; run_id: number; role_id: string; error: string; latency_ms: number; index: number; total: number }
  | { type: "run_completed"; run_id: number }
  | { type: "run_failed"; run_id: number; error: string }
  | { type: "error"; error: string };

// ── Skill Tabs ────────────────────────────────────────────────────────────────

export interface SkillTab {
  id: string;
  name: string;
  description: string;
  source_type: "builtin" | "github";
  source_url: string;
  branch: string;
  sub_path: string;
  imported_at: string;
  updated_at: string;
  role_count: number;
  icon: string;
  tab_order: number;
}

export interface TabRole {
  id: string;
  tab_id: string;
  role_id: string;
  display_name: string;
  category: string;
  classification: "planning" | "implementation" | "";
  description: string;
  capabilities: string[];
  recommended_tools: string[];
  skill_md_path: string;
  created_at: string;
}

export interface TabScenario {
  id: string;
  tab_id: string;
  name: string;
  description: string;
  tools: string[];
  recommended_roles: string[];
  generated_by: string;
  created_at: string;
}

export interface TabImportResult {
  success: boolean;
  scanned: number;
  imported: number;
  scenarios_generated: number;
  roles: TabRole[];
  scenarios: TabScenario[];
}
