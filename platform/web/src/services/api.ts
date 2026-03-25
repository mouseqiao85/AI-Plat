import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface PlatformStatus {
  platform_id: string
  is_running: boolean
  start_time: string
  uptime: number
  modules: {
    ontology: { initialized: boolean; triples_count: number }
    agents: { initialized: boolean; registered_agents: number; active_workflows: number }
    vibecoding: { initialized: boolean; notebooks_count: number }
    mcp: { server_initialized: boolean; clients_count: number; adapters_count: number }
  }
}

export interface ModelAsset {
  id: string
  name: string
  description: string
  model_type: string
  framework: string
  version: string
}

export interface DataAsset {
  id: string
  name: string
  description: string
  data_type: string
  format: string
  size: number
}

export const platformApi = {
  getStatus: async (): Promise<PlatformStatus> => {
    const response = await api.get('/status')
    return response.data
  },

  healthCheck: async () => {
    const response = await api.get('/health')
    return response.data
  },
}

export const ontologyApi = {
  getStatus: async () => {
    const response = await api.get('/ontology/status')
    return response.data
  },

  getEntities: async (entityType?: string) => {
    const response = await api.get('/ontology/entities', { params: { type: entityType } })
    return response.data
  },
}

export const agentsApi = {
  getStatus: async () => {
    const response = await api.get('/agents/status')
    return response.data
  },

  getAgents: async () => {
    const response = await api.get('/agents')
    return response.data
  },
}

export const vibecodingApi = {
  getStatus: async () => {
    const response = await api.get('/vibecoding/status')
    return response.data
  },

  generateCode: async (prompt: string, context?: string) => {
    const response = await api.post('/vibecoding/generate', { prompt, context })
    return response.data
  },
}

export const mcpApi = {
  getStatus: async () => {
    const response = await api.get('/mcp/status')
    return response.data
  },

  getConnections: async () => {
    const response = await api.get('/mcp/connections')
    return response.data
  },
}

export const assetsApi = {
  getModels: async () => {
    const response = await api.get('/assets/models')
    return response.data
  },

  getDataAssets: async () => {
    const response = await api.get('/assets/data')
    return response.data
  },
}

export default api
