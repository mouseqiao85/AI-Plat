import { useState, useEffect } from 'react'
import { User, Shield, Bell, Database, Plus, Edit2, Trash2, X, Users, Lock, Eye, EyeOff } from 'lucide-react'

interface UserItem {
  id: string
  username: string
  email: string
  role: string
  is_active: boolean
  created_at: string
  last_login?: string
}

interface Role {
  name: string
  description: string
  permissions: string[]
}

interface Permission {
  id: string
  name: string
  description: string
  resource: string
  action: string
}

type SettingsTab = 'users' | 'roles' | 'security' | 'notifications' | 'data'

function Settings() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('users')
  const [users, setUsers] = useState<UserItem[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [loading, setLoading] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [modalType, setModalType] = useState<'createUser' | 'editUser' | 'createRole' | 'apiKey'>('createUser')
  const [selectedItem, setSelectedItem] = useState<UserItem | Role | null>(null)
  const [apiKeys, setApiKeys] = useState<any[]>([])

  useEffect(() => {
    if (activeTab === 'users') fetchUsers()
    if (activeTab === 'roles') fetchRoles()
    if (activeTab === 'security') fetchApiKeys()
  }, [activeTab])

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/auth/users', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setUsers(data.users || [])
      }
    } catch (error) {
      console.error('Failed to fetch users:', error)
      setUsers(getMockUsers())
    }
    setLoading(false)
  }

  const fetchRoles = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/auth/roles', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setRoles(data.roles || [])
        setPermissions(data.permissions || [])
      }
    } catch (error) {
      console.error('Failed to fetch roles:', error)
      setRoles(getMockRoles())
      setPermissions(getMockPermissions())
    }
    setLoading(false)
  }

  const fetchApiKeys = async () => {
    setLoading(true)
    setApiKeys(getMockApiKeys())
    setLoading(false)
  }

  const getMockUsers = (): UserItem[] => [
    { id: '1', username: 'admin', email: 'admin@example.com', role: 'admin', is_active: true, created_at: '2024-01-01', last_login: '2024-03-18' },
    { id: '2', username: 'developer', email: 'dev@example.com', role: 'developer', is_active: true, created_at: '2024-02-15', last_login: '2024-03-17' },
    { id: '3', username: 'analyst', email: 'analyst@example.com', role: 'analyst', is_active: false, created_at: '2024-03-01' },
  ]

  const getMockRoles = (): Role[] => [
    { name: 'admin', description: '系统管理员，拥有所有权限', permissions: ['*'] },
    { name: 'developer', description: '开发者，可以管理模型和工作流', permissions: ['models:read', 'models:write', 'workflows:*'] },
    { name: 'analyst', description: '分析师，只读权限', permissions: ['models:read', 'data:read'] },
  ]

  const getMockPermissions = (): Permission[] => [
    { id: '1', name: 'models:read', description: '查看模型', resource: 'models', action: 'read' },
    { id: '2', name: 'models:write', description: '创建和编辑模型', resource: 'models', action: 'write' },
    { id: '3', name: 'workflows:read', description: '查看工作流', resource: 'workflows', action: 'read' },
    { id: '4', name: 'workflows:write', description: '创建和编辑工作流', resource: 'workflows', action: 'write' },
    { id: '5', name: 'users:manage', description: '管理用户', resource: 'users', action: 'manage' },
    { id: '6', name: 'ontology:read', description: '查看本体', resource: 'ontology', action: 'read' },
    { id: '7', name: 'ontology:write', description: '编辑本体', resource: 'ontology', action: 'write' },
  ]

  const getMockApiKeys = () => [
    { id: '1', name: 'Production API Key', key: 'sk-****...****abc123', created_at: '2024-01-15', last_used: '2024-03-18', expires_at: '2025-01-15' },
    { id: '2', name: 'Development Key', key: 'sk-****...****def456', created_at: '2024-02-20', last_used: '2024-03-17', expires_at: '2024-08-20' },
  ]

  const handleCreateUser = () => {
    setModalType('createUser')
    setSelectedItem(null)
    setShowModal(true)
  }

  const handleEditUser = (user: UserItem) => {
    setModalType('editUser')
    setSelectedItem(user)
    setShowModal(true)
  }

  const handleToggleUserStatus = async (user: UserItem) => {
    const token = localStorage.getItem('access_token')
    const action = user.is_active ? 'deactivate' : 'activate'
    try {
      const res = await fetch(`/api/auth/users/${user.id}/${action}`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        fetchUsers()
      }
    } catch (error) {
      console.error('Failed to toggle user status:', error)
      setUsers(users.map(u => u.id === user.id ? { ...u, is_active: !u.is_active } : u))
    }
  }

  const handleDeleteUser = async (userId: string) => {
    if (!confirm('确定要删除此用户吗？')) return
    setUsers(users.filter(u => u.id !== userId))
  }

  const handleCreateApiKey = () => {
    setModalType('apiKey')
    setShowModal(true)
  }

  const handleDeleteApiKey = (keyId: string) => {
    if (!confirm('确定要删除此API密钥吗？')) return
    setApiKeys(apiKeys.filter(k => k.id !== keyId))
  }

  const tabs = [
    { id: 'users' as const, label: '用户管理', icon: Users },
    { id: 'roles' as const, label: '角色权限', icon: Lock },
    { id: 'security' as const, label: '安全设置', icon: Shield },
    { id: 'notifications' as const, label: '通知设置', icon: Bell },
    { id: 'data' as const, label: '数据管理', icon: Database },
  ]

  const renderUsers = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">用户列表</h2>
        <button onClick={handleCreateUser} className="btn btn-primary flex items-center gap-2">
          <Plus size={18} /> 添加用户
        </button>
      </div>
      
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">用户名</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">邮箱</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">角色</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">最后登录</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                      <User size={16} className="text-primary-600" />
                    </div>
                    <span className="font-medium text-gray-900">{user.username}</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500">{user.email}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    user.role === 'admin' ? 'bg-purple-100 text-purple-800' :
                    user.role === 'developer' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {user.role}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {user.is_active ? '活跃' : '停用'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500 text-sm">
                  {user.last_login || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <button onClick={() => handleEditUser(user)} className="text-blue-600 hover:text-blue-900 mr-3">
                    <Edit2 size={16} />
                  </button>
                  <button onClick={() => handleToggleUserStatus(user)} className="text-yellow-600 hover:text-yellow-900 mr-3">
                    {user.is_active ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                  <button onClick={() => handleDeleteUser(user.id)} className="text-red-600 hover:text-red-900">
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const renderRoles = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">角色与权限</h2>
        <button onClick={() => { setModalType('createRole'); setShowModal(true) }} className="btn btn-primary flex items-center gap-2">
          <Plus size={18} /> 添加角色
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {roles.map((role) => (
          <div key={role.name} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">{role.name}</h3>
              <button className="text-gray-400 hover:text-gray-600">
                <Edit2 size={16} />
              </button>
            </div>
            <p className="text-sm text-gray-500 mb-4">{role.description}</p>
            <div className="space-y-2">
              <p className="text-xs font-medium text-gray-700">权限:</p>
              <div className="flex flex-wrap gap-2">
                {role.permissions.map((perm, idx) => (
                  <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                    {perm}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4">所有权限列表</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {permissions.map((perm) => (
            <div key={perm.id} className="p-3 bg-gray-50 rounded-lg">
              <p className="font-medium text-sm text-gray-900">{perm.name}</p>
              <p className="text-xs text-gray-500">{perm.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  const renderSecurity = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">API密钥管理</h2>
        <button onClick={handleCreateApiKey} className="btn btn-primary flex items-center gap-2">
          <Plus size={18} /> 创建密钥
        </button>
      </div>
      
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">名称</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">密钥</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">创建时间</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">过期时间</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {apiKeys.map((key) => (
              <tr key={key.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{key.name}</td>
                <td className="px-6 py-4 whitespace-nowrap font-mono text-sm text-gray-500">{key.key}</td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500 text-sm">{key.created_at}</td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-500 text-sm">{key.expires_at}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <button onClick={() => handleDeleteApiKey(key.id)} className="text-red-600 hover:text-red-900">
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4">安全设置</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-gray-900">双因素认证</p>
              <p className="text-sm text-gray-500">为账户添加额外的安全保护</p>
            </div>
            <button className="btn btn-secondary">启用</button>
          </div>
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-gray-900">IP白名单</p>
              <p className="text-sm text-gray-500">限制API访问来源</p>
            </div>
            <button className="btn btn-secondary">配置</button>
          </div>
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-gray-900">登录日志</p>
              <p className="text-sm text-gray-500">查看账户登录记录</p>
            </div>
            <button className="btn btn-secondary">查看</button>
          </div>
        </div>
      </div>
    </div>
  )

  const renderNotifications = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4">邮件通知</h3>
        <div className="space-y-4">
          {['系统更新通知', '安全告警通知', '任务完成通知', '每周报告'].map((item) => (
            <div key={item} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <span className="font-medium text-gray-900">{item}</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" defaultChecked className="sr-only peer" />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
              </label>
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  const renderData = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4">存储使用</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-gray-600">已使用</span>
            <span className="font-medium">2.4 GB / 10 GB</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-4">
            <div className="bg-primary-600 h-4 rounded-full" style={{ width: '24%' }}></div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4">数据备份</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-gray-900">自动备份</p>
              <p className="text-sm text-gray-500">每天凌晨2点自动备份</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" defaultChecked className="sr-only peer" />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
            </label>
          </div>
          <button className="w-full btn btn-secondary flex items-center justify-center gap-2">
            <Database size={18} /> 立即备份
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4">数据导出</h3>
        <div className="grid grid-cols-2 gap-4">
          <button className="btn btn-secondary">导出用户数据</button>
          <button className="btn btn-secondary">导出系统日志</button>
          <button className="btn btn-secondary">导出配置</button>
          <button className="btn btn-secondary">导出全部</button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">系统设置</h1>

      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
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
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : (
            <>
              {activeTab === 'users' && renderUsers()}
              {activeTab === 'roles' && renderRoles()}
              {activeTab === 'security' && renderSecurity()}
              {activeTab === 'notifications' && renderNotifications()}
              {activeTab === 'data' && renderData()}
            </>
          )}
        </div>
      </div>

      {showModal && (
        <Modal
          type={modalType}
          item={selectedItem}
          permissions={permissions}
          onClose={() => setShowModal(false)}
          onSave={() => {
            setShowModal(false)
            if (activeTab === 'users') fetchUsers()
            if (activeTab === 'roles') fetchRoles()
            if (activeTab === 'security') fetchApiKeys()
          }}
        />
      )}
    </div>
  )
}

function Modal({ type, item, permissions, onClose, onSave }: {
  type: 'createUser' | 'editUser' | 'createRole' | 'apiKey'
  item: any
  permissions: Permission[]
  onClose: () => void
  onSave: () => void
}) {
  const [form, setForm] = useState<any>({
    username: item?.username || '',
    email: item?.email || '',
    password: '',
    role: item?.role || 'analyst',
    name: '',
    description: '',
    selectedPermissions: item?.permissions || [],
    keyName: '',
    expiresIn: '30',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Form submitted:', form)
    onSave()
  }

  const title = {
    createUser: '添加用户',
    editUser: '编辑用户',
    createRole: '添加角色',
    apiKey: '创建API密钥',
  }[type]

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {(type === 'createUser' || type === 'editUser') && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">用户名</label>
                <input
                  type="text"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>
              {type === 'createUser' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    required
                  />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">角色</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="admin">管理员</option>
                  <option value="developer">开发者</option>
                  <option value="analyst">分析师</option>
                </select>
              </div>
            </>
          )}

          {type === 'createRole' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">角色名称</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  rows={2}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">权限</label>
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                  {permissions.map((perm) => (
                    <label key={perm.id} className="flex items-center gap-2 p-2 bg-gray-50 rounded cursor-pointer hover:bg-gray-100">
                      <input
                        type="checkbox"
                        checked={form.selectedPermissions.includes(perm.name)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setForm({ ...form, selectedPermissions: [...form.selectedPermissions, perm.name] })
                          } else {
                            setForm({ ...form, selectedPermissions: form.selectedPermissions.filter((p: string) => p !== perm.name) })
                          }
                        }}
                        className="rounded text-primary-600"
                      />
                      <span className="text-sm">{perm.name}</span>
                    </label>
                  ))}
                </div>
              </div>
            </>
          )}

          {type === 'apiKey' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">密钥名称</label>
                <input
                  type="text"
                  value={form.keyName}
                  onChange={(e) => setForm({ ...form, keyName: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="例如: Production API Key"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">有效期</label>
                <select
                  value={form.expiresIn}
                  onChange={(e) => setForm({ ...form, expiresIn: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="30">30天</option>
                  <option value="90">90天</option>
                  <option value="180">180天</option>
                  <option value="365">1年</option>
                  <option value="never">永不过期</option>
                </select>
              </div>
            </>
          )}

          <div className="flex justify-end gap-3 pt-4">
            <button type="button" onClick={onClose} className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg">
              取消
            </button>
            <button type="submit" className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
              保存
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Settings
