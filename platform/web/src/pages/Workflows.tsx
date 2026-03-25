import { useState } from 'react'
import { Plus, Copy } from 'lucide-react'
import WorkflowEditor from '@/components/WorkflowEditor'

interface WorkflowNode {
  id: string
  name: string
  type: 'start' | 'end' | 'task' | 'condition'
  status?: 'pending' | 'running' | 'completed' | 'failed'
  agent?: string
  skill?: string
}

interface WorkflowEdge {
  id: string
  source: string
  target: string
  label?: string
}

const sampleNodes: WorkflowNode[] = [
  { id: 'node_1', name: '开始', type: 'start', status: 'completed' },
  { id: 'node_2', name: '数据处理', type: 'task', status: 'running', agent: '数据分析代理' },
  { id: 'node_3', name: '模型推理', type: 'task', status: 'pending', agent: '推理代理' },
  { id: 'node_4', name: '结果判断', type: 'condition', status: 'pending' },
  { id: 'node_5', name: '结束', type: 'end' },
]

const sampleEdges: WorkflowEdge[] = [
  { id: 'edge_1', source: 'node_1', target: 'node_2' },
  { id: 'edge_2', source: 'node_2', target: 'node_3' },
  { id: 'edge_3', source: 'node_3', target: 'node_4' },
  { id: 'edge_4', source: 'node_4', target: 'node_5' },
]

const savedWorkflows = [
  { id: 'wf_001', name: '数据处理流水线', status: 'running', tasks: 5, lastRun: '10分钟前' },
  { id: 'wf_002', name: '模型训练流程', status: 'completed', tasks: 8, lastRun: '2小时前' },
  { id: 'wf_003', name: '报告生成流程', status: 'pending', tasks: 3, lastRun: '昨天' },
]

function Workflows() {
  const [nodes, setNodes] = useState<WorkflowNode[]>(sampleNodes)
  const [edges, setEdges] = useState<WorkflowEdge[]>(sampleEdges)
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null)

  const handleNodeDelete = (nodeId: string) => {
    setNodes(nodes.filter(n => n.id !== nodeId))
    setEdges(edges.filter(e => e.source !== nodeId && e.target !== nodeId))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">工作流编排</h1>
        <div className="flex items-center gap-3">
          <button className="btn btn-secondary flex items-center gap-2">
            <Copy className="w-4 h-4" />
            复制
          </button>
          <button className="btn btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" />
            新建工作流
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="card">
          <h3 className="font-medium text-gray-900 mb-4">已保存的工作流</h3>
          <div className="space-y-2">
            {savedWorkflows.map((wf) => (
              <div
                key={wf.id}
                onClick={() => setSelectedWorkflow(wf.id)}
                className={`p-3 rounded-lg cursor-pointer transition-colors ${
                  selectedWorkflow === wf.id
                    ? 'bg-primary-50 border border-primary-200'
                    : 'hover:bg-gray-50 border border-transparent'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-900">{wf.name}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs ${
                    wf.status === 'running' ? 'bg-success-500/10 text-success-600' :
                    wf.status === 'completed' ? 'bg-gray-100 text-gray-600' :
                    'bg-yellow-100 text-yellow-600'
                  }`}>
                    {wf.status === 'running' ? '运行中' : wf.status === 'completed' ? '已完成' : '待运行'}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                  <span>{wf.tasks}个任务</span>
                  <span>·</span>
                  <span>上次运行: {wf.lastRun}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-3">
          <div className="card h-[600px] p-0 overflow-hidden">
            <WorkflowEditor
              nodes={nodes}
              edges={edges}
              onNodeAdd={(node) => setNodes([...nodes, node])}
              onNodeDelete={handleNodeDelete}
              onRun={() => console.log('Running workflow...')}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default Workflows
