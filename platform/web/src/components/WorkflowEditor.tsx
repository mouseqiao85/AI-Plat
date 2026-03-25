import { useState } from 'react'
import { Play, Plus, Trash2, GripVertical } from 'lucide-react'

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

interface WorkflowEditorProps {
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  onNodeSelect?: (node: WorkflowNode) => void
  onNodeAdd?: (node: WorkflowNode) => void
  onNodeDelete?: (nodeId: string) => void
  onRun?: () => void
}

function WorkflowEditor({
  nodes,
  edges,
  onNodeSelect,
  onNodeAdd,
  onNodeDelete,
  onRun,
}: WorkflowEditorProps) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null)

  const getNodeColor = (type: string, status?: string) => {
    if (status === 'completed') return 'bg-success-500'
    if (status === 'running') return 'bg-primary-500 animate-pulse'
    if (status === 'failed') return 'bg-red-500'
    
    switch (type) {
      case 'start': return 'bg-success-500'
      case 'end': return 'bg-gray-500'
      case 'condition': return 'bg-yellow-500'
      default: return 'bg-primary-500'
    }
  }

  const handleNodeClick = (node: WorkflowNode) => {
    setSelectedNode(node.id)
    onNodeSelect?.(node)
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 relative bg-gray-50 rounded-lg overflow-hidden">
        <div className="absolute top-4 right-4 flex gap-2 z-10">
          <button
            onClick={onRun}
            className="btn btn-primary flex items-center gap-2"
          >
            <Play className="w-4 h-4" />
            运行
          </button>
          <button
            onClick={() => onNodeAdd?.({
              id: `node_${Date.now()}`,
              name: '新任务',
              type: 'task',
            })}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            添加节点
          </button>
        </div>

        <svg className="w-full h-full">
          {edges.map((edge) => {
            const sourceNode = nodes.find(n => n.id === edge.source)
            const targetNode = nodes.find(n => n.id === edge.target)
            if (!sourceNode || !targetNode) return null
            
            return (
              <line
                key={edge.id}
                x1={150}
                y1={100}
                x2={300}
                y2={200}
                stroke="#9ca3af"
                strokeWidth="2"
                markerEnd="url(#arrow)"
              />
            )
          })}
          <defs>
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#9ca3af" />
            </marker>
          </defs>
        </svg>

        <div className="absolute inset-0 p-8">
          {nodes.map((node, index) => (
            <div
              key={node.id}
              onClick={() => handleNodeClick(node)}
              className={`absolute cursor-pointer transition-all ${
                selectedNode === node.id ? 'ring-2 ring-primary-500 ring-offset-2' : ''
              }`}
              style={{
                left: `${100 + (index % 3) * 200}px`,
                top: `${100 + Math.floor(index / 3) * 150}px`,
              }}
            >
              <div className={`w-40 rounded-lg border shadow-sm bg-white ${
                selectedNode === node.id ? 'border-primary-500' : 'border-gray-200'
              }`}>
                <div className="flex items-center gap-2 p-3 border-b border-gray-100">
                  <GripVertical className="w-4 h-4 text-gray-300 cursor-move" />
                  <span className={`w-3 h-3 rounded-full ${getNodeColor(node.type, node.status)}`} />
                  <span className="font-medium text-gray-900 text-sm">{node.name}</span>
                </div>
                {node.agent && (
                  <div className="p-3 text-xs text-gray-500">
                    代理: {node.agent}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="w-64 border-l bg-white p-4">
        <h3 className="font-medium text-gray-900 mb-4">节点属性</h3>
        {selectedNode ? (
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-500 mb-1">名称</label>
              <input
                type="text"
                className="input"
                defaultValue={nodes.find(n => n.id === selectedNode)?.name}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-500 mb-1">类型</label>
              <select className="input">
                <option value="task">任务</option>
                <option value="condition">条件</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-500 mb-1">代理</label>
              <select className="input">
                <option value="">选择代理</option>
                <option value="agent_1">客服代理</option>
                <option value="agent_2">分析代理</option>
              </select>
            </div>
            <button
              onClick={() => onNodeDelete?.(selectedNode)}
              className="btn w-full text-red-600 hover:bg-red-50 flex items-center justify-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              删除节点
            </button>
          </div>
        ) : (
          <p className="text-sm text-gray-500">选择一个节点查看属性</p>
        )}
      </div>
    </div>
  )
}

export default WorkflowEditor
