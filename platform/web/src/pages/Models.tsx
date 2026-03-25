import { useState, useEffect } from 'react'
import { 
  Brain, Plus, Search, Trash2, Copy, Download,
  Rocket, Settings, HardDrive, GitBranch,
  Square, ExternalLink, X, Globe, Key, Link2, Sparkles, Zap
} from 'lucide-react'

interface Model {
  id: string
  name: string
  description: string
  model_type: string
  framework: string
  source: 'local' | 'huggingface' | 'external_api'
  status: 'draft' | 'ready' | 'deployed' | 'error'
  version: string
  file_size?: number
  endpoint_url?: string
  api_key?: string
  hf_model_id?: string
  external_api_url?: string
  metrics?: Record<string, number>
  tags: string[]
  created_at: string
}

type ModelStatus = 'draft' | 'ready' | 'deployed' | 'error'
type CreateType = 'local' | 'huggingface' | 'external_api'

const statusColors: Record<ModelStatus, string> = {
  draft: 'bg-gray-100 text-gray-800',
  ready: 'bg-green-100 text-green-800',
  deployed: 'bg-purple-100 text-purple-800',
  error: 'bg-red-100 text-red-800',
}

const sourceLabels: Record<string, { label: string; color: string }> = {
  local: { label: '本地模型', color: 'bg-blue-100 text-blue-700' },
  huggingface: { label: 'HuggingFace', color: 'bg-yellow-100 text-yellow-700' },
  external_api: { label: '外部API', color: 'bg-green-100 text-green-700' },
}

const frameworkIcons: Record<string, string> = {
  pytorch: '🔥',
  tensorflow: '🧠',
  sklearn: '📊',
  xgboost: '⚡',
  openai: '🤖',
  anthropic: '🔮',
  huggingface: '🤗',
  custom: '⚙️',
}

const popularHFModels = [
  { id: 'bert-base-uncased', name: 'BERT Base', downloads: '50M+', task: 'NLP' },
  { id: 'gpt2', name: 'GPT-2', downloads: '30M+', task: 'Text Generation' },
  { id: 'llama-2-7b-hf', name: 'LLaMA 2 7B', downloads: '20M+', task: 'LLM' },
  { id: 'stable-diffusion-xl-base-1.0', name: 'SDXL Base', downloads: '15M+', task: 'Image' },
  { id: 'whisper-large-v3', name: 'Whisper V3', downloads: '25M+', task: 'Audio' },
  { id: 'sentence-transformers/all-MiniLM-L6-v2', name: 'MiniLM', downloads: '40M+', task: 'Embedding' },
]

