import { useState, useEffect } from 'react'
import { 
  Database, Upload, Search, Trash2, Download, Edit2,
  Eye, RefreshCw,
  Plus, Link2, Brain, Zap, Play, Settings, ChevronRight,
  FileJson, Network, Sparkles, X, Save
} from 'lucide-react'

interface OntologyDataset {
  id: string
  name: string
  description: string
  data_type: 'ontology' | 'knowledge_graph' | 'entity_list' | 'relation_set'
  status: 'draft' | 'ready' | 'processing' | 'error'
  format: string
  file_size?: number
  record_count?: number
  entities?: Entity[]
  relations?: Relation[]
  schema?: OntologySchema
  created_at: string
  updated_at: string
}

interface Entity {
  id: string
  name: string
  type: string
  description: string | null
  properties: Record<string, any> | null
}

interface Relation {
  id: string
  source_id: string
  target_id: string
  relation_type: string
  confidence: number
}

interface OntologySchema {
  entity_types: string[]
  relation_types: string[]
  properties: Record<string, string[]>
}

interface ReasoningResult {
  query: string
  answer: string
  confidence: number
  reasoning_chain: string[]
  related_entities: string[]
}

type TabType = 'datasets' | 'entities' | 'relations' | 'reasoning' | 'schema'

export default function DataManagement() {
  const [activeTab, setActiveTab] = useState<TabType>('datasets')
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  
  // 数据集
  const [datasets, setDatasets] = useState<OntologyDataset[]>([])
  const [selectedDataset, setSelectedDataset] = useState<OntologyDataset | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  
  // 实体和关系
  const [entities, setEntities] = useState<Entity[]>([])
  const [relations, setRelations] = useState<Relation[]>([])
  
  // 推理
  const [reasoningQuery, setReasoningQuery] = useState('')
  const [reasoningType, setReasoningType] = useState('deductive')
  const [reasoningResult, setReasoningResult] = useState<ReasoningResult | null>(null)
  const [reasoningLoading, setReasoningLoading] = useState(false)

  useEffect(() => {
    fetchData()
  }, [activeTab])

  const fetchData = async () => {
    setLoading(true)
    try {
      if (activeTab === 'datasets') {
        const res = await fetch('/api/mlops/datasets')
        if (res.ok) {
          const data = await res.json()
          setDatasets(data.datasets || getMockDatasets())
        } else {
          setDatasets(getMockDatasets())
        }
      } else if (activeTab === 'entities' || activeTab === 'relations') {
        const res = await fetch('/api/ontology/entities')
        if (res.ok) {
          const data = await res.json()
          setEntities(data.entities || getMockEntities())
        } else {
          setEntities(getMockEntities())
        }
        
        const relRes = await fetch('/api/ontology/relations')
        if (relRes.ok) {
          const data = await relRes.json()
          setRelations(data.relations || getMockRelations())
        } else {
          setRelations(getMockRelations())
        }
      }
    } catch (error) {
      console.error('Failed to fetch data:', error)
      if (activeTab === 'datasets') setDatasets(getMockDatasets())
      if (activeTab === 'entities') {
        setEntities(getMockEntities())
        setRelations(getMockRelations())
      }
    }
    setLoading(false)
  }

  const getMockDatasets = (): OntologyDataset[] => [
    { id: '1', name: '产品知识图谱', description: '产品分类和属性知识图谱', data_type: 'knowledge_graph', status: 'ready', format: 'JSON', file_size: 2048000, record_count: 1500, created_at: '2024-01-15', updated_at: '2024-03-01' },
    { id: '2', name: '供应链本体', description: '供应商、物料、工厂关系本体', data_type: 'ontology', status: 'ready', format: 'OWL', file_size: 512000, record_count: 320, created_at: '2024-02-20', updated_at: '2024-03-05' },
    { id: '3', name: '客户实体库', description: '客户信息和标签实体', data_type: 'entity_list', status: 'ready', format: 'CSV', file_size: 1024000, record_count: 5000, created_at: '2024-03-01', updated_at: '2024-03-10' },
    { id: '4', name: '业务流程关系', description: '业务流程间的关系定义', data_type: 'relation_set', status: 'processing', format: 'JSON', file_size: 256000, record_count: 180, created_at: '2024-03-10', updated_at: '2024-03-10' },
  ]

  const getMockEntities = (): Entity[] => [
    { id: 'e1', name: '产品', type: 'class', description: '产品实体类', properties: { properties: ['name', 'price', 'category'] } },
    { id: 'e2', name: '供应商', type: 'class', description: '供应商实体类', properties: { properties: ['name', 'location', 'rating'] } },
    { id: 'e3', name: '客户', type: 'class', description: '客户实体类', properties: { properties: ['name', 'email', 'level'] } },
    { id: 'e4', name: '订单', type: 'class', description: '订单实体类', properties: { properties: ['order_id', 'amount', 'status'] } },
    { id: 'e5', name: 'iPhone 15', type: 'individual', description: '苹果手机产品', properties: { price: 7999, category: '手机' } },
    { id: 'e6', name: '华为供应商A', type: 'individual', description: '华为一级供应商', properties: { location: '深圳' } },
  ]

  const getMockRelations = (): Relation[] => [
    { id: 'r1', source_id: 'e2', target_id: 'e1', relation_type: 'supplies', confidence: 0.95 },
    { id: 'r2', source_id: 'e3', target_id: 'e4', relation_type: 'places', confidence: 1.0 },
    { id: 'r3', source_id: 'e4', target_id: 'e1', relation_type: 'contains', confidence: 1.0 },
    { id: 'r4', source_id: 'e1', target_id: 'e2', relation_type: 'manufactured_by', confidence: 0.88 },
  ]

  const handleCreateDataset = async (data: Partial<OntologyDataset>) => {
    const newDataset: OntologyDataset = {
      id: Date.now().toString(),
      name: data.name || '',
      description: data.description || '',
      data_type: data.data_type || 'ontology',
      status: 'draft',
      format: data.format || 'JSON',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    setDatasets([...datasets, newDataset])
    setShowCreateModal(false)
  }

  const handleUpdateDataset = async (id: string, data: Partial<OntologyDataset>) => {
    setDatasets(datasets.map(d => d.id === id ? { ...d, ...data, updated_at: new Date().toISOString() } : d))
    setShowEditModal(false)
    setSelectedDataset(null)
  }

  const handleDeleteDataset = async (id: string) => {
    if (!confirm('确定要删除此数据集吗？')) return
    setDatasets(datasets.filter(d => d.id !== id))
  }

  const handleCreateEntity = async (entity: Partial<Entity>) => {
    const newEntity: Entity = {
      id: Date.now().toString(),
      name: entity.name || '',
      type: entity.type || 'class',
      description: entity.description || null,
      properties: entity.properties || null,
    }
    setEntities([...entities, newEntity])
  }

  const handleDeleteEntity = async (id: string) => {
    setEntities(entities.filter(e => e.id !== id))
    setRelations(relations.filter(r => r.source_id !== id && r.target_id !== id))
  }

  const handleCreateRelation = async (relation: Partial<Relation>) => {
    const newRelation: Relation = {
      id: Date.now().toString(),
      source_id: relation.source_id || '',
      target_id: relation.target_id || '',
      relation_type: relation.relation_type || '',
      confidence: relation.confidence || 1.0,
    }
    setRelations([...relations, newRelation])
  }

  const handleDeleteRelation = async (id: string) => {
    setRelations(relations.filter(r => r.id !== id))
  }

  const handleReasoning = async () => {
    if (!reasoningQuery.trim()) return
    setReasoningLoading(true)
    
    // 模拟推理
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    setReasoningResult({
      query: reasoningQuery,
      answer: `基于知识图谱分析，${reasoningQuery}的推理结果如下：通过实体关系分析，发现相关联的实体之间存在明确的语义关系。`,
      confidence: 0.87,
      reasoning_chain: [
        '解析查询意图，识别关键实体',
        '在知识图谱中检索相关实体节点',
        '遍历关系边，发现关联路径',
        '应用推理规则，得出结论',
      ],
      related_entities: ['产品', '供应商', '订单'],
    })
    setReasoningLoading(false)
  }

  const formatBytes = (bytes?: number) => {
    if (!bytes) return '-'
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${sizes[i]}`
  }

  const getEntityName = (id: string) => {
    return entities.find(e => e.id === id)?.name || id
  }

  const stats = {
    datasets: datasets.length,
    entities: entities.length,
    relations: relations.length,
    ready: datasets.filter(d => d.status === 'ready').length,
  }

  const tabs: { id: TabType; label: string; icon: any }[] = [
    { id: 'datasets', label: '数据集管理', icon: Database },
    { id: 'entities', label: '实体管理', icon: FileJson },
    { id: 'relations', label: '关系管理', icon: Network },
    { id: 'reasoning', label: '推理服务', icon: Brain },
    { id: 'schema', label: '本体配置', icon: Settings },
  ]

  const renderDatasets = () => (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-lg"
            placeholder="搜索数据集..."
          />
        </div>
        <button onClick={() => setShowCreateModal(true)} className="btn btn-primary flex items-center gap-2">
          <Plus size={18} /> 新建数据集
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">名称</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">类型</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">格式</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">大小</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">记录数</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {datasets.filter(d => d.name.includes(searchTerm)).map((dataset) => (
              <tr key={dataset.id} className="hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div>
                    <p className="font-medium text-gray-900">{dataset.name}</p>
                    <p className="text-sm text-gray-500">{dataset.description}</p>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                    {dataset.data_type === 'ontology' ? '本体' : 
                     dataset.data_type === 'knowledge_graph' ? '知识图谱' :
                     dataset.data_type === 'entity_list' ? '实体列表' : '关系集'}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs rounded ${
                    dataset.status === 'ready' ? 'bg-green-100 text-green-700' :
                    dataset.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {dataset.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">{dataset.format}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{formatBytes(dataset.file_size)}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{dataset.record_count?.toLocaleString()}</td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button onClick={() => { setSelectedDataset(dataset); setShowPreviewModal(true) }} className="p-1.5 text-gray-600 hover:bg-gray-100 rounded" title="预览">
                      <Eye size={16} />
                    </button>
                    <button onClick={() => { setSelectedDataset(dataset); setShowEditModal(true) }} className="p-1.5 text-blue-600 hover:bg-blue-50 rounded" title="编辑">
                      <Edit2 size={16} />
                    </button>
                    <button className="p-1.5 text-gray-600 hover:bg-gray-100 rounded" title="下载">
                      <Download size={16} />
                    </button>
                    <button onClick={() => handleDeleteDataset(dataset.id)} className="p-1.5 text-red-600 hover:bg-red-50 rounded" title="删除">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const renderEntities = () => (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="font-semibold text-gray-900 mb-4">创建实体</h3>
        <EntityForm onSubmit={handleCreateEntity} />
      </div>

      <div className="lg:col-span-2 bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">实体列表</h3>
          <span className="text-sm text-gray-500">{entities.length} 个实体</span>
        </div>
        
        <div className="space-y-2 max-h-[500px] overflow-auto">
          {entities.map((entity) => (
            <div key={entity.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900">{entity.name}</span>
                  <span className={`px-2 py-0.5 text-xs rounded ${
                    entity.type === 'class' ? 'bg-purple-100 text-purple-700' :
                    entity.type === 'property' ? 'bg-blue-100 text-blue-700' :
                    'bg-green-100 text-green-700'
                  }`}>
                    {entity.type}
                  </span>
                </div>
                {entity.description && (
                  <p className="text-sm text-gray-500 mt-1">{entity.description}</p>
                )}
              </div>
              <button onClick={() => handleDeleteEntity(entity.id)} className="p-2 text-red-500 hover:bg-red-50 rounded">
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  const renderRelations = () => (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="font-semibold text-gray-900 mb-4">创建关系</h3>
        <RelationForm onSubmit={handleCreateRelation} entities={entities} />
      </div>

      <div className="lg:col-span-2 bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">关系列表</h3>
          <span className="text-sm text-gray-500">{relations.length} 个关系</span>
        </div>
        
        <div className="space-y-2 max-h-[500px] overflow-auto">
          {relations.map((relation) => (
            <div key={relation.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900">{getEntityName(relation.source_id)}</span>
                <ChevronRight size={16} className="text-blue-600" />
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">{relation.relation_type}</span>
                <ChevronRight size={16} className="text-blue-600" />
                <span className="font-medium text-gray-900">{getEntityName(relation.target_id)}</span>
                <span className="text-xs text-gray-400">({(relation.confidence * 100).toFixed(0)}%)</span>
              </div>
              <button onClick={() => handleDeleteRelation(relation.id)} className="p-2 text-red-500 hover:bg-red-50 rounded">
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  const renderReasoning = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Brain size={20} className="text-purple-600" />
          推理查询
        </h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">查询问题</label>
            <textarea
              value={reasoningQuery}
              onChange={(e) => setReasoningQuery(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
              rows={4}
              placeholder="例如：供应商A供应哪些产品？客户订单中包含哪些商品？"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">推理类型</label>
            <select
              value={reasoningType}
              onChange={(e) => setReasoningType(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="deductive">演绎推理 - 从规则推导结论</option>
              <option value="inductive">归纳推理 - 从实例发现模式</option>
              <option value="causal">因果推理 - 分析因果关系</option>
              <option value="analogical">类比推理 - 相似性推理</option>
            </select>
          </div>

          <button 
            onClick={handleReasoning}
            disabled={!reasoningQuery.trim() || reasoningLoading}
            className="w-full btn btn-primary flex items-center justify-center gap-2"
          >
            {reasoningLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                推理中...
              </>
            ) : (
              <>
                <Play size={18} />
                执行推理
              </>
            )}
          </button>
        </div>

        <div className="mt-6 p-4 bg-purple-50 rounded-lg">
          <h4 className="text-sm font-medium text-purple-900 mb-2">推理类型说明</h4>
          <ul className="text-sm text-purple-700 space-y-1">
            <li>• <strong>演绎推理：</strong>基于已知规则推导必然结论</li>
            <li>• <strong>归纳推理：</strong>从大量实例中总结规律</li>
            <li>• <strong>因果推理：</strong>识别事件间的因果关系</li>
            <li>• <strong>类比推理：</strong>基于相似性进行推断</li>
          </ul>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Sparkles size={20} className="text-yellow-500" />
          推理结果
        </h3>

        {!reasoningResult ? (
          <div className="text-center py-12 text-gray-500">
            <Brain size={48} className="mx-auto mb-4 text-gray-300" />
            <p>输入问题并执行推理</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="text-sm text-gray-500">查询</label>
              <p className="font-medium text-gray-900">{reasoningResult.query}</p>
            </div>

            <div>
              <label className="text-sm text-gray-500">答案</label>
              <p className="text-gray-700 bg-gray-50 p-3 rounded-lg">{reasoningResult.answer}</p>
            </div>

            <div>
              <label className="text-sm text-gray-500 mb-2 block">置信度</label>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-purple-600 h-2 rounded-full transition-all"
                    style={{ width: `${reasoningResult.confidence * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium">{(reasoningResult.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>

            <div>
              <label className="text-sm text-gray-500 mb-2 block">推理链</label>
              <div className="space-y-2">
                {reasoningResult.reasoning_chain.map((step, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className="w-6 h-6 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center text-xs font-medium">{i + 1}</span>
                    <span className="text-gray-700">{step}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label className="text-sm text-gray-500 mb-2 block">相关实体</label>
              <div className="flex flex-wrap gap-2">
                {reasoningResult.related_entities.map((entity, i) => (
                  <span key={i} className="px-2 py-1 bg-blue-100 text-blue-700 text-sm rounded">{entity}</span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )

  const renderSchema = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4">实体类型配置</h3>
        <div className="space-y-3">
          {['class', 'property', 'individual'].map((type) => (
            <div key={type} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <FileJson className="text-blue-600" size={20} />
                <div>
                  <p className="font-medium text-gray-900">{type === 'class' ? '类' : type === 'property' ? '属性' : '个体'}</p>
                  <p className="text-sm text-gray-500">
                    {entities.filter(e => e.type === type).length} 个实体
                  </p>
                </div>
              </div>
              <button className="p-2 text-gray-600 hover:bg-gray-100 rounded">
                <Settings size={16} />
              </button>
            </div>
          ))}
          <button className="w-full btn btn-secondary flex items-center justify-center gap-2">
            <Plus size={18} /> 添加实体类型
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4">关系类型配置</h3>
        <div className="space-y-3">
          {[...new Set(relations.map(r => r.relation_type))].map((type) => (
            <div key={type} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <Link2 className="text-green-600" size={20} />
                <div>
                  <p className="font-medium text-gray-900">{type}</p>
                  <p className="text-sm text-gray-500">
                    {relations.filter(r => r.relation_type === type).length} 条关系
                  </p>
                </div>
              </div>
              <button className="p-2 text-gray-600 hover:bg-gray-100 rounded">
                <Settings size={16} />
              </button>
            </div>
          ))}
          <button className="w-full btn btn-secondary flex items-center justify-center gap-2">
            <Plus size={18} /> 添加关系类型
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">智能本体数据</h1>
          <p className="text-gray-600 mt-1">本体数据集管理、实体关系配置与推理服务</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchData} className="btn btn-secondary flex items-center gap-2">
            <RefreshCw size={18} />
            刷新
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn btn-primary flex items-center gap-2">
            <Upload size={18} />
            导入数据
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Database className="text-blue-600" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.datasets}</p>
              <p className="text-sm text-gray-500">数据集</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <FileJson className="text-purple-600" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.entities}</p>
              <p className="text-sm text-gray-500">实体</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Network className="text-green-600" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.relations}</p>
              <p className="text-sm text-gray-500">关系</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              <Zap className="text-yellow-600" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.ready}</p>
              <p className="text-sm text-gray-500">就绪数据集</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <tab.icon size={18} />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <>
              {activeTab === 'datasets' && renderDatasets()}
              {activeTab === 'entities' && renderEntities()}
              {activeTab === 'relations' && renderRelations()}
              {activeTab === 'reasoning' && renderReasoning()}
              {activeTab === 'schema' && renderSchema()}
            </>
          )}
        </div>
      </div>

      {showCreateModal && (
        <CreateDatasetModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateDataset}
        />
      )}

      {showEditModal && selectedDataset && (
        <EditDatasetModal
          dataset={selectedDataset}
          onClose={() => { setShowEditModal(false); setSelectedDataset(null) }}
          onSubmit={(data) => handleUpdateDataset(selectedDataset.id, data)}
        />
      )}

      {showPreviewModal && selectedDataset && (
        <PreviewModal
          dataset={selectedDataset}
          entities={entities}
          relations={relations}
          onClose={() => { setShowPreviewModal(false); setSelectedDataset(null) }}
        />
      )}
    </div>
  )
}

