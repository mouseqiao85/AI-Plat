import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { platformApi, type PlatformStatus } from '@/services/api'
import type {
  Ontology,
  Agent,
  MCPConnection,
  ModelAsset,
  DatasetAsset,
  DashboardMetrics,
  CodeGenerationRequest,
  CodeGenerationResponse,
} from '@/types'

export function usePlatformStatus() {
  return useQuery<PlatformStatus>({
    queryKey: ['platform', 'status'],
    queryFn: platformApi.getStatus,
    refetchInterval: 30000,
  })
}

export function useOntologies() {
  return useQuery<{ ontologies: Ontology[]; count: number }>({
    queryKey: ['ontologies'],
    queryFn: async () => {
      const response = await fetch('/api/ontology/list')
      return response.json()
    },
  })
}

export function useOntology(id: string) {
  return useQuery<Ontology>({
    queryKey: ['ontologies', id],
    queryFn: async () => {
      const response = await fetch(`/api/ontology/${id}`)
      return response.json()
    },
    enabled: !!id,
  })
}

export function useAgents() {
  return useQuery<{ agents: Agent[]; count: number }>({
    queryKey: ['agents'],
    queryFn: async () => {
      const response = await fetch('/api/agents/list')
      return response.json()
    },
  })
}

export function useAgent(id: string) {
  return useQuery<Agent>({
    queryKey: ['agents', id],
    queryFn: async () => {
      const response = await fetch(`/api/agents/${id}`)
      return response.json()
    },
    enabled: !!id,
  })
}

export function useStartAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (agentId: string) => {
      const response = await fetch(`/api/agents/${agentId}/start`, { method: 'POST' })
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

export function useStopAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (agentId: string) => {
      const response = await fetch(`/api/agents/${agentId}/stop`, { method: 'POST' })
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

export function useMCPConnections() {
  return useQuery<{ connections: MCPConnection[]; count: number }>({
    queryKey: ['mcp', 'connections'],
    queryFn: async () => {
      const response = await fetch('/api/mcp/connections')
      return response.json()
    },
  })
}

export function useMCPConnection(id: string) {
  return useQuery<MCPConnection>({
    queryKey: ['mcp', 'connections', id],
    queryFn: async () => {
      const response = await fetch(`/api/mcp/connections/${id}`)
      return response.json()
    },
    enabled: !!id,
  })
}

export function useTestMCPConnection() {
  return useMutation({
    mutationFn: async (connectionId: string) => {
      const response = await fetch(`/api/mcp/connections/${connectionId}/test`, { method: 'POST' })
      return response.json()
    },
  })
}

export function useModels() {
  return useQuery<{ models: ModelAsset[]; count: number }>({
    queryKey: ['assets', 'models'],
    queryFn: async () => {
      const response = await fetch('/api/assets/models')
      return response.json()
    },
  })
}

export function useDatasets() {
  return useQuery<{ datasets: DatasetAsset[]; count: number }>({
    queryKey: ['assets', 'datasets'],
    queryFn: async () => {
      const response = await fetch('/api/assets/datasets')
      return response.json()
    },
  })
}

export function useDashboardMetrics() {
  return useQuery<DashboardMetrics>({
    queryKey: ['dashboard', 'metrics'],
    queryFn: async () => {
      const response = await fetch('/api/metrics/dashboard')
      return response.json()
    },
    refetchInterval: 60000,
  })
}

export function useWorkflows() {
  return useQuery({
    queryKey: ['workflows'],
    queryFn: async () => {
      const response = await fetch('/api/workflows')
      return response.json()
    },
  })
}

export function useRecentTasks(limit: number = 10) {
  return useQuery({
    queryKey: ['tasks', 'recent', limit],
    queryFn: async () => {
      const response = await fetch(`/api/tasks/recent?limit=${limit}`)
      return response.json()
    },
  })
}

export function useGenerateCode() {
  return useMutation<CodeGenerationResponse, Error, CodeGenerationRequest>({
    mutationFn: async (request: CodeGenerationRequest) => {
      const params = new URLSearchParams({
        prompt: request.prompt,
        ...(request.context && { context: request.context }),
        ...(request.language && { language: request.language }),
      })
      const response = await fetch(`/api/vibecoding/generate?${params}`, { method: 'POST' })
      return response.json()
    },
  })
}

export function useAnalyzeCode() {
  return useMutation({
    mutationFn: async (code: string) => {
      const params = new URLSearchParams({ code })
      const response = await fetch(`/api/vibecoding/analyze?${params}`, { method: 'POST' })
      return response.json()
    },
  })
}
