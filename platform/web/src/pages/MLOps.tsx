import React, { useState, useEffect } from 'react'

interface Deployment {
  deployment_id: string
  deployment_name: string
  status: string
  replicas: number
  endpoint_url: string
  created_at: string
}

interface Evaluation {
  evaluation_id: string
  model_id: string
  evaluation_type: string
  status: string
  summary: {
    pass_rate: number
  }
}

interface Dataset {
  dataset_id: string
  name: string
  data_type: string
  format: string
  size: string
  records: number
  status: string
}

export const MLOps: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'datasets' | 'deployment' | 'evaluation'>('datasets')
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [deployments, setDeployments] = useState<Deployment[]>([])
  const [evaluations, setEvaluations] = useState<Evaluation[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchData()
  }, [activeTab])

  const fetchData = async () => {
    setLoading(true)
    try {
      if (activeTab === 'datasets') {
        const res = await fetch('/api/mlops/datasets')
        const data = await res.json()
        setDatasets(data.datasets || [])
      } else if (activeTab === 'deployment') {
        const res = await fetch('/api/mlops/deployments')
        const data = await res.json()
        setDeployments(data.deployments || [])
      } else if (activeTab === 'evaluation') {
        const res = await fetch('/api/mlops/evaluations')
        const data = await res.json()
        setEvaluations(data.evaluations || [])
      }
    } catch (error) {
      console.error('Failed to fetch data:', error)
    }
    setLoading(false)
  }

  const renderStatusBadge = (status: string) => {
    const statusColors: Record<string, string> = {
      running: 'bg-green-100 text-green-800',
      completed: 'bg-blue-100 text-blue-800',
      pending: 'bg-yellow-100 text-yellow-800',
      failed: 'bg-red-100 text-red-800',
      stopped: 'bg-gray-100 text-gray-800',
      ready: 'bg-green-100 text-green-800',
    }
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[status] || 'bg-gray-100 text-gray-800'}`}>
        {status}
      </span>
    )
  }

  const renderDatasets = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">数据集管理</h3>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + 新建数据集
        </button>
      </div>
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
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {datasets.map((dataset) => (
              <tr key={dataset.dataset_id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {dataset.name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {dataset.data_type}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {dataset.format}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {dataset.size}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {dataset.records.toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {renderStatusBadge(dataset.status)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <button className="text-blue-600 hover:text-blue-900 mr-3">查看</button>
                  <button className="text-green-600 hover:text-green-900 mr-3">验证</button>
                  <button className="text-red-600 hover:text-red-900">删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const renderDeployment = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">模型部署</h3>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + 新建部署
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {deployments.map((deployment) => (
          <div key={deployment.deployment_id} className="bg-white rounded-lg shadow p-4">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="font-semibold text-gray-900">{deployment.deployment_name}</h4>
                <p className="text-sm text-gray-500 mt-1">{deployment.deployment_id}</p>
              </div>
              {renderStatusBadge(deployment.status)}
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">副本数</span>
                <span className="font-medium">{deployment.replicas}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">端点</span>
                <span className="font-mono text-xs truncate max-w-[150px]">{deployment.endpoint_url}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">创建时间</span>
                <span>{new Date(deployment.created_at).toLocaleDateString()}</span>
              </div>
            </div>
            <div className="mt-4 flex space-x-2">
              <button className="flex-1 px-3 py-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100">
                管理
              </button>
              <button className="flex-1 px-3 py-1 bg-gray-50 text-gray-600 rounded hover:bg-gray-100">
                监控
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )

  const renderEvaluation = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">模型评估</h3>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + 新建评估
        </button>
      </div>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">评估ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">模型ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">评估类型</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">通过率</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {evaluations.map((evaluation) => (
              <tr key={evaluation.evaluation_id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                  {evaluation.evaluation_id.slice(0, 12)}...
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {evaluation.model_id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {evaluation.evaluation_type}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {renderStatusBadge(evaluation.status)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                      <div 
                        className={`h-2 rounded-full ${
                          (evaluation.summary?.pass_rate || 0) >= 0.8 ? 'bg-green-500' : 'bg-yellow-500'
                        }`}
                        style={{ width: `${(evaluation.summary?.pass_rate || 0) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-500">
                      {((evaluation.summary?.pass_rate || 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <button className="text-blue-600 hover:text-blue-900">查看报告</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const tabs = [
    { id: 'datasets', label: '数据集', icon: '📊' },
    { id: 'deployment', label: '模型部署', icon: '🚀' },
    { id: 'evaluation', label: '模型评估', icon: '📈' },
  ]

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <>
          {activeTab === 'datasets' && renderDatasets()}
          {activeTab === 'deployment' && renderDeployment()}
          {activeTab === 'evaluation' && renderEvaluation()}
        </>
      )}
    </div>
  )
}

export default MLOps