function EntityForm({ onSubmit }: { onSubmit: (data: Partial<Entity>) => void }) {
  const [form, setForm] = useState({ name: '', type: 'class', description: '' })

  const handleSubmit = () => {
    if (!form.name) return
    onSubmit(form)
    setForm({ name: '', type: 'class', description: '' })
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm text-gray-600 mb-1">名称</label>
        <input
          type="text"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="w-full px-3 py-2 border rounded-lg"
          placeholder="实体名称"
        />
      </div>
      <div>
        <label className="block text-sm text-gray-600 mb-1">类型</label>
        <select
          value={form.type}
          onChange={(e) => setForm({ ...form, type: e.target.value })}
          className="w-full px-3 py-2 border rounded-lg"
        >
          <option value="class">类</option>
          <option value="property">属性</option>
          <option value="individual">个体</option>
        </select>
      </div>
      <div>
        <label className="block text-sm text-gray-600 mb-1">描述</label>
        <textarea
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          className="w-full px-3 py-2 border rounded-lg"
          rows={2}
        />
      </div>
      <button onClick={handleSubmit} className="w-full btn btn-primary">
        <Plus size={16} className="mr-2" /> 创建实体
      </button>
    </div>
  )
}

function RelationForm({ onSubmit, entities }: { onSubmit: (data: Partial<Relation>) => void; entities: Entity[] }) {
  const [form, setForm] = useState({ source_id: '', target_id: '', relation_type: '' })

  const handleSubmit = () => {
    if (!form.source_id || !form.target_id || !form.relation_type) return
    onSubmit(form)
    setForm({ source_id: '', target_id: '', relation_type: '' })
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm text-gray-600 mb-1">源实体</label>
        <select
          value={form.source_id}
          onChange={(e) => setForm({ ...form, source_id: e.target.value })}
          className="w-full px-3 py-2 border rounded-lg"
        >
          <option value="">选择源实体</option>
          {entities.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-sm text-gray-600 mb-1">关系类型</label>
        <input
          type="text"
          value={form.relation_type}
          onChange={(e) => setForm({ ...form, relation_type: e.target.value })}
          className="w-full px-3 py-2 border rounded-lg"
          placeholder="如: supplies, has, belongs_to"
        />
      </div>
      <div>
        <label className="block text-sm text-gray-600 mb-1">目标实体</label>
        <select
          value={form.target_id}
          onChange={(e) => setForm({ ...form, target_id: e.target.value })}
          className="w-full px-3 py-2 border rounded-lg"
        >
          <option value="">选择目标实体</option>
          {entities.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
        </select>
      </div>
      <button onClick={handleSubmit} className="w-full btn btn-primary">
        <Link2 size={16} className="mr-2" /> 创建关系
      </button>
    </div>
  )
}

function CreateDatasetModal({ onClose, onSubmit }: { onClose: () => void; onSubmit: (data: Partial<OntologyDataset>) => void }) {
  const [form, setForm] = useState({
    name: '',
    description: '',
    data_type: 'ontology' as const,
    format: 'JSON',
  })

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div className="p-6 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold">创建本体数据集</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
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
              <label className="block text-sm font-medium text-gray-700 mb-1">数据类型</label>
              <select
                value={form.data_type}
                onChange={(e) => setForm({ ...form, data_type: e.target.value as any })}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="ontology">本体</option>
                <option value="knowledge_graph">知识图谱</option>
                <option value="entity_list">实体列表</option>
                <option value="relation_set">关系集</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">格式</label>
              <select
                value={form.format}
                onChange={(e) => setForm({ ...form, format: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="JSON">JSON</option>
                <option value="OWL">OWL</option>
                <option value="RDF">RDF</option>
                <option value="CSV">CSV</option>
              </select>
            </div>
          </div>
        </div>
        <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3 rounded-b-lg">
          <button onClick={onClose} className="btn btn-secondary">取消</button>
          <button onClick={() => onSubmit(form)} className="btn btn-primary">创建</button>
        </div>
      </div>
    </div>
  )
}

function EditDatasetModal({ dataset, onClose, onSubmit }: { dataset: OntologyDataset; onClose: () => void; onSubmit: (data: Partial<OntologyDataset>) => void }) {
  const [form, setForm] = useState({
    name: dataset.name,
    description: dataset.description,
    data_type: dataset.data_type,
    format: dataset.format,
  })

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div className="p-6 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold">编辑数据集</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
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
              <label className="block text-sm font-medium text-gray-700 mb-1">数据类型</label>
              <select
                value={form.data_type}
                onChange={(e) => setForm({ ...form, data_type: e.target.value as any })}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="ontology">本体</option>
                <option value="knowledge_graph">知识图谱</option>
                <option value="entity_list">实体列表</option>
                <option value="relation_set">关系集</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">格式</label>
              <select
                value={form.format}
                onChange={(e) => setForm({ ...form, format: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="JSON">JSON</option>
                <option value="OWL">OWL</option>
                <option value="RDF">RDF</option>
                <option value="CSV">CSV</option>
              </select>
            </div>
          </div>
        </div>
        <div className="px-6 py-4 bg-gray-50 flex justify-end gap-3 rounded-b-lg">
          <button onClick={onClose} className="btn btn-secondary">取消</button>
          <button onClick={() => onSubmit(form)} className="btn btn-primary"><Save size={16} className="mr-2" />保存</button>
        </div>
      </div>
    </div>
  )
}

function PreviewModal({ dataset, entities: entityList, relations, onClose }: { dataset: OntologyDataset; entities: Entity[]; relations: Relation[]; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[80vh] overflow-auto">
        <div className="p-4 border-b flex items-center justify-between sticky top-0 bg-white">
          <h2 className="text-lg font-semibold">{dataset.name}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">类型</p>
              <p className="font-medium">{dataset.data_type}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">格式</p>
              <p className="font-medium">{dataset.format}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">记录数</p>
              <p className="font-medium">{dataset.record_count?.toLocaleString()}</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">文件大小</p>
              <p className="font-medium">{dataset.file_size ? `${(dataset.file_size / 1024).toFixed(2)} KB` : '-'}</p>
            </div>
          </div>

          <div>
            <h3 className="font-medium text-gray-900 mb-3">数据集描述</h3>
            <p className="text-gray-600">{dataset.description}</p>
          </div>

          <div>
            <h3 className="font-medium text-gray-900 mb-3">关联实体 ({entityList.length})</h3>
            <div className="grid grid-cols-3 gap-2">
              {entityList.slice(0, 12).map(e => (
                <div key={e.id} className="p-2 bg-gray-50 rounded text-sm">
                  <span className="font-medium">{e.name}</span>
                  <span className="text-gray-400 text-xs ml-2">({e.type})</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="font-medium text-gray-900 mb-3">关联关系 ({relations.length})</h3>
            <div className="space-y-2">
              {relations.slice(0, 10).map(r => (
                <div key={r.id} className="p-2 bg-gray-50 rounded text-sm flex items-center gap-2">
                  <span>{entityList.find(e => e.id === r.source_id)?.name || r.source_id}</span>
                  <ChevronRight size={14} className="text-blue-600" />
                  <span className="text-blue-600">{r.relation_type}</span>
                  <ChevronRight size={14} className="text-blue-600" />
                  <span>{entityList.find(e => e.id === r.target_id)?.name || r.target_id}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