export default function Models() {
  const [models, setModels] = useState<Model[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterFramework, setFilterFramework] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterSource, setFilterSource] = useState('')
  const [selectedModel, setSelectedModel] = useState<Model | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createType, setCreateType] = useState<CreateType>('local')
  const [showDeployModal, setShowDeployModal] = useState(false)
  const [deployModelId, setDeployModelId] = useState<string | null>(null)
  const [showTestModal, setShowTestModal] = useState(false)
  const [testModel, setTestModel] = useState<Model | null>(null)

  useEffect(() => {
    fetchModels()
  }, [])

  const fetchModels = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/models')
      if (res.ok) {
        const data = await res.json()
        setModels(data.models || data || getMockModels())
      } else {
        setModels(getMockModels())
      }
    } catch (error) {
      console.error('Failed to fetch models:', error)
      setModels(getMockModels())
    }
    setLoading(false)
  }

  const getMockModels = (): Model[] => [
    { id: '1', name: 'GPT-4 Turbo', description: 'OpenAI GPT-4 Turbo模型', model_type: 'LLM', framework: 'openai', source: 'external_api', status: 'deployed', version: '1.0', endpoint_url: 'https://api.openai.com/v1/chat/completions', tags: ['NLP', '对话', '推理'], created_at: '2024-01-15' },
    { id: '2', name: 'Claude-3 Opus', description: 'Anthropic Claude-3模型', model_type: 'LLM', framework: 'anthropic', source: 'external_api', status: 'ready', version: '1.0', endpoint_url: 'https://api.anthropic.com/v1/messages', tags: ['NLP', '对话'], created_at: '2024-02-20' },
    { id: '3', name: 'BERT-Base-Chinese', description: '中文BERT预训练模型', model_type: 'NLP', framework: 'huggingface', source: 'huggingface', status: 'deployed', version: '1.0', hf_model_id: 'bert-base-chinese', tags: ['NLP', '中文', '预训练'], created_at: '2024-03-01' },
    { id: '4', name: 'LLaMA-2-7B', description: 'Meta LLaMA 2 7B模型', model_type: 'LLM', framework: 'pytorch', source: 'huggingface', status: 'ready', version: '1.0', hf_model_id: 'meta-llama/Llama-2-7b-hf', file_size: 13480787456, tags: ['LLM', '开源'], created_at: '2024-03-10' },
    { id: '5', name: '图像分类ResNet50', description: 'ResNet50图像分类模型', model_type: 'CV', framework: 'pytorch', source: 'local', status: 'deployed', version: '2.1', file_size: 102000000, endpoint_url: 'http://localhost:8001/predict', tags: ['CV', '分类'], created_at: '2024-02-01' },
    { id: '6', name: '通义千问', description: '阿里通义千问API', model_type: 'LLM', framework: 'custom', source: 'external_api', status: 'ready', version: '1.0', endpoint_url: 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation', tags: ['NLP', '中文', 'LLM'], created_at: '2024-03-05' },
  ]

  const filteredModels = models.filter((model) => {
    const matchesSearch = model.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      model.description?.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFramework = !filterFramework || model.framework === filterFramework
    const matchesStatus = !filterStatus || model.status === filterStatus
    const matchesSource = !filterSource || model.source === filterSource
    return matchesSearch && matchesFramework && matchesStatus && matchesSource
  })

  const formatBytes = (bytes?: number) => {
    if (!bytes) return '-'
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`
  }

  const handleCreateModel = async (data: Partial<Model>) => {
    const newModel: Model = {
      id: Date.now().toString(),
      name: data.name || '',
      description: data.description || '',
      model_type: data.model_type || 'custom',
      framework: data.framework || 'custom',
      source: data.source || 'local',
      status: 'draft',
      version: '1.0',
      tags: data.tags || [],
      created_at: new Date().toISOString(),
      ...data,
    }
    setModels([...models, newModel])
    setShowCreateModal(false)
  }

  const handleDeploy = async (modelId: string, _config: Record<string, any>) => {
    setModels(models.map(m => 
      m.id === modelId 
        ? { ...m, status: 'deployed' as const, endpoint_url: `http://localhost:8001/models/${modelId}/predict` }
        : m
    ))
    setShowDeployModal(false)
    setDeployModelId(null)
  }

  const handleUndeploy = async (modelId: string) => {
    setModels(models.map(m => 
      m.id === modelId ? { ...m, status: 'ready' as const } : m
    ))
  }

  const handleDelete = async (modelId: string) => {
    if (!confirm('确定要删除此模型吗？')) return
    setModels(models.filter(m => m.id !== modelId))
    setSelectedModel(null)
  }

  const handleTestModel = (model: Model) => {
    setTestModel(model)
    setShowTestModal(true)
  }

  const stats = {
    total: models.length,
    deployed: models.filter(m => m.status === 'deployed').length,
    ready: models.filter(m => m.status === 'ready').length,
    hf: models.filter(m => m.source === 'huggingface').length,
    external: models.filter(m => m.source === 'external_api').length,
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">模型管理</h1>
          <p className="text-gray-600 mt-1">管理本地模型、HuggingFace模型和外部API服务</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchModels}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
          >
            刷新
          </button>
          <button
            onClick={() => { setCreateType('local'); setShowCreateModal(true) }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus size={20} />
            新建模型
          </button>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
              <Brain className="text-gray-600" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
              <p className="text-sm text-gray-500">总模型</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Rocket className="text-green-600" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.deployed}</p>
              <p className="text-sm text-gray-500">已部署</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Settings className="text-blue-600" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.ready}</p>
              <p className="text-sm text-gray-500">待部署</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              <Sparkles className="text-yellow-600" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.hf}</p>
              <p className="text-sm text-gray-500">HuggingFace</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <Globe className="text-purple-600" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.external}</p>
              <p className="text-sm text-gray-500">外部API</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex gap-4">
        <button
          onClick={() => { setCreateType('huggingface'); setShowCreateModal(true) }}
          className="flex items-center gap-2 px-4 py-2 bg-yellow-100 text-yellow-800 rounded-lg hover:bg-yellow-200"
        >
          <Download size={18} />
          从HuggingFace导入
        </button>
        <button
          onClick={() => { setCreateType('external_api'); setShowCreateModal(true) }}
          className="flex items-center gap-2 px-4 py-2 bg-green-100 text-green-800 rounded-lg hover:bg-green-200"
        >
          <Link2 size={18} />
          配置外部API
        </button>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="搜索模型..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <select
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">所有来源</option>
            <option value="local">本地模型</option>
            <option value="huggingface">HuggingFace</option>
            <option value="external_api">外部API</option>
          </select>
          <select
            value={filterFramework}
            onChange={(e) => setFilterFramework(e.target.value)}
            className="px-4 py-2 border rounded-lg"
          >
            <option value="">所有框架</option>
            <option value="pytorch">PyTorch</option>
            <option value="tensorflow">TensorFlow</option>
            <option value="huggingface">HuggingFace</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="custom">自定义</option>
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 border rounded-lg"
          >
            <option value="">所有状态</option>
            <option value="draft">草稿</option>
            <option value="ready">就绪</option>
            <option value="deployed">已部署</option>
            <option value="error">错误</option>
          </select>
        </div>

        {loading ? (
          <div className="p-8 text-center text-gray-500">加载中...</div>
        ) : filteredModels.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Brain className="mx-auto mb-4 text-gray-300" size={48} />
            <p>没有找到模型</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
            {filteredModels.map((model) => (
              <div
                key={model.id}
                className="border rounded-lg p-4 hover:shadow-md cursor-pointer transition-shadow bg-white"
                onClick={() => setSelectedModel(model)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center text-xl">
                      {frameworkIcons[model.framework] || '📦'}
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{model.name}</h3>
                      <p className="text-xs text-gray-500">{model.framework} · {model.model_type}</p>
                    </div>
                  </div>
                  <div className="flex flex-col gap-1 items-end">
                    <span className={`px-2 py-0.5 text-xs rounded-full ${statusColors[model.status as ModelStatus]}`}>
                      {model.status}
                    </span>
                    <span className={`px-2 py-0.5 text-xs rounded-full ${sourceLabels[model.source]?.color}`}>
                      {sourceLabels[model.source]?.label}
                    </span>
                  </div>
                </div>
                
                <p className="text-sm text-gray-500 mb-3 line-clamp-2">
                  {model.description || '暂无描述'}
                </p>

                {model.source === 'huggingface' && model.hf_model_id && (
                  <div className="text-xs text-gray-400 mb-2 flex items-center gap-1">
                    <Sparkles size={12} />
                    <span className="font-mono">{model.hf_model_id}</span>
                  </div>
                )}

                {model.source === 'external_api' && model.endpoint_url && (
                  <div className="text-xs text-gray-400 mb-2 flex items-center gap-1">
                    <Globe size={12} />
                    <span className="truncate max-w-[200px]">{model.endpoint_url}</span>
                  </div>
                )}

                <div className="flex flex-wrap gap-1 mb-3">
                  {model.tags.slice(0, 3).map((tag, i) => (
                    <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">{tag}</span>
                  ))}
                </div>

                <div className="flex items-center justify-between text-xs text-gray-400 border-t pt-3">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1">
                      <GitBranch size={12} />
                      v{model.version}
                    </span>
                    {model.file_size && (
                      <span className="flex items-center gap-1">
                        <HardDrive size={12} />
                        {formatBytes(model.file_size)}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleTestModel(model) }}
                      className="p-1.5 text-green-600 hover:bg-green-50 rounded"
                      title="测试"
                    >
                      <Zap size={14} />
                    </button>
                    {model.status === 'ready' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeployModelId(model.id); setShowDeployModal(true) }}
                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                        title="部署"
                      >
                        <Rocket size={14} />
                      </button>
                    )}
                    {model.status === 'deployed' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleUndeploy(model.id) }}
                        className="p-1.5 text-yellow-600 hover:bg-yellow-50 rounded"
                        title="取消部署"
                      >
                        <Square size={14} />
                      </button>
                    )}
                    {model.endpoint_url && (
                      <a
                        href={model.endpoint_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 text-gray-600 hover:bg-gray-100 rounded"
                        title="API端点"
                      >
                        <ExternalLink size={14} />
                      </a>
                    )}
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(model.id) }}
                      className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                      title="删除"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedModel && (
        <ModelDetailModal
          model={selectedModel}
          onClose={() => setSelectedModel(null)}
          onDeploy={() => { setDeployModelId(selectedModel.id); setShowDeployModal(true); setSelectedModel(null) }}
          onUndeploy={() => { handleUndeploy(selectedModel.id); setSelectedModel(null) }}
          onDelete={() => handleDelete(selectedModel.id)}
          onTest={() => { handleTestModel(selectedModel); setSelectedModel(null) }}
        />
      )}

      {showCreateModal && (
        <CreateModelModal
          createType={createType}
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateModel}
        />
      )}

      {showDeployModal && deployModelId && (
        <DeployModal
          onClose={() => { setShowDeployModal(false); setDeployModelId(null) }}
          onDeploy={(config) => handleDeploy(deployModelId, config)}
        />
      )}

      {showTestModal && testModel && (
        <TestModelModal
          model={testModel}
          onClose={() => { setShowTestModal(false); setTestModel(null) }}
        />
      )}
    </div>
  )
}

