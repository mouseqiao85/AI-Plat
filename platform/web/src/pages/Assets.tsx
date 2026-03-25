import { useState, useEffect } from 'react'
import { Search, Filter, Plus, Star, Download, Brain, Database, AppWindow, Play, Pause, Trash2, Edit2, ExternalLink, X, Copy } from 'lucide-react'

interface Model {
  id: string
  name: string
  description: string
  type: string
  framework: string
  rating: number
  calls: number
  status: 'available' | 'deployed' | 'error'
  endpoint?: string
  tags: string[]
  created_at: string
}

interface Dataset {
  id: string
  name: string
  description: string
  type: string
  size: string
  format: string
  record_count: number
  status: 'ready' | 'processing' | 'error'
  tags: string[]
  created_at: string
}

interface App {
  id: string
  name: string
  description: string
  model_id: string
  status: 'running' | 'stopped' | 'error'
  deployments: number
  endpoint?: string
  created_at: string
}

type TabType = 'models' | 'data' | 'apps'

function Assets() {
  const [activeTab, setActiveTab] = useState<TabType>('models')
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [modalType, setModalType] = useState<'create' | 'edit' | 'detail'>('create')
  const [selectedItem, setSelectedItem] = useState<any>(null)
  
  const [models, setModels] = useState<Model[]>([])
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [apps, setApps] = useState<App[]>([])
  const [favorites, setFavorites] = useState<string[]>(['model-1', 'dataset-1', 'app-1'])

  useEffect(() => {
    fetchData()
  }, [activeTab])

  const fetchData = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const headers: Record<string, string> = token ? { 'Authorization': `Bearer ${token}` } : {}
      
      if (activeTab === 'models') {
        const res = await fetch('/api/models', { headers })
        if (res.ok) {
          const data = await res.json()
          setModels(data.models || data || getMockModels())
        } else {
          setModels(getMockModels())
        }
      } else if (activeTab === 'data') {
        const res = await fetch('/api/mlops/datasets', { headers })
        if (res.ok) {
          const data = await res.json()
          setDatasets(data.datasets || data || getMockDatasets())
        } else {
          setDatasets(getMockDatasets())
        }
      } else if (activeTab === 'apps') {
        setApps(getMockApps())
      }
    } catch (error) {
      console.error('Failed to fetch data:', error)
      if (activeTab === 'models') setModels(getMockModels())
      if (activeTab === 'data') setDatasets(getMockDatasets())
      if (activeTab === 'apps') setApps(getMockApps())
    }
    setLoading(false)
  }

  const getMockModels = (): Model[] => [
    { id: 'model-1', name: 'GPT-4 Turbo', description: 'OpenAI最新大语言模型', type: 'LLM', framework: 'openai', rating: 4.8, calls: 12800, status: 'available', tags: ['NLP', '对话', '推理'], created_at: '2024-01-15' },
    { id: 'model-2', name: 'Claude-3 Opus', description: 'Anthropic大语言模型', type: 'LLM', framework: 'anthropic', rating: 4.6, calls: 8200, status: 'deployed', endpoint: 'https://api.example.com/claude', tags: ['NLP', '对话'], created_at: '2024-02-20' },
    { id: 'model-3', name: '文心一言', description: '百度大语言模型', type: 'LLM', framework: 'baidu', rating: 4.5, calls: 6500, status: 'available', tags: ['NLP', '中文'], created_at: '2024-03-01' },
    { id: 'model-4', name: '通义千问', description: '阿里大语言模型', type: 'LLM', framework: 'alibaba', rating: 4.4, calls: 4100, status: 'available', tags: ['NLP', '中文'], created_at: '2024-03-10' },
    { id: 'model-5', name: '图像分类模型', description: 'ResNet50图像分类', type: 'CV', framework: 'pytorch', rating: 4.3, calls: 3200, status: 'deployed', endpoint: 'https://api.example.com/resnet', tags: ['CV', '分类'], created_at: '2024-02-01' },
    { id: 'model-6', name: '语音识别模型', description: 'Whisper语音转文字', type: 'ASR', framework: 'openai', rating: 4.7, calls: 5800, status: 'available', tags: ['语音', 'ASR'], created_at: '2024-01-20' },
  ]

  const getMockDatasets = (): Dataset[] => [
    { id: 'dataset-1', name: '客户服务对话数据集', description: '客服对话记录数据', type: 'text', size: '50MB', format: 'JSON', record_count: 10000, status: 'ready', tags: ['对话', '客服'], created_at: '2024-01-15' },
    { id: 'dataset-2', name: '产品知识库', description: '产品说明和FAQ数据', type: 'structured', size: '120MB', format: 'CSV', record_count: 5000, status: 'ready', tags: ['知识库', 'FAQ'], created_at: '2024-02-20' },
    { id: 'dataset-3', name: '销售记录数据', description: '历史销售数据', type: 'structured', size: '200MB', format: 'Parquet', record_count: 50000, status: 'ready', tags: ['销售', '分析'], created_at: '2024-03-01' },
    { id: 'dataset-4', name: '用户反馈数据', description: '用户评价和反馈', type: 'text', size: '80MB', format: 'JSON', record_count: 20000, status: 'processing', tags: ['反馈', 'NLP'], created_at: '2024-03-10' },
    { id: 'dataset-5', name: '图像数据集', description: '产品图片数据', type: 'image', size: '2GB', format: 'JPEG', record_count: 5000, status: 'ready', tags: ['图像', 'CV'], created_at: '2024-02-15' },
  ]

  const getMockApps = (): App[] => [
    { id: 'app-1', name: '智能客服机器人', description: '基于LLM的智能客服系统', model_id: 'model-1', status: 'running', deployments: 3, endpoint: 'https://app.example.com/chatbot', created_at: '2024-01-20' },
    { id: 'app-2', name: '文档问答助手', description: '文档理解和问答系统', model_id: 'model-2', status: 'running', deployments: 2, endpoint: 'https://app.example.com/docqa', created_at: '2024-02-15' },
    { id: 'app-3', name: '报告生成器', description: '自动生成分析报告', model_id: 'model-3', status: 'stopped', deployments: 1, created_at: '2024-03-01' },
    { id: 'app-4', name: '图像分类服务', description: '产品图片自动分类', model_id: 'model-5', status: 'running', deployments: 2, endpoint: 'https://app.example.com/image-class', created_at: '2024-02-10' },
  ]

  const toggleFavorite = (id: string) => {
    if (favorites.includes(id)) {
      setFavorites(favorites.filter(f => f !== id))
    } else {
      setFavorites([...favorites, id])
    }
  }

  const handleCreateAsset = () => {
    setModalType('create')
    setSelectedItem(null)
    setShowModal(true)
  }

  const handleEditAsset = (item: any) => {
    setModalType('edit')
    setSelectedItem(item)
    setShowModal(true)
  }

  const handleViewDetail = (item: any) => {
    setModalType('detail')
    setSelectedItem(item)
    setShowModal(true)
  }

  const handleDeployModel = async (model: Model) => {
    alert(`正在部署模型: ${model.name}`)
  }

  const handleToggleApp = async (app: App) => {
    const newStatus = app.status === 'running' ? 'stopped' : 'running'
    setApps(apps.map(a => a.id === app.id ? { ...a, status: newStatus } : a))
  }

  const handleDeleteAsset = async (type: TabType, id: string) => {
    if (!confirm('确定要删除此资产吗？')) return
    if (type === 'models') setModels(models.filter(m => m.id !== id))
    if (type === 'data') setDatasets(datasets.filter(d => d.id !== id))
    if (type === 'apps') setApps(apps.filter(a => a.id !== id))
  }

  const handleDownloadDataset = async (dataset: Dataset) => {
    alert(`正在下载数据集: ${dataset.name}`)
  }

  const copyEndpoint = (endpoint: string) => {
    navigator.clipboard.writeText(endpoint)
    alert('端点地址已复制到剪贴板')
  }

  const tabs = [
    { id: 'models' as TabType, label: '模型广场', icon: Brain, count: models.length },
    { id: 'data' as TabType, label: '数据广场', icon: Database, count: datasets.length },
    { id: 'apps' as TabType, label: '应用广场', icon: AppWindow, count: apps.length },
  ]

  const filteredModels = models.filter(m => 
    m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const filteredDatasets = datasets.filter(d => 
    d.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    d.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const filteredApps = apps.filter(a => 
    a.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    a.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const renderModels = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {filteredModels.map((model) => (
        <div key={model.id} className="bg-white rounded-lg shadow hover:shadow-md transition-shadow cursor-pointer" onClick={() => handleViewDetail(model)}>
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-100 to-purple-100 rounded-lg flex items-center justify-center">
                <Brain className="w-6 h-6 text-blue-600" />
              </div>
              <div className="flex items-center gap-2">
                <button 
                  onClick={(e) => { e.stopPropagation(); toggleFavorite(model.id) }}
                  className="p-1.5 hover:bg-gray-100 rounded"
                >
                  <Star className={`w-4 h-4 ${favorites.includes(model.id) ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'}`} />
                </button>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  model.status === 'deployed' ? 'bg-green-100 text-green-700' :
                  model.status === 'available' ? 'bg-blue-100 text-blue-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  {model.status === 'deployed' ? '已部署' : model.status === 'available' ? '可用' : '错误'}
                </span>
              </div>
            </div>
            <h3 className="font-semibold text-gray-900 mb-1">{model.name}</h3>
            <p className="text-sm text-gray-500 mb-3 line-clamp-2">{model.description}</p>
            <div className="flex items-center gap-4 text-sm text-gray-500 mb-3">
              <div className="flex items-center gap-1">
                <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                <span>{model.rating}</span>
              </div>
              <span>{(model.calls / 1000).toFixed(1)}K 调用</span>
              <span className="text-xs px-2 py-0.5 bg-gray-100 rounded">{model.type}</span>
            </div>
            <div className="flex flex-wrap gap-1 mb-4">
              {model.tags.slice(0, 3).map((tag, idx) => (
                <span key={idx} className="text-xs px-2 py-0.5 bg-gray-50 text-gray-600 rounded">{tag}</span>
              ))}
            </div>
            <div className="flex gap-2">
              {model.status !== 'deployed' && (
                <button 
                  onClick={(e) => { e.stopPropagation(); handleDeployModel(model) }}
                  className="flex-1 btn btn-primary text-sm py-1.5"
                >
                  部署
                </button>
              )}
              {model.endpoint && (
                <button 
                  onClick={(e) => { e.stopPropagation(); copyEndpoint(model.endpoint!) }}
                  className="btn btn-secondary text-sm py-1.5"
                >
                  <Copy size={14} />
                </button>
              )}
              <button 
                onClick={(e) => { e.stopPropagation(); handleEditAsset(model) }}
                className="btn btn-secondary text-sm py-1.5"
              >
                <Edit2 size={14} />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )

  const renderDatasets = () => (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">名称</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">类型</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">格式</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">大小</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">记录数</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {filteredDatasets.map((dataset) => (
            <tr key={dataset.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => handleViewDetail(dataset)}>
              <td className="px-6 py-4">
                <div className="flex items-center gap-3">
                  <button 
                    onClick={(e) => { e.stopPropagation(); toggleFavorite(dataset.id) }}
                    className="p-0.5"
                  >
                    <Star className={`w-4 h-4 ${favorites.includes(dataset.id) ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'}`} />
                  </button>
                  <div>
                    <p className="font-medium text-gray-900">{dataset.name}</p>
                    <p className="text-sm text-gray-500">{dataset.description}</p>
                  </div>
                </div>
              </td>
              <td className="px-6 py-4 text-sm text-gray-500">{dataset.type}</td>
              <td className="px-6 py-4 text-sm text-gray-500">{dataset.format}</td>
              <td className="px-6 py-4 text-sm text-gray-500">{dataset.size}</td>
              <td className="px-6 py-4 text-sm text-gray-500">{dataset.record_count.toLocaleString()}</td>
              <td className="px-6 py-4">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  dataset.status === 'ready' ? 'bg-green-100 text-green-700' :
                  dataset.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  {dataset.status === 'ready' ? '就绪' : dataset.status === 'processing' ? '处理中' : '错误'}
                </span>
              </td>
              <td className="px-6 py-4 text-right">
                <div className="flex items-center justify-end gap-2">
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleDownloadDataset(dataset) }}
                    className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
                    title="下载"
                  >
                    <Download size={16} />
                  </button>
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleEditAsset(dataset) }}
                    className="p-1.5 text-gray-600 hover:bg-gray-100 rounded"
                    title="编辑"
                  >
                    <Edit2 size={16} />
                  </button>
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleDeleteAsset('data', dataset.id) }}
                    className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                    title="删除"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  const renderApps = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {filteredApps.map((app) => (
        <div key={app.id} className="bg-white rounded-lg shadow hover:shadow-md transition-shadow cursor-pointer" onClick={() => handleViewDetail(app)}>
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="w-12 h-12 bg-gradient-to-br from-green-100 to-teal-100 rounded-lg flex items-center justify-center">
                <AppWindow className="w-6 h-6 text-green-600" />
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                app.status === 'running' ? 'bg-green-100 text-green-700' :
                app.status === 'stopped' ? 'bg-gray-100 text-gray-700' :
                'bg-red-100 text-red-700'
              }`}>
                {app.status === 'running' ? '运行中' : app.status === 'stopped' ? '已停止' : '错误'}
              </span>
            </div>
            <h3 className="font-semibold text-gray-900 mb-1">{app.name}</h3>
            <p className="text-sm text-gray-500 mb-3">{app.description}</p>
            <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
              <span>{app.deployments} 个部署</span>
              {app.endpoint && (
                <a 
                  href={app.endpoint} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-1 text-blue-600 hover:text-blue-700"
                >
                  <ExternalLink size={14} />
                  访问
                </a>
              )}
            </div>
            <div className="flex gap-2">
              <button 
                onClick={(e) => { e.stopPropagation(); handleToggleApp(app) }}
                className={`flex-1 btn text-sm py-1.5 ${app.status === 'running' ? 'btn-secondary' : 'btn-primary'}`}
              >
                {app.status === 'running' ? <Pause size={14} className="mr-1" /> : <Play size={14} className="mr-1" />}
                {app.status === 'running' ? '停止' : '启动'}
              </button>
              <button 
                onClick={(e) => { e.stopPropagation(); handleEditAsset(app) }}
                className="btn btn-secondary text-sm py-1.5"
              >
                <Edit2 size={14} />
              </button>
              <button 
                onClick={(e) => { e.stopPropagation(); handleDeleteAsset('apps', app.id) }}
                className="btn btn-secondary text-sm py-1.5 text-red-600"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )

  const favoriteItems = [
    ...models.filter(m => favorites.includes(m.id)).map(m => ({ type: 'model', name: m.name, id: m.id })),
    ...datasets.filter(d => favorites.includes(d.id)).map(d => ({ type: 'dataset', name: d.name, id: d.id })),
    ...apps.filter(a => favorites.includes(a.id)).map(a => ({ type: 'app', name: a.name, id: a.id })),
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">资产广场</h1>
        <div className="flex items-center gap-3">
          <button className="btn btn-secondary flex items-center gap-2">
            <Filter className="w-4 h-4" />
            筛选
          </button>
          <button onClick={handleCreateAsset} className="btn btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" />
            新建资产
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {tabs.map((tab) => (
          <div
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`bg-white rounded-lg shadow p-4 cursor-pointer transition-all ${
              activeTab === tab.id ? 'ring-2 ring-blue-500' : 'hover:shadow-md'
            }`}
          >
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                activeTab === tab.id ? 'bg-blue-100' : 'bg-gray-100'
              }`}>
                <tab.icon className={`w-6 h-6 ${
                  activeTab === tab.id ? 'text-blue-600' : 'text-gray-500'
                }`} />
              </div>
              <div>
                <p className="font-medium text-gray-900">{tab.label}</p>
                <p className="text-sm text-gray-500">{tab.count} 个项目</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input 
            type="text" 
            placeholder="搜索资产..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <>
          {activeTab === 'models' && renderModels()}
          {activeTab === 'data' && renderDatasets()}
          {activeTab === 'apps' && renderApps()}
        </>
      )}

      {favoriteItems.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">我的收藏</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {favoriteItems.map((item) => (
              <div key={`${item.type}-${item.id}`} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer">
                <Star className="w-4 h-4 text-yellow-400 fill-yellow-400 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-gray-700 truncate">{item.name}</p>
                  <p className="text-xs text-gray-400">{item.type === 'model' ? '模型' : item.type === 'dataset' ? '数据集' : '应用'}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {showModal && (
        <AssetModal
          type={activeTab}
          modalType={modalType}
          item={selectedItem}
          onClose={() => setShowModal(false)}
          onSave={() => {
            setShowModal(false)
            fetchData()
          }}
        />
      )}
    </div>
  )
}

