import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export interface Dataset {
  id: string
  name: string
  description?: string
  data_type: string
  format: string
  status: 'draft' | 'ready' | 'processing' | 'error'
  file_path?: string
  file_size?: number
  record_count?: number
  schema?: Record<string, any>
  statistics?: Record<string, any>
  version: string
  tags: string[]
  owner_id?: string
  is_public: boolean
  created_at: string
  updated_at: string
}

export interface Model {
  id: string
  name: string
  description?: string
  model_type: string
  framework: string
  status: 'draft' | 'training' | 'ready' | 'deployed' | 'error'
  version: string
  file_path?: string
  file_size?: number
  dataset_id?: string
  hyperparameters?: Record<string, any>
  metrics?: Record<string, any>
  training_config?: Record<string, any>
  deployment_config?: Record<string, any>
  endpoint_url?: string
  owner_id?: string
  is_public: boolean
  tags: string[]
  created_at: string
  updated_at: string
}

export interface Experiment {
  id: string
  name: string
  description?: string
  status: 'active' | 'completed' | 'archived'
  artifact_location?: string
  lifecycle_stage: string
  created_at: string
  updated_at: string
  runs?: Run[]
}

export interface Run {
  id: string
  experiment_id: string
  name: string
  status: 'running' | 'completed' | 'failed' | 'killed'
  start_time: string
  end_time?: string
  metrics: Record<string, number>
  params: Record<string, any>
  artifacts: string[]
  duration_ms?: number
}

export const datasetApi = {
  list: async (params?: { skip?: number; limit?: number }): Promise<Dataset[]> => {
    const response = await api.get('/datasets', { params })
    return response.data
  },
  
  get: async (id: string): Promise<Dataset> => {
    const response = await api.get(`/datasets/${id}`)
    return response.data
  },
  
  create: async (data: Partial<Dataset>): Promise<Dataset> => {
    const response = await api.post('/datasets', data)
    return response.data
  },
  
  update: async (id: string, data: Partial<Dataset>): Promise<Dataset> => {
    const response = await api.put(`/datasets/${id}`, data)
    return response.data
  },
  
  delete: async (id: string): Promise<void> => {
    await api.delete(`/datasets/${id}`)
  },
  
  upload: async (file: File, metadata?: Partial<Dataset>): Promise<Dataset> => {
    const formData = new FormData()
    formData.append('file', file)
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata))
    }
    const response = await api.post('/datasets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },
  
  preview: async (id: string, limit?: number): Promise<any[]> => {
    const response = await api.get(`/datasets/${id}/preview`, { params: { limit } })
    return response.data
  },
  
  getStatistics: async (id: string): Promise<Record<string, any>> => {
    const response = await api.get(`/datasets/${id}/statistics`)
    return response.data
  }
}

export const modelApi = {
  list: async (params?: { skip?: number; limit?: number }): Promise<Model[]> => {
    const response = await api.get('/models', { params })
    return response.data
  },
  
  get: async (id: string): Promise<Model> => {
    const response = await api.get(`/models/${id}`)
    return response.data
  },
  
  create: async (data: Partial<Model>): Promise<Model> => {
    const response = await api.post('/models', data)
    return response.data
  },
  
  update: async (id: string, data: Partial<Model>): Promise<Model> => {
    const response = await api.put(`/models/${id}`, data)
    return response.data
  },
  
  delete: async (id: string): Promise<void> => {
    await api.delete(`/models/${id}`)
  },
  
  deploy: async (id: string, config?: Record<string, any>): Promise<Model> => {
    const response = await api.post(`/models/${id}/deploy`, config)
    return response.data
  },
  
  undeploy: async (id: string): Promise<Model> => {
    const response = await api.post(`/models/${id}/undeploy`)
    return response.data
  },
  
  predict: async (id: string, input: any): Promise<any> => {
    const response = await api.post(`/models/${id}/predict`, { input })
    return response.data
  },
  
  getVersions: async (name: string): Promise<any[]> => {
    const response = await api.get(`/models/${name}/versions`)
    return response.data
  }
}

export const experimentApi = {
  list: async (): Promise<Experiment[]> => {
    const response = await api.get('/mlops/experiments')
    return response.data
  },
  
  get: async (id: string): Promise<Experiment> => {
    const response = await api.get(`/mlops/experiments/${id}`)
    return response.data
  },
  
  create: async (data: { name: string; description?: string }): Promise<Experiment> => {
    const response = await api.post('/mlops/experiments', data)
    return response.data
  },
  
  delete: async (id: string): Promise<void> => {
    await api.delete(`/mlops/experiments/${id}`)
  }
}

export const runApi = {
  list: async (experimentId?: string): Promise<Run[]> => {
    const response = await api.get('/mlops/runs', { params: { experiment_id: experimentId } })
    return response.data
  },
  
  get: async (id: string): Promise<Run> => {
    const response = await api.get(`/mlops/runs/${id}`)
    return response.data
  },
  
  start: async (experimentId: string, name: string): Promise<Run> => {
    const response = await api.post('/mlops/runs', { experiment_id: experimentId, name })
    return response.data
  },
  
  end: async (id: string, status?: string): Promise<Run> => {
    const response = await api.post(`/mlops/runs/${id}/end`, { status })
    return response.data
  },
  
  logMetric: async (runId: string, key: string, value: number): Promise<void> => {
    await api.post('/mlops/metrics', { run_id: runId, key, value })
  },
  
  logParam: async (runId: string, key: string, value: any): Promise<void> => {
    await api.post('/mlops/params', { run_id: runId, key, value })
  }
}

export default api