function ModelDetailModal({ model, onClose, onDeploy, onUndeploy, onDelete, onTest }: {
  model: Model
  onClose: () => void
  onDeploy: () => void
  onUndeploy: () => void
  onDelete: () => void
  onTest: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-auto">
        <div className="p-6 border-b sticky top-0 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center text-2xl">
                {frameworkIcons[model.framework] || '📦'}
              </div>
              <div>
                <h2 className="text-xl font-semibold">{model.name}</h2>
                <div className="flex items-center gap-2">
                  <p className="text-sm text-gray-500">{model.framework} · {model.model_type}</p>
                  <span className={`px-2 py-0.5 text-xs rounded-full ${sourceLabels[model.source]?.color}`}>
                    {sourceLabels[model.source]?.label}
                  </span>
                </div>
              </div>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">描述</h3>
            <p className="text-gray-600">{model.description || '暂无描述'}</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">状态</p>
              <span className={`inline-flex mt-1 px-2 py-0.5 text-xs rounded-full ${statusColors[model.status as ModelStatus]}`}>
                {model.status}
              </span>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">版本</p>
              <p className="font-medium">{model.version}</p>
            </div>
            {model.file_size && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">文件大小</p>
                <p className="font-medium">{formatBytes(model.file_size)}</p>
              </div>
            )}
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">创建时间</p>
              <p className="font-medium">{new Date(model.created_at).toLocaleString()}</p>
            </div>
          </div>

          {model.source === 'huggingface' && model.hf_model_id && (
            <div className="p-4 bg-yellow-50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <Sparkles size={16} /> HuggingFace模型ID
              </h3>
              <code className="text-sm bg-white px-2 py-1 rounded border">{model.hf_model_id}</code>
            </div>
          )}

          {model.source === 'external_api' && model.endpoint_url && (
            <div className="p-4 bg-green-50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <Globe size={16} /> API端点
              </h3>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-sm bg-white px-2 py-1 rounded border overflow-hidden">{model.endpoint_url}</code>
                <button className="p-1 text-gray-600 hover:text-gray-900" onClick={() => navigator.clipboard.writeText(model.endpoint_url!)}>
                  <Copy size={16} />
                </button>
              </div>
            </div>
          )}

          {model.endpoint_url && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">服务端点</h3>
              <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                <code className="flex-1 text-sm">{model.endpoint_url}</code>
                <button className="p-1 text-gray-600 hover:text-gray-900" onClick={() => navigator.clipboard.writeText(model.endpoint_url!)}>
                  <Copy size={16} />
                </button>
                <a href={model.endpoint_url} target="_blank" rel="noopener noreferrer" className="p-1 text-blue-600">
                  <ExternalLink size={16} />
                </a>
              </div>
            </div>
          )}

          {model.tags.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">标签</h3>
              <div className="flex flex-wrap gap-2">
                {model.tags.map((tag, i) => (
                  <span key={i} className="px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded">{tag}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="px-6 py-4 bg-gray-50 flex justify-between gap-3 rounded-b-lg">
          <button
            onClick={onTest}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
          >
            <Zap size={16} /> 测试模型
          </button>
          <div className="flex gap-3">
            <button
              onClick={onDelete}
              className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg"
            >
              删除
            </button>
            {model.status === 'deployed' ? (
              <button
                onClick={onUndeploy}
                className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700"
              >
                取消部署
              </button>
            ) : model.status === 'ready' ? (
              <button
                onClick={onDeploy}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                部署
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}

function CreateModelModal({ createType, onClose, onSubmit }: {
  createType: CreateType
  onClose: () => void
  onSubmit: (data: Partial<Model>) => void
}) {
  const [activeTab, setActiveTab] = useState<CreateType>(createType)
  const [form, setForm] = useState({
    name: '',
    description: '',
    model_type: 'LLM',
    framework: 'pytorch',
    hf_model_id: '',
    external_api_url: '',
    api_key: '',
    tags: '',
  })
  const [searchHF, setSearchHF] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const filteredHFModels = popularHFModels.filter(m => 
    m.name.toLowerCase().includes(searchHF.toLowerCase()) ||
    m.id.toLowerCase().includes(searchHF.toLowerCase())
  )

  const handleSubmit = async () => {
    if (!form.name) return
    setIsLoading(true)
    
    const tags = form.tags.split(',').map(t => t.trim()).filter(Boolean)
    
    if (activeTab === 'huggingface') {
      await onSubmit({
        name: form.name,
        description: form.description,
        model_type: form.model_type,
        framework: 'huggingface',
        source: 'huggingface',
        hf_model_id: form.hf_model_id,
        status: 'ready',
        tags,
      })
    } else if (activeTab === 'external_api') {
      await onSubmit({
        name: form.name,
        description: form.description,
        model_type: form.model_type,
        framework: form.framework,
        source: 'external_api',
        external_api_url: form.external_api_url,
        endpoint_url: form.external_api_url,
        api_key: form.api_key,
        status: 'ready',
        tags,
      })
    } else {
      await onSubmit({
        name: form.name,
        description: form.description,
        model_type: form.model_type,
        framework: form.framework,
        source: 'local',
        status: 'draft',
        tags,
      })
    }
    
    setIsLoading(false)
  }

  const selectHFModel = (model: typeof popularHFModels[0]) => {
    setForm({
      ...form,
      name: model.name,
      hf_model_id: model.id,
      model_type: model.task === 'LLM' ? 'LLM' : model.task === 'NLP' ? 'NLP' : model.task === 'Image' ? 'CV' : 'custom',
    })
  }

  const presetAPIs = [
    { name: 'OpenAI GPT-4', framework: 'openai', url: 'https://api.openai.com/v1/chat/completions' },
    { name: 'Anthropic Claude', framework: 'anthropic', url: 'https://api.anthropic.com/v1/messages' },
    { name: '百度文心一言', framework: 'custom', url: 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions' },
    { name: '阿里通义千问', framework: 'custom', url: 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation' },
    { name: '智谱ChatGLM', framework: 'custom', url: 'https://open.bigmodel.cn/api/paas/v3/model-api/chatglm_pro/invoke' },
  ]

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-auto">
        <div className="p-4 border-b">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">添加模型</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <X size={20} />
            </button>
          </div>
          
          <div className="flex gap-2">
            {[
              { id: 'local' as const, label: '本地模型', icon: Brain },
              { id: 'huggingface' as const, label: 'HuggingFace', icon: Sparkles },
              { id: 'external_api' as const, label: '外部API', icon: Globe },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
                  activeTab === tab.id ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <tab.icon size={18} />
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="p-6 space-y-4">
          {activeTab === 'local' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">模型名称</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="输入模型名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                  rows={2}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">类型</label>
                  <select
                    value={form.model_type}
                    onChange={(e) => setForm({ ...form, model_type: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="LLM">大语言模型</option>
                    <option value="NLP">自然语言处理</option>
                    <option value="CV">计算机视觉</option>
                    <option value="ASR">语音识别</option>
                    <option value="custom">自定义</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">框架</label>
                  <select
                    value={form.framework}
                    onChange={(e) => setForm({ ...form, framework: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="pytorch">PyTorch</option>
                    <option value="tensorflow">TensorFlow</option>
                    <option value="sklearn">Scikit-learn</option>
                    <option value="custom">自定义</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">标签 (逗号分隔)</label>
                <input
                  type="text"
                  value={form.tags}
                  onChange={(e) => setForm({ ...form, tags: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="NLP, 对话, 中文"
                />
              </div>
            </>
          )}

          {activeTab === 'huggingface' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">搜索HuggingFace模型</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                  <input
                    type="text"
                    value={searchHF}
                    onChange={(e) => setSearchHF(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border rounded-lg"
                    placeholder="搜索模型名称或ID..."
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">热门模型</label>
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                  {filteredHFModels.map((model) => (
                    <button
                      key={model.id}
                      onClick={() => selectHFModel(model)}
                      className={`p-3 text-left border rounded-lg hover:bg-blue-50 ${
                        form.hf_model_id === model.id ? 'border-blue-500 bg-blue-50' : ''
                      }`}
                    >
                      <p className="font-medium text-sm">{model.name}</p>
                      <p className="text-xs text-gray-500">{model.id}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-gray-400">{model.downloads} 下载</span>
                        <span className="text-xs px-1.5 py-0.5 bg-gray-100 rounded">{model.task}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">或输入模型ID</label>
                <input
                  type="text"
                  value={form.hf_model_id}
                  onChange={(e) => setForm({ ...form, hf_model_id: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="例如: bert-base-uncased, meta-llama/Llama-2-7b-hf"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">模型名称</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="为模型命名"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                  rows={2}
                />
              </div>
            </>
          )}

          {activeTab === 'external_api' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">预设API服务</label>
                <div className="grid grid-cols-2 gap-2">
                  {presetAPIs.map((api) => (
                    <button
                      key={api.name}
                      onClick={() => setForm({ 
                        ...form, 
                        name: form.name || api.name,
                        framework: api.framework, 
                        external_api_url: api.url 
                      })}
                      className={`p-3 text-left border rounded-lg hover:bg-green-50 ${
                        form.external_api_url === api.url ? 'border-green-500 bg-green-50' : ''
                      }`}
                    >
                      <p className="font-medium text-sm">{api.name}</p>
                      <p className="text-xs text-gray-500">{api.framework}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">模型名称</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="输入模型名称"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API端点URL</label>
                <div className="flex items-center gap-2">
                  <Globe size={18} className="text-gray-400" />
                  <input
                    type="text"
                    value={form.external_api_url}
                    onChange={(e) => setForm({ ...form, external_api_url: e.target.value })}
                    className="flex-1 px-3 py-2 border rounded-lg"
                    placeholder="https://api.example.com/v1/chat"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API密钥</label>
                <div className="flex items-center gap-2">
                  <Key size={18} className="text-gray-400" />
                  <input
                    type="password"
                    value={form.api_key}
                    onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                    className="flex-1 px-3 py-2 border rounded-lg"
                    placeholder="sk-..."
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">类型</label>
                  <select
                    value={form.model_type}
                    onChange={(e) => setForm({ ...form, model_type: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="LLM">大语言模型</option>
                    <option value="NLP">自然语言处理</option>
                    <option value="Embedding">向量嵌入</option>
                    <option value="Image">图像生成</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">框架/提供商</label>
                  <select
                    value={form.framework}
                    onChange={(e) => setForm({ ...form, framework: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="baidu">百度</option>
                    <option value="alibaba">阿里</option>
                    <option value="zhipu">智谱</option>
                    <option value="custom">自定义</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                  rows={2}
                />
              </div>
            </>
          )}
        </div>

        <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3 rounded-b-lg">
          <button onClick={onClose} className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg">取消</button>
          <button
            onClick={handleSubmit}
            disabled={!form.name || isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? '添加中...' : '添加模型'}
          </button>
        </div>
      </div>
    </div>
  )
}

function DeployModal({ onClose, onDeploy }: {
  onClose: () => void
  onDeploy: (config: Record<string, any>) => void
}) {
  const [config, setConfig] = useState({
    replicas: 1,
    cpu: '2',
    memory: '4Gi',
    gpu: 0,
    auto_scaling: false,
    max_replicas: 5,
  })

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">部署模型</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">副本数</label>
              <input
                type="number"
                value={config.replicas}
                onChange={(e) => setConfig({ ...config, replicas: parseInt(e.target.value) || 1 })}
                className="w-full px-3 py-2 border rounded-lg"
                min={1}
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">CPU</label>
                <input
                  type="text"
                  value={config.cpu}
                  onChange={(e) => setConfig({ ...config, cpu: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">内存</label>
                <input
                  type="text"
                  value={config.memory}
                  onChange={(e) => setConfig({ ...config, memory: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">GPU</label>
                <input
                  type="number"
                  value={config.gpu}
                  onChange={(e) => setConfig({ ...config, gpu: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border rounded-lg"
                  min={0}
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="auto_scaling"
                checked={config.auto_scaling}
                onChange={(e) => setConfig({ ...config, auto_scaling: e.target.checked })}
              />
              <label htmlFor="auto_scaling" className="text-sm text-gray-700">启用自动扩缩容</label>
            </div>
          </div>
        </div>
        <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3 rounded-b-lg">
          <button onClick={onClose} className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg">取消</button>
          <button
            onClick={() => onDeploy(config)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            部署
          </button>
        </div>
      </div>
    </div>
  )
}

function TestModelModal({ model, onClose }: {
  model: Model
  onClose: () => void
}) {
  const [input, setInput] = useState('')
  const [output, setOutput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleTest = async () => {
    if (!input) return
    setIsLoading(true)
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    setOutput(`[${model.name}] 响应结果:\n\n您输入的是: "${input}"\n\n这是一个模拟的响应结果。实际使用时，会调用 ${model.endpoint_url || model.external_api_url || '模型服务端点'} 进行推理。`)
    setIsLoading(false)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4">
        <div className="p-4 border-b flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Zap className="text-green-600" size={20} />
            <h2 className="text-lg font-semibold">测试模型: {model.name}</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>
        
        <div className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">输入</label>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              rows={4}
              placeholder="输入测试内容..."
            />
          </div>
          
          <button
            onClick={handleTest}
            disabled={!input || isLoading}
            className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                处理中...
              </>
            ) : (
              <>
                <Zap size={18} />
                执行测试
              </>
            )}
          </button>

          {output && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">输出</label>
              <pre className="w-full px-3 py-2 bg-gray-50 border rounded-lg text-sm whitespace-pre-wrap">
                {output}
              </pre>
            </div>
          )}
        </div>

        <div className="px-4 py-3 bg-gray-50 rounded-b-lg flex justify-end">
          <button onClick={onClose} className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg">
            关闭
          </button>
        </div>
      </div>
    </div>
  )
}

function formatBytes(bytes: number): string {
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`
}
