import { useState, useEffect } from 'react'
import { Bot, CheckCircle, TrendingUp, Activity, Brain, Zap, ArrowUpRight } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import axios from 'axios'

interface PlatformStatus {
  platform_id: string
  version: string
  status: string
  modules: {
    users: { count: number }
    ontology: { initialized: boolean; entities: number }
    agents: { initialized: boolean; count: number }
    vibecoding: { status: string }
  }
}

interface DashboardMetrics {
  roi: { current: number; change: number }
  tasks: { completed: number; pending: number; running: number }
  agents: { total: number; running: number; stopped: number }
}

function Dashboard() {
  const [status, setStatus] = useState<PlatformStatus | null>(null)
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000) // 每30秒刷新
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [statusRes, metricsRes] = await Promise.all([
        axios.get('/api/status'),
        axios.get('/api/metrics/dashboard')
      ])
      setStatus(statusRes.data)
      setMetrics(metricsRes.data)
      setError('')
    } catch (err) {
      setError('加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  const roiData = [
    { name: '周一', value: 65 },
    { name: '周二', value: 78 },
    { name: '周三', value: 92 },
    { name: '周四', value: 85 },
    { name: '周五', value: 110 },
    { name: '周六', value: 125 },
    { name: '周日', value: metrics?.roi.current || 127 },
  ]

  const taskData = metrics ? [
    { name: '已完成', value: metrics.tasks.completed, color: '#10b981' },
    { name: '运行中', value: metrics.tasks.running, color: '#2563eb' },
    { name: '待处理', value: metrics.tasks.pending, color: '#f59e0b' },
  ] : []

  const recentActivities = [
    { id: 1, text: '数据分析代理成功处理了数据集', time: '10分钟前', type: 'success', icon: Bot },
    { id: 2, text: '本体引擎添加了新实体: Product', time: '1小时前', type: 'info', icon: Brain },
    { id: 3, text: 'Vibecoding生成了新的API端点', time: '2小时前', type: 'success', icon: Zap },
    { id: 4, text: '系统性能优化建议已生成', time: '3小时前', type: 'warning', icon: Activity },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500">{error}</p>
        <button onClick={loadData} className="btn btn-primary mt-4">重试</button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 顶部欢迎区 */}
      <div className="bg-gradient-to-r from-primary-600 to-accent-600 rounded-2xl p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">NexusMind OS</h1>
            <p className="text-primary-100 mt-1">AI-Plat Platform v{status?.version}</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm text-primary-100">平台状态</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                <span className="font-medium">{status?.status === 'running' ? '运行中' : '停止'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">代理数量</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{status?.modules.agents.count || 0}</p>
              <div className="flex items-center gap-1 mt-2 text-sm text-success-600">
                <ArrowUpRight className="w-4 h-4" />
                <span>{metrics?.agents.running || 0} 运行中</span>
              </div>
            </div>
            <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
              <Bot className="w-6 h-6 text-primary-600" />
            </div>
          </div>
        </div>

        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">本体实体</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{status?.modules.ontology.entities || 0}</p>
              <div className="flex items-center gap-1 mt-2 text-sm text-primary-600">
                <Brain className="w-4 h-4" />
                <span>知识图谱</span>
              </div>
            </div>
            <div className="w-12 h-12 bg-accent-100 rounded-xl flex items-center justify-center">
              <Brain className="w-6 h-6 text-accent-600" />
            </div>
          </div>
        </div>

        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">任务完成</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{metrics?.tasks.completed || 0}</p>
              <div className="flex items-center gap-1 mt-2 text-sm text-success-600">
                <CheckCircle className="w-4 h-4" />
                <span>{metrics?.tasks.pending || 0} 待处理</span>
              </div>
            </div>
            <div className="w-12 h-12 bg-success-500/10 rounded-xl flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-success-600" />
            </div>
          </div>
        </div>

        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">ROI增长</p>
              <p className="text-2xl font-bold text-success-600 mt-1">+{metrics?.roi.current || 0}%</p>
              <div className="flex items-center gap-1 mt-2 text-sm text-gray-500">
                <TrendingUp className="w-4 h-4" />
                <span>本月</span>
              </div>
            </div>
            <div className="w-12 h-12 bg-success-500/10 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-success-600" />
            </div>
          </div>
        </div>
      </div>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">ROI 趋势</h3>
            <select className="text-sm border-gray-200 rounded-lg px-3 py-1">
              <option>最近7天</option>
              <option>最近30天</option>
              <option>最近90天</option>
            </select>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={roiData}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
                <YAxis stroke="#9ca3af" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'white', 
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px'
                  }} 
                />
                <Area 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#2563eb" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorValue)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">任务分布</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={taskData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {taskData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-4 mt-4">
            {taskData.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></span>
                <span className="text-sm text-gray-600">{item.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 底部卡片 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 最近活动 */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">最近活动</h3>
            <button className="text-sm text-primary-600 hover:text-primary-700">查看全部</button>
          </div>
          <div className="space-y-4">
            {recentActivities.map((activity) => {
              const Icon = activity.icon
              return (
                <div key={activity.id} className="flex items-start gap-3 p-3 hover:bg-gray-50 rounded-lg transition-colors">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    activity.type === 'success' ? 'bg-success-500/10' :
                    activity.type === 'warning' ? 'bg-yellow-500/10' : 'bg-primary-100'
                  }`}>
                    <Icon className={`w-5 h-5 ${
                      activity.type === 'success' ? 'text-success-600' :
                      activity.type === 'warning' ? 'text-yellow-600' : 'text-primary-600'
                    }`} />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{activity.text}</p>
                    <p className="text-xs text-gray-400 mt-1">{activity.time}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* 快速操作 */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">快速操作</h3>
          <div className="grid grid-cols-2 gap-4">
            <button className="p-4 border border-gray-200 rounded-xl hover:border-primary-300 hover:bg-primary-50 transition-all text-left group">
              <Bot className="w-8 h-8 text-primary-600 mb-2 group-hover:scale-110 transition-transform" />
              <p className="font-medium text-gray-900">创建代理</p>
              <p className="text-sm text-gray-500">部署新的AI代理</p>
            </button>
            
            <button className="p-4 border border-gray-200 rounded-xl hover:border-accent-300 hover:bg-accent-50 transition-all text-left group">
              <Brain className="w-8 h-8 text-accent-600 mb-2 group-hover:scale-110 transition-transform" />
              <p className="font-medium text-gray-900">添加实体</p>
              <p className="text-sm text-gray-500">扩展知识图谱</p>
            </button>
            
            <button className="p-4 border border-gray-200 rounded-xl hover:border-success-300 hover:bg-success-50 transition-all text-left group">
              <Zap className="w-8 h-8 text-success-600 mb-2 group-hover:scale-110 transition-transform" />
              <p className="font-medium text-gray-900">生成代码</p>
              <p className="text-sm text-gray-500">Vibecoding助手</p>
            </button>
            
            <button className="p-4 border border-gray-200 rounded-xl hover:border-yellow-300 hover:bg-yellow-50 transition-all text-left group">
              <Activity className="w-8 h-8 text-yellow-600 mb-2 group-hover:scale-110 transition-transform" />
              <p className="font-medium text-gray-900">查看监控</p>
              <p className="text-sm text-gray-500">系统性能指标</p>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
