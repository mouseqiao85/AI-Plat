export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  cards?: CardData[];
  fileDownloads?: FileDownloadInfo[];
  plan?: PlanData;
  workers?: WorkerInfo[];
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

export interface LlmProvider {
  id: string;
  name: string;
  base_url: string;
  api_key: string;
  custom_header?: string;
  models: string[];
}

