import { useState } from 'react'
import { 
  Plus, Search, Settings, Trash2,
  Play, CheckCircle, XCircle, AlertTriangle, Zap,
  DollarSign, BarChart3, Key, Lock,
  RefreshCw, Eye, EyeOff, TestTube, Copy
} from 'lucide-react'
import axios from 'axios'

interface ModelConfig {
  id: number
  configName: string
  provider: string
  modelType: string
  baseUrl: string
  apiKey: string
  apiVersion?: string
  timeoutMs: number
  maxTokens: number
  temperature: number
  isDefault: boolean
  isActive: boolean
  status?: 'healthy' | 'warning' | 'error'
  responseTime?: number
  totalCalls?: number
  totalTokens?: number
  totalCost?: number
  availability?: number
}

interface TestResult {
  connected: boolean
  response: string
  latency: number
  tokensUsed: number
  error?: string
}

const providers = [
  { value: 'OPENAI', label: 'OpenAI', baseUrl: 'https://api.openai.com/v1' },
  { value: 'AZURE', label: 'Azure OpenAI', baseUrl: '' },
  { value: 'ANTHROPIC', label: 'Anthropic Claude', baseUrl: 'https://api.anthropic.com/v1' },
  { value: 'GOOGLE', label: 'Google AI', baseUrl: 'https://generativelanguage.googleapis.com/v1' },
  { value: 'CUSTOM', label: '自定义服务', baseUrl: '' },
]

const mockConfigs: ModelConfig[] = [
  {
    id: 1,
    configName: 'GPT-4 主连接',
    provider: 'OPENAI',
    modelType: 'CHAT',
    baseUrl: 'https://api.openai.com/v1',
    apiKey: 'sk-••••••••••••••••',
    timeoutMs: 30000,
    maxTokens: 4096,
    temperature: 0.7,
    isDefault: true,
    isActive: true,
    status: 'healthy',
    responseTime: 120,
    totalCalls: 2450,
    totalTokens: 1250000,
    totalCost: 12.50,
    availability: 99.8
  },
  {
    id: 2,
    configName: 'Claude-3 连接',
    provider: 'ANTHROPIC',
    modelType: 'CHAT',
    baseUrl: 'https://api.anthropic.com/v1',
    apiKey: 'sk-ant-••••••••••',
    timeoutMs: 30000,
    maxTokens: 4096,
    temperature: 0.7,
    isDefault: false,
    isActive: true,
    status: 'healthy',
    responseTime: 180,
    totalCalls: 1780,
    totalTokens: 890000,
    totalCost: 8.90,
    availability: 99.5
  },
]

