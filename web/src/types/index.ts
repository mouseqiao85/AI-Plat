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
  function?: string;
  icon: string;
  access_url?: string;
  knowledge_url?: string;
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

// ── Knowledge Graph / GraphRAG (Python agent /api/v1) ───────────────────────

export interface KnowledgeGraphStats {
  sources: number;
  nodes: number;
  edges: number;
  notes: number;
  tags: number;
  entities: number;
  folders?: number;
  last_import_at?: string | null;
}

export interface KnowledgeSource {
  id: number;
  source_type: string;
  name: string;
  source_uri?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSourceDeleteResult {
  source_id: number;
  deleted: boolean;
  nodes: number;
  edges: number;
  import_jobs: number;
}

export interface KnowledgeImportJob {
  id: number;
  source_id: number;
  status: string;
  filename: string;
  stats: Record<string, unknown>;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface KnowledgeNode {
  id: number;
  source_id: number;
  node_type: "note" | "tag" | "entity" | "folder" | string;
  key: string;
  title: string;
  content_preview?: string | null;
  path?: string | null;
  uri?: string | null;
  properties: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeEdge {
  id: number;
  source_id: number;
  from_node_id: number;
  to_node_id: number;
  edge_type: string;
  weight: number;
  properties: Record<string, unknown>;
  created_at: string;
}

export interface KnowledgeNeighbors {
  center: KnowledgeNode;
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

export interface KnowledgeSubgraph {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

export interface GraphRAGContext {
  node: {
    id: number;
    type: string;
    title: string;
    key?: string;
    path?: string | null;
    uri?: string | null;
    preview?: string | null;
    content_excerpt?: string | null;
    properties?: Record<string, unknown>;
  };
  chunks?: Array<{
    id?: number;
    heading?: string;
    content?: string;
    path?: string | null;
    uri?: string | null;
  }>;
  neighbors: Array<{
    id: number;
    type: string;
    title: string;
    key?: string;
    path?: string | null;
    preview?: string | null;
  }>;
  relations: Array<{
    type: string;
    from: string;
    to: string;
    properties?: Record<string, unknown>;
  }>;
}

export interface GraphRAGQueryResult {
  query: string;
  contexts: GraphRAGContext[];
}

export interface GraphRAGAnswerResult {
  query: string;
  answer: string;
  contexts: GraphRAGContext[];
}

export interface KnowledgeImportResult {
  job_id: number;
  source_id: number;
  status: string;
  stats: {
    notes: number;
    tags: number;
    entities: number;
    folders?: number;
    relations: number;
    skipped: number;
    errors: number;
  };
  errors: Array<Record<string, unknown>>;
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

export type FlowType = "sequential" | "parallel" | "hierarchical" | "competitive" | "pipeline" | "peer_to_peer" | "dag";

export interface DagFlowNode {
  id: string;
  type?: "role" | "graphrag";
  role_id: string;
  label?: string;
  prompt_template?: string;
  query_template?: string;
  max_hits?: number;
}

export interface DagFlowEdge {
  from: string;
  to: string;
}

export interface DagFlowSpec {
  nodes: DagFlowNode[];
  edges: DagFlowEdge[];
}

export type SandboxSecurityLevel = "local_dev" | "standard" | "high";

export interface SandboxPolicy {
  security_level: SandboxSecurityLevel;
  resources: {
    cpu_seconds?: number | null;
    memory_mb?: number | null;
    disk_mb?: number | null;
  };
  network: {
    allow_all: boolean;
    allowed_domains: string[];
    denied_ips: string[];
  };
  filesystem: {
    mode: "workspace" | "read_only" | "none";
    read_paths: string[];
    write_paths: string[];
  };
}

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
  sandbox_policy: SandboxPolicy;
  flow_spec?: Record<string, unknown>;
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

export type CollaborationMessageStatus = "queued" | "sent" | "received" | "failed" | "timed_out";

export interface CollaborationMessage {
  id: number | null;
  run_id: number;
  seq: number | null;
  from_agent: string;
  to_agent: string;
  type: string;
  payload: Record<string, unknown>;
  priority?: number;
  timeout_ms?: number | null;
  status: CollaborationMessageStatus;
  role_id?: string | null;
  output_index?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

type RunEventSeq = { seq?: number };

export type RunEvent =
  | ({ type: "run_started"; run_id: number; flow_id: number; flow_type: FlowType; role_ids: string[]; total: number; project_dir?: string; dag_nodes?: DagFlowNode[] } & RunEventSeq)
  | ({ type: "role_started"; run_id: number; role_id: string; index: number; total: number; node_id?: string } & RunEventSeq)
  | ({ type: "role_output"; run_id: number; role_id: string; content: string; index: number; total: number; node_id?: string } & RunEventSeq)
  | ({ type: "role_completed"; run_id: number; role_id: string; content: string; latency_ms: number; index: number; total: number; node_id?: string } & RunEventSeq)
  | ({ type: "role_failed"; run_id: number; role_id: string; error: string; latency_ms: number; index: number; total: number; node_id?: string } & RunEventSeq)
  | ({ type: "conflict_resolved"; run_id: number; role_id: string; content: string; latency_ms?: number; index?: number; total?: number; strategy?: string; winner?: string; votes?: Record<string, number> } & RunEventSeq)
  | ({ type: "run_completed"; run_id: number } & RunEventSeq)
  | ({ type: "run_failed"; run_id: number; error: string } & RunEventSeq)
  | ({ type: "run_cancelled"; run_id: number; error?: string } & RunEventSeq)
  | ({ type: "error"; error: string } & RunEventSeq);

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
