import { useState, useEffect } from 'react'
import { Plus, Trash2, Link2, Brain, RefreshCw } from 'lucide-react'
import axios from 'axios'

interface Entity {
  id: string
  name: string
  type: string
  description: string | null
  properties: Record<string, any> | null
  created_at: string
}

interface Relation {
  id: string
  source_id: string
  target_id: string
  relation_type: string
  confidence: number
}

interface Statistics {
  entity_count: number
  relation_count: number
  entity_types: Record<string, number>
}

function Ontology() {
  const [entities, setEntities] = useState<Entity[]>([])
  const [relations, setRelations] = useState<Relation[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'entities' | 'relations' | 'reasoning'>('entities')
  
  // Form states
  const [entityName, setEntityName] = useState('')
  const [entityType, setEntityType] = useState('class')
  const [entityDescription, setEntityDescription] = useState('')
  
  const [sourceId, setSourceId] = useState('')
  const [targetId, setTargetId] = useState('')
  const [relationType, setRelationType] = useState('')
  
  const [query, setQuery] = useState('')
  const [reasoningType, setReasoningType] = useState('deductive')
  const [reasoningResult, setReasoningResult] = useState<any>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [entitiesRes, relationsRes, statsRes] = await Promise.all([
        axios.get('/api/ontology/entities'),
        axios.get('/api/ontology/relations'),
        axios.get('/api/ontology/statistics')
      ])
      setEntities(entitiesRes.data.entities || [])
      setRelations(relationsRes.data.relations || [])
      setStatistics(statsRes.data)
    } catch (error) {
      console.error('Failed to load ontology data:', error)
    } finally {
      setLoading(false)
    }
  }

  const createEntity = async () => {
    if (!entityName.trim()) return
    
    try {
      await axios.post('/api/ontology/entities', {
        name: entityName,
        type: entityType,
        description: entityDescription
      })
      setEntityName('')
      setEntityDescription('')
      loadData()
    } catch (error) {
      console.error('Failed to create entity:', error)
    }
  }

  const deleteEntity = async (id: string) => {
    try {
      await axios.delete(`/api/ontology/entities/${id}`)
      loadData()
    } catch (error) {
      console.error('Failed to delete entity:', error)
    }
  }

  const createRelation = async () => {
    if (!sourceId || !targetId || !relationType) return
    
    try {
      await axios.post('/api/ontology/relations', {
        source_id: sourceId,
        target_id: targetId,
        relation_type: relationType,
        confidence: 1.0
      })
      setSourceId('')
      setTargetId('')
      setRelationType('')
      loadData()
    } catch (error) {
      console.error('Failed to create relation:', error)
    }
  }

  const deleteRelation = async (id: string) => {
    try {
      await axios.delete(`/api/ontology/relations/${id}`)
      loadData()
    } catch (error) {
      console.error('Failed to delete relation:', error)
    }
  }

  const performReasoning = async () => {
    if (!query.trim()) return
    
    try {
      const res = await axios.post('/api/ontology/reasoning', {
        query,
        reasoning_type: reasoningType
      })
      setReasoningResult(res.data.result)
    } catch (error) {
      console.error('Failed to perform reasoning:', error)
    }
  }

  const getEntityName = (id: string) => {
    const entity = entities.find(e => e.id === id)
    return entity ? entity.name : id
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">智能本体引擎</h1>
          <p className="text-gray-500 mt-1">管理本体实体、关系和认知推理</p>
        </div>
        <button onClick={loadData} className="btn btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          刷新
        </button>
      </div>

      {statistics && (
        <div className="grid grid-cols-4 gap-4">
          <div className="card p-4">
            <p className="text-sm text-gray-500">实体总数</p>
            <p className="text-2xl font-bold text-gray-900">{statistics.entity_count}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-500">关系总数</p>
            <p className="text-2xl font-bold text-gray-900">{statistics.relation_count}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-500">类实体</p>
            <p className="text-2xl font-bold text-primary-600">{statistics.entity_types?.class || 0}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-500">推理类型</p>
            <p className="text-2xl font-bold text-accent-600">4种</p>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab('entities')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'entities' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          实体管理
        </button>
        <button
          onClick={() => setActiveTab('relations')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'relations' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          关系管理
        </button>
        <button
          onClick={() => setActiveTab('reasoning')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'reasoning' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          认知推理
        </button>
      </div>

      {activeTab === 'entities' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">创建实体</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">名称</label>
                <input
                  type="text"
                  value={entityName}
                  onChange={(e) => setEntityName(e.target.value)}
                  className="input w-full"
                  placeholder="输入实体名称"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">类型</label>
                <select
                  value={entityType}
                  onChange={(e) => setEntityType(e.target.value)}
                  className="input w-full"
                >
                  <option value="class">类</option>
                  <option value="property">属性</option>
                  <option value="individual">个体</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">描述</label>
                <textarea
                  value={entityDescription}
                  onChange={(e) => setEntityDescription(e.target.value)}
                  className="input w-full"
                  rows={3}
                  placeholder="实体描述（可选）"
                />
              </div>
              <button onClick={createEntity} className="btn btn-primary w-full">
                <Plus className="w-4 h-4 mr-2" />
                创建实体
              </button>
            </div>
          </div>

          <div className="lg:col-span-2 card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">实体列表</h3>
              <span className="text-sm text-gray-500">{entities.length} 个实体</span>
            </div>
            
            {entities.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                暂无实体，请创建第一个实体
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-auto">
                {entities.map((entity) => (
                  <div key={entity.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{entity.name}</span>
                        <span className="px-2 py-0.5 bg-primary-100 text-primary-700 text-xs rounded">
                          {entity.type}
                        </span>
                      </div>
                      {entity.description && (
                        <p className="text-sm text-gray-500 mt-1">{entity.description}</p>
                      )}
                    </div>
                    <button
                      onClick={() => deleteEntity(entity.id)}
                      className="p-2 text-red-500 hover:bg-red-50 rounded"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'relations' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">创建关系</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">源实体</label>
                <select
                  value={sourceId}
                  onChange={(e) => setSourceId(e.target.value)}
                  className="input w-full"
                >
                  <option value="">选择源实体</option>
                  {entities.map((e) => (
                    <option key={e.id} value={e.id}>{e.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">关系类型</label>
                <input
                  type="text"
                  value={relationType}
                  onChange={(e) => setRelationType(e.target.value)}
                  className="input w-full"
                  placeholder="例如: supplies, has, belongs_to"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">目标实体</label>
                <select
                  value={targetId}
                  onChange={(e) => setTargetId(e.target.value)}
                  className="input w-full"
                >
                  <option value="">选择目标实体</option>
                  {entities.map((e) => (
                    <option key={e.id} value={e.id}>{e.name}</option>
                  ))}
                </select>
              </div>
              <button onClick={createRelation} className="btn btn-primary w-full">
                <Link2 className="w-4 h-4 mr-2" />
                创建关系
              </button>
            </div>
          </div>

          <div className="lg:col-span-2 card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">关系列表</h3>
              <span className="text-sm text-gray-500">{relations.length} 个关系</span>
            </div>
            
            {relations.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                暂无关系，请先创建实体再建立关系
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-auto">
                {relations.map((relation) => (
                  <div key={relation.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{getEntityName(relation.source_id)}</span>
                      <span className="text-primary-600">→ {relation.relation_type} →</span>
                      <span className="font-medium">{getEntityName(relation.target_id)}</span>
                      <span className="text-xs text-gray-400">({(relation.confidence * 100).toFixed(0)}%)</span>
                    </div>
                    <button
                      onClick={() => deleteRelation(relation.id)}
                      className="p-2 text-red-500 hover:bg-red-50 rounded"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'reasoning' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">认知推理</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">查询</label>
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="input w-full"
                  rows={4}
                  placeholder="输入您的问题，例如：供应商和产品之间有什么关系？"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">推理类型</label>
                <select
                  value={reasoningType}
                  onChange={(e) => setReasoningType(e.target.value)}
                  className="input w-full"
                >
                  <option value="deductive">演绎推理</option>
                  <option value="inductive">归纳推理</option>
                  <option value="causal">因果推理</option>
                  <option value="counterfactual">反事实推理</option>
                </select>
              </div>
              <button onClick={performReasoning} className="btn btn-primary w-full">
                <Brain className="w-4 h-4 mr-2" />
                执行推理
              </button>
            </div>

            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-700 mb-2">推理类型说明</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li><strong>演绎推理：</strong>从一般到特殊，基于已知规则推导结论</li>
                <li><strong>归纳推理：</strong>从特殊到一般，从实例中发现模式</li>
                <li><strong>因果推理：</strong>分析因果关系，识别原因和结果</li>
                <li><strong>反事实推理：</strong>假设性推理，探索"如果...会怎样"</li>
              </ul>
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">推理结果</h3>
            
            {!reasoningResult ? (
              <div className="text-center py-8 text-gray-500">
                输入查询并点击"执行推理"查看结果
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">置信度:</span>
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-primary-600 h-2 rounded-full"
                      style={{ width: `${reasoningResult.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">{(reasoningResult.confidence * 100).toFixed(0)}%</span>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">解释</h4>
                  <p className="text-gray-600">{reasoningResult.explanation}</p>
                </div>

                {reasoningResult.conclusions && reasoningResult.conclusions.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">结论</h4>
                    <ul className="space-y-2">
                      {reasoningResult.conclusions.map((c: any, i: number) => (
                        <li key={i} className="p-3 bg-primary-50 rounded-lg">
                          <p className="text-gray-700">{c.content}</p>
                          {c.confidence && (
                            <p className="text-xs text-gray-500 mt-1">
                              置信度: {(c.confidence * 100).toFixed(0)}%
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {reasoningResult.reasoning_chain && reasoningResult.reasoning_chain.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-700 mb-2">推理链</h4>
                    <div className="space-y-2">
                      {reasoningResult.reasoning_chain.map((step: any, i: number) => (
                        <div key={i} className="flex items-center gap-2 text-sm">
                          <span className="w-6 h-6 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center text-xs">{i + 1}</span>
                          <span className="text-gray-600">{JSON.stringify(step)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Ontology
