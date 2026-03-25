export interface Ontology {
  id: string
  name: string
  entities: number
  relations: number
  status: 'active' | 'inactive'
  description?: string
  created_at?: string
}

export interface Agent {
  id: string
  name: string
  status: 'running' | 'stopped' | 'error'
  skills: number
  processed: number
  cpu: number
  memory: number
  description?: string
}

export interface Task {
  id: string
  name: string
  description?: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  agent_id: string
  skill_id: string
  priority: number
  created_at: string
  completed_at?: string
}

export interface MCPConnection {
  id: string
  name: string
  status: 'healthy' | 'warning' | 'error'
  responseTime: number
  calls: number
  endpoint: string
  availability: number
}

export interface ModelAsset {
  id: string
  name: string
  rating: number
  calls: string
  category: 'pretrained' | 'fine_tuned' | 'custom'
  framework: string
  description?: string
}

export interface DatasetAsset {
  id: string
  name: string
  size: string
  type: string
  format: string
  records: number
  description?: string
}

export interface Workflow {
  id: string
  name: string
  status: 'created' | 'running' | 'completed' | 'failed'
  tasks: number
  description?: string
}

export interface PlatformStatus {
  platform_id: string
  version: string
  status: string
  uptime: number
  modules: {
    ontology: { status: string; count: number }
    agents: { status: string; count: number }
    vibecoding: { status: string; notebooks: number }
    mcp: { status: string; connections: number }
    assets: { models: number; datasets: number }
  }
  metrics: {
    total_tasks_completed: number
    active_workflows: number
    api_calls_today: number
    avg_response_time_ms: number
  }
}

export interface DashboardMetrics {
  roi: {
    current: number
    change: number
    trend: number[]
  }
  tasks: {
    completed: number
    pending: number
    running: number
    success_rate: number
  }
  agents: {
    total: number
    running: number
    stopped: number
  }
  api_calls: {
    today: number
    week: number
    month: number
  }
  performance: {
    avg_response_time_ms: number
    p99_response_time_ms: number
    error_rate: number
  }
}

export interface ApiResponse<T> {
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface CodeGenerationRequest {
  prompt: string
  context?: string
  language?: string
}

export interface CodeGenerationResponse {
  generated_code: string
  language: string
  tokens_used: number
  generated_at: string
}

export interface CodeAnalysisResponse {
  functions: string[]
  classes: string[]
  imports: string[]
  lines_of_code: number
  complexity: string
  suggestions: string[]
}
