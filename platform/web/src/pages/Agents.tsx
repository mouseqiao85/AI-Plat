import { useState } from 'react'
import { Plus, Search, Play, Square, Trash2, Settings } from 'lucide-react'

const agentsList = [
  { id: 1, name: '客服智能代理', status: 'running', skills: 8, processed: 156, cpu: 23, memory: 45 },
  { id: 2, name: '销售助手代理', status: 'running', skills: 6, processed: 42, cpu: 18, memory: 32 },
  { id: 3, name: '数据分析代理', status: 'stopped', skills: 12, processed: 0, cpu: 0, memory: 0 },
  { id: 4, name: '报告生成代理', status: 'running', skills: 5, processed: 28, cpu: 15, memory: 28 },
]

function Agents() {
  const [selectedAgent, setSelectedAgent] = useState(agentsList[0])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-success-500'
      case 'stopped': return 'bg-red-500'
      case 'warning': return 'bg-yellow-500'
      default: return 'bg-gray-400'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">自主代理系统</h1>
        <div className="flex items-center gap-3">
          <button className="btn btn-secondary">模板库</button>
          <button className="btn btn-secondary">技能市场</button>
          <button className="btn btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" />
            创建新代理
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {agentsList.map((agent) => (
          <div
            key={agent.id}
            onClick={() => setSelectedAgent(agent)}
            className={`card cursor-pointer transition-all ${
              selectedAgent.id === agent.id ? 'ring-2 ring-primary-500' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                agent.status === 'running' ? 'bg-success-500/10' : 'bg-gray-100'
              }`}>
                <div className={`w-3 h-3 rounded-full ${getStatusColor(agent.status)}`} />
              </div>
              <span className={`text-sm font-medium ${
                agent.status === 'running' ? 'text-success-600' : 'text-gray-500'
              }`}>
                {agent.status === 'running' ? '运行中' : '停止'}
              </span>
            </div>
            <h3 className="font-medium text-gray-900">{agent.name}</h3>
            <p className="text-sm text-gray-500 mt-1">{agent.skills}个技能</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="text" placeholder="搜索代理..." className="input pl-9 text-sm" />
            </div>
          </div>

          <div className="space-y-2">
            {agentsList.map((agent) => (
              <div
                key={agent.id}
                onClick={() => setSelectedAgent(agent)}
                className={`p-4 rounded-lg cursor-pointer transition-colors ${
                  selectedAgent.id === agent.id
                    ? 'bg-primary-50 border border-primary-200'
                    : 'hover:bg-gray-50 border border-transparent'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${getStatusColor(agent.status)}`} />
                    <span className="font-medium text-gray-900">{agent.name}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                  <span>技能: {agent.skills}个</span>
                  <span>今日处理: {agent.processed}个</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900">{selectedAgent.name}</h2>
            <div className="flex items-center gap-2">
              <button className="p-2 hover:bg-gray-100 rounded-lg">
                <Settings className="w-4 h-4 text-gray-500" />
              </button>
              {selectedAgent.status === 'running' ? (
                <button className="btn btn-secondary flex items-center gap-2 text-red-600">
                  <Square className="w-4 h-4" />
                  停止
                </button>
              ) : (
                <button className="btn btn-primary flex items-center gap-2">
                  <Play className="w-4 h-4" />
                  启动
                </button>
              )}
              <button className="p-2 hover:bg-red-50 rounded-lg">
                <Trash2 className="w-4 h-4 text-red-500" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-500">状态</p>
              <p className={`text-lg font-semibold ${
                selectedAgent.status === 'running' ? 'text-success-600' : 'text-red-500'
              }`}>
                {selectedAgent.status === 'running' ? '运行中' : '已停止'}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-500">技能数量</p>
              <p className="text-lg font-semibold text-gray-900">{selectedAgent.skills}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-500">今日处理</p>
              <p className="text-lg font-semibold text-gray-900">{selectedAgent.processed}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-500">CPU使用</p>
              <p className="text-lg font-semibold text-gray-900">{selectedAgent.cpu}%</p>
            </div>
          </div>

          <div className="border-t pt-6">
            <h3 className="text-sm font-medium text-gray-700 mb-4">已安装技能</h3>
            <div className="flex flex-wrap gap-2">
              {['会话管理', '问题分类', '知识检索', '回复生成', '情感分析', '意图识别', '多轮对话', '智能推荐'].slice(0, selectedAgent.skills).map((skill, idx) => (
                <span key={idx} className="px-3 py-1 bg-primary-50 text-primary-600 rounded-full text-sm">
                  {skill}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Agents