function AssetModal({ type, modalType, item, onClose, onSave }: {
  type: TabType
  modalType: 'create' | 'edit' | 'detail'
  item: any
  onClose: () => void
  onSave: () => void
}) {
  const [form, setForm] = useState({
    name: item?.name || '',
    description: item?.description || '',
    type: item?.type || '',
    framework: item?.framework || '',
    format: item?.format || '',
    tags: item?.tags?.join(', ') || '',
  })

  const title = {
    create: type === 'models' ? '新建模型' : type === 'data' ? '新建数据集' : '新建应用',
    edit: type === 'models' ? '编辑模型' : type === 'data' ? '编辑数据集' : '编辑应用',
    detail: type === 'models' ? '模型详情' : type === 'data' ? '数据集详情' : '应用详情',
  }[modalType]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Form submitted:', form)
    onSave()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {modalType === 'detail' ? (
          <div className="p-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">名称</p>
                <p className="font-medium">{item?.name}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">状态</p>
                <p className="font-medium">{item?.status}</p>
              </div>
              <div className="col-span-2">
                <p className="text-sm text-gray-500">描述</p>
                <p className="font-medium">{item?.description}</p>
              </div>
              {item?.endpoint && (
                <div className="col-span-2">
                  <p className="text-sm text-gray-500">端点</p>
                  <code className="text-sm bg-gray-100 px-2 py-1 rounded">{item.endpoint}</code>
                </div>
              )}
              {item?.tags && (
                <div className="col-span-2">
                  <p className="text-sm text-gray-500 mb-1">标签</p>
                  <div className="flex flex-wrap gap-1">
                    {item.tags.map((tag: string, idx: number) => (
                      <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-sm rounded">{tag}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 pt-4 border-t">
              <button onClick={onClose} className="btn btn-secondary">关闭</button>
              <button onClick={() => { onClose(); /* open edit */ }} className="btn btn-primary">编辑</button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
              />
            </div>
            {type === 'models' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">框架</label>
                <select
                  value={form.framework}
                  onChange={(e) => setForm({ ...form, framework: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">选择框架</option>
                  <option value="pytorch">PyTorch</option>
                  <option value="tensorflow">TensorFlow</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="baidu">百度</option>
                  <option value="alibaba">阿里</option>
                </select>
              </div>
            )}
            {type === 'data' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">格式</label>
                <select
                  value={form.format}
                  onChange={(e) => setForm({ ...form, format: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">选择格式</option>
                  <option value="JSON">JSON</option>
                  <option value="CSV">CSV</option>
                  <option value="Parquet">Parquet</option>
                  <option value="JPEG">JPEG</option>
                </select>
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">标签 (逗号分隔)</label>
              <input
                type="text"
                value={form.tags}
                onChange={(e) => setForm({ ...form, tags: e.target.value })}
                placeholder="NLP, 对话, 中文"
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex justify-end gap-3 pt-4 border-t">
              <button type="button" onClick={onClose} className="btn btn-secondary">取消</button>
              <button type="submit" className="btn btn-primary">
                {modalType === 'create' ? '创建' : '保存'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export default Assets
