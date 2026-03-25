import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Brain,
  Bot,
  Code2,
  Link2,
  Package,
  Settings,
  Sparkles,
  Database,
  Layers
} from 'lucide-react'

const navItems = [
  { path: '/', icon: LayoutDashboard, label: '仪表盘' },
  { path: '/ontology', icon: Brain, label: '智能本体' },
  { path: '/agents', icon: Bot, label: 'Agent管理' },
  { path: '/vibecoding', icon: Code2, label: 'Vibe Coding' },
  { path: '/skills', icon: Sparkles, label: '技能管理' },
  { path: '/mcp', icon: Link2, label: '模型连接' },
  { path: '/data', icon: Database, label: '数据管理' },
  { path: '/models', icon: Layers, label: '模型管理' },
  { path: '/assets', icon: Package, label: '资产广场' },
  { path: '/settings', icon: Settings, label: '系统设置' },
]

function Sidebar() {
  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-gray-900">NexusMind OS</h1>
            <p className="text-xs text-gray-500">AI-Plat Platform</p>
          </div>
        </div>
      </div>
      
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `sidebar-item ${isActive ? 'sidebar-item-active' : ''}`
            }
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      
      <div className="p-4 border-t border-gray-100">
        <div className="bg-gradient-to-r from-primary-50 to-accent-50 rounded-lg p-4">
          <p className="text-sm font-medium text-gray-700">需要帮助?</p>
          <p className="text-xs text-gray-500 mt-1">查看文档或联系支持</p>
          <button className="mt-3 text-sm text-primary-600 font-medium hover:text-primary-700">
            查看文档 →
          </button>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