function MCP() {
  const [configs, setConfigs] = useState<ModelConfig[]>(mockConfigs)
  const [selectedConfig, setSelectedConfig] = useState<ModelConfig>(mockConfigs[0])
  const [showAddModal, setShowAddModal] = useState(false)
  const [showTestModal, setShowTestModal] = useState(false)
  const [showApiKey, setShowApiKey] = useState(false)
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [isTesting, setIsTesting] = useState(false)
  const [testPrompt, setTestPrompt] = useState('Hello, world!')
  const [activeTab, setActiveTab] = useState<'overview' | 'config' | 'stats'>('overview')
  
  const [newConfig, setNewConfig] = useState<Partial<ModelConfig>>({
    configName: '',
    provider: 'OPENAI',
    modelType: 'CHAT',
    baseUrl: 'https://api.openai.com/v1',
    apiKey: '',
    timeoutMs: 30000,
    maxTokens: 4096,
    temperature: 0.7,
    isDefault: false
  })

  const getStatusInfo = (status?: string) => {
    switch (status) {
      case 'healthy': return { color: 'bg-green-500', text: '连接正常', textColor: 'text-green-600', icon: CheckCircle }
      case 'warning': return { color: 'bg-yellow-500', text: '响应较慢', textColor: 'text-yellow-600', icon: AlertTriangle }
      default: return { color: 'bg-red-500', text: '连接失败', textColor: 'text-red-600', icon: XCircle }
    }
  }

  const handleTestConnection = async () => {
    setIsTesting(true)
    try {
      const response = await axios.post(`/api/model-configs/${selectedConfig.id}/test`, {
        testPrompt
      })
      setTestResult(response.data.data)
    } catch (error: any) {
      setTestResult({
        connected: false,
        response: '',
        latency: 0,
        tokensUsed: 0,
        error: error.response?.data?.message || error.message
      })
    } finally {
      setIsTesting(false)
    }
  }

  const handleAddConfig = async () => {
    try {
      const response = await axios.post('/api/model-configs', newConfig)
      setConfigs([...configs, response.data.data])
      setShowAddModal(false)
      setNewConfig({
        configName: '',
        provider: 'OPENAI',
        modelType: 'CHAT',
        baseUrl: 'https://api.openai.com/v1',
        apiKey: '',
        timeoutMs: 30000,
        maxTokens: 4096,
        temperature: 0.7,
        isDefault: false
      })
    } catch (error) {
      console.error('Failed to add config:', error)
    }
  }

  const mockDailyStats = [
    { date: '2026-03-17', callCount: 120, tokenCount: 45000, cost: 0.45 },
    { date: '2026-03-16', callCount: 145, tokenCount: 52000, cost: 0.52 },
    { date: '2026-03-15', callCount: 98, tokenCount: 38000, cost: 0.38 },
    { date: '2026-03-14', callCount: 167, tokenCount: 61000, cost: 0.61 },
    { date: '2026-03-13', callCount: 134, tokenCount: 49000, cost: 0.49 },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">模型连接</h1>
        <div className="flex items-center gap-3">
          <button className="btn btn-secondary">连接模板</button>
          <button 
            onClick={() => setShowAddModal(true)}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            添加模型配置
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="text" placeholder="搜索配置..." className="input pl-9 text-sm" />
            </div>
          </div>

          <div className="space-y-2">
            {configs.map((config) => {
              const statusInfo = getStatusInfo(config.status)
              const StatusIcon = statusInfo.icon
              return (
                <div
                  key={config.id}
                  onClick={() => setSelectedConfig(config)}
                  className={`p-4 rounded-lg cursor-pointer transition-colors ${
                    selectedConfig.id === config.id
                      ? 'bg-primary-50 border border-primary-200'
                      : 'hover:bg-gray-50 border border-transparent'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <StatusIcon className={`w-4 h-4 ${statusInfo.textColor}`} />
                      <span className="font-medium text-gray-900">{config.configName}</span>
                    </div>
                    {config.isDefault && (
                      <span className="px-2 py-0.5 bg-primary-100 text-primary-700 text-xs rounded">默认</span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                    <span>{config.provider}</span>
                    <span>•</span>
                    <span>{config.totalCalls?.toLocaleString()}次调用</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">{selectedConfig.configName}</h2>
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setShowTestModal(true)}
                  className="btn btn-secondary flex items-center gap-2"
                >
                  <TestTube className="w-4 h-4" />
                  测试连接
                </button>
                <button className="p-2 hover:bg-gray-100 rounded-lg">
                  <Settings className="w-4 h-4 text-gray-500" />
                </button>
                <button className="p-2 hover:bg-red-50 rounded-lg">
                  <Trash2 className="w-4 h-4 text-red-500" />
                </button>
              </div>
            </div>

            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setActiveTab('overview')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeTab === 'overview' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                概览
              </button>
              <button
                onClick={() => setActiveTab('config')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeTab === 'config' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                配置详情
              </button>
              <button
                onClick={() => setActiveTab('stats')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeTab === 'stats' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                调用统计
              </button>
            </div>

            {activeTab === 'overview' && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500">状态</p>
                    <p className={`text-lg font-semibold ${getStatusInfo(selectedConfig.status).textColor}`}>
                      {getStatusInfo(selectedConfig.status).text}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500">响应时间</p>
                    <p className="text-lg font-semibold text-gray-900">{selectedConfig.responseTime}ms</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500">今日调用</p>
                    <p className="text-lg font-semibold text-gray-900">{selectedConfig.totalCalls?.toLocaleString()}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500">可用性</p>
                    <p className="text-lg font-semibold text-gray-900">{selectedConfig.availability}%</p>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-500 mb-2">端点地址</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-sm text-gray-700 bg-white px-3 py-1 rounded border">
                      {selectedConfig.baseUrl}
                    </code>
                    <button className="p-1 text-gray-400 hover:text-gray-600">
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </>
            )}

            {activeTab === 'config' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">提供商</label>
                    <input type="text" value={selectedConfig.provider} disabled className="input w-full bg-gray-50" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">模型类型</label>
                    <input type="text" value={selectedConfig.modelType} disabled className="input w-full bg-gray-50" />
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 relative">
                      <input 
                        type={showApiKey ? 'text' : 'password'}
                        value={selectedConfig.apiKey} 
                        disabled 
                        className="input w-full bg-gray-50 pr-10"
                      />
                      <Lock className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    </div>
                    <button 
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="p-2 text-gray-400 hover:text-gray-600"
                    >
                      {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    <Key className="w-3 h-3 inline mr-1" />
                    API Key 已加密存储
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">超时时间</label>
                    <input type="text" value={`${selectedConfig.timeoutMs}ms`} disabled className="input w-full bg-gray-50" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">最大Token</label>
                    <input type="text" value={selectedConfig.maxTokens} disabled className="input w-full bg-gray-50" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">温度</label>
                    <input type="text" value={selectedConfig.temperature} disabled className="input w-full bg-gray-50" />
                  </div>
                </div>

                {selectedConfig.apiVersion && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">API版本</label>
                    <input type="text" value={selectedConfig.apiVersion} disabled className="input w-full bg-gray-50" />
                  </div>
                )}
              </div>
            )}

            {activeTab === 'stats' && (
              <div className="space-y-6">
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gradient-to-br from-primary-50 to-primary-100 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-primary-600 mb-2">
                      <Zap className="w-5 h-5" />
                      <span className="text-sm font-medium">总调用次数</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">{selectedConfig.totalCalls?.toLocaleString()}</p>
                  </div>
                  <div className="bg-gradient-to-br from-accent-50 to-accent-100 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-accent-600 mb-2">
                      <BarChart3 className="w-5 h-5" />
                      <span className="text-sm font-medium">Token消耗</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">{selectedConfig.totalTokens?.toLocaleString()}</p>
                  </div>
                  <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-green-600 mb-2">
                      <DollarSign className="w-5 h-5" />
                      <span className="text-sm font-medium">预估费用</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">${selectedConfig.totalCost?.toFixed(2)}</p>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-3">每日调用统计</h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="space-y-2">
                      {mockDailyStats.map((stat, idx) => (
                        <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-200 last:border-0">
                          <span className="text-sm text-gray-600">{stat.date}</span>
                          <div className="flex items-center gap-6">
                            <span className="text-sm text-gray-500">{stat.callCount} 次</span>
                            <span className="text-sm text-gray-500">{stat.tokenCount.toLocaleString()} tokens</span>
                            <span className="text-sm font-medium text-gray-900">${stat.cost.toFixed(2)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">添加模型配置</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">配置名称</label>
                <input
                  type="text"
                  value={newConfig.configName}
                  onChange={(e) => setNewConfig({...newConfig, configName: e.target.value})}
                  placeholder="如: GPT-4 主连接"
                  className="input w-full"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">提供商</label>
                  <select
                    value={newConfig.provider}
                    onChange={(e) => {
                      const provider = providers.find(p => p.value === e.target.value)
                      setNewConfig({
                        ...newConfig, 
                        provider: e.target.value,
                        baseUrl: provider?.baseUrl || newConfig.baseUrl
                      })
                    }}
                    className="input w-full"
                  >
                    {providers.map(p => (
                      <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">模型类型</label>
                  <select
                    value={newConfig.modelType}
                    onChange={(e) => setNewConfig({...newConfig, modelType: e.target.value})}
                    className="input w-full"
                  >
                    <option value="CHAT">对话模型</option>
                    <option value="COMPLETION">补全模型</option>
                    <option value="EMBEDDING">嵌入模型</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
                <input
                  type="text"
                  value={newConfig.baseUrl}
                  onChange={(e) => setNewConfig({...newConfig, baseUrl: e.target.value})}
                  placeholder="https://api.openai.com/v1"
                  className="input w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <input
                  type="password"
                  value={newConfig.apiKey}
                  onChange={(e) => setNewConfig({...newConfig, apiKey: e.target.value})}
                  placeholder="sk-..."
                  className="input w-full"
                />
                <p className="text-xs text-gray-500 mt-1">
                  <Lock className="w-3 h-3 inline mr-1" />
                  API Key 将被加密存储
                </p>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">超时(ms)</label>
                  <input
                    type="number"
                    value={newConfig.timeoutMs}
                    onChange={(e) => setNewConfig({...newConfig, timeoutMs: parseInt(e.target.value)})}
                    className="input w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">最大Token</label>
                  <input
                    type="number"
                    value={newConfig.maxTokens}
                    onChange={(e) => setNewConfig({...newConfig, maxTokens: parseInt(e.target.value)})}
                    className="input w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">温度</label>
                  <input
                    type="number"
                    step="0.1"
                    value={newConfig.temperature}
                    onChange={(e) => setNewConfig({...newConfig, temperature: parseFloat(e.target.value)})}
                    className="input w-full"
                  />
                </div>
              </div>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={newConfig.isDefault}
                  onChange={(e) => setNewConfig({...newConfig, isDefault: e.target.checked})}
                  className="rounded"
                />
                <span className="text-sm text-gray-700">设为默认配置</span>
              </label>
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowAddModal(false)} className="btn btn-secondary">取消</button>
              <button onClick={handleAddConfig} className="btn btn-primary">添加配置</button>
            </div>
          </div>
        </div>
      )}

      {showTestModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">测试连接 - {selectedConfig.configName}</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">测试提示词</label>
                <textarea
                  value={testPrompt}
                  onChange={(e) => setTestPrompt(e.target.value)}
                  placeholder="输入测试文本..."
                  className="input w-full h-24"
                />
              </div>

              {testResult && (
                <div className={`p-4 rounded-lg ${testResult.connected ? 'bg-green-50' : 'bg-red-50'}`}>
                  <div className="flex items-center gap-2 mb-2">
                    {testResult.connected ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-600" />
                    )}
                    <span className={`font-medium ${testResult.connected ? 'text-green-700' : 'text-red-700'}`}>
                      {testResult.connected ? '连接成功' : '连接失败'}
                    </span>
                  </div>
                  
                  {testResult.connected ? (
                    <div className="space-y-2">
                      <p className="text-sm text-gray-600">
                        <strong>响应:</strong> {testResult.response}
                      </p>
                      <div className="flex gap-4 text-sm text-gray-500">
                        <span>延迟: {testResult.latency}ms</span>
                        <span>Token: {testResult.tokensUsed}</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-red-600">{testResult.error}</p>
                  )}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => { setShowTestModal(false); setTestResult(null); }} className="btn btn-secondary">关闭</button>
              <button 
                onClick={handleTestConnection}
                disabled={isTesting}
                className="btn btn-primary flex items-center gap-2"
              >
                {isTesting ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                测试连接
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MCP
