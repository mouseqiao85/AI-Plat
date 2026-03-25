import { useState, useEffect } from 'react'
import { 
  Sparkles, Plus, Search, Star, Download, 
  Upload, Play, Edit, Code,
  BookOpen, Zap, FileDown, FileUp, History, BarChart3
} from 'lucide-react'
import axios from 'axios'

interface Skill {
  id: number
  skillKey: string
  name: string
  description: string
  category: string
  author: { id: number; username: string }
  version: string
  usageCount: number
  rating: number
  tags: string[]
  isPublic: boolean
  createdAt: string
}

interface SkillDetail extends Skill {
  skillContent: string
  iconUrl?: string
}

const categories = [
  { value: 'all', label: '全部分类' },
  { value: 'AI', label: 'AI智能' },
  { value: 'TOOLS', label: '工具类' },
  { value: 'AUTOMATION', label: '自动化' },
  { value: 'DATA', label: '数据处理' },
  { value: 'INTEGRATION', label: '集成服务' },
]

function Skills() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [selectedSkill, setSelectedSkill] = useState<SkillDetail | null>(null)
  const [editorContent, setEditorContent] = useState('')
  const [editorName, setEditorName] = useState('')
  const [editorDescription, setEditorDescription] = useState('')
  const [activeTab, setActiveTab] = useState<'list' | 'market' | 'editor'>('list')

  useEffect(() => {
    fetchSkills()
  }, [selectedCategory, searchQuery])

  const fetchSkills = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (selectedCategory !== 'all') params.append('category', selectedCategory)
      if (searchQuery) params.append('search', searchQuery)
      
      const response = await axios.get(`/api/skills?${params.toString()}
  useEffect(() => {
    fetchStats()
  }, [])

`)
      setSkills(response.data.data?.list || [])
    } catch (error) {
      console.error('Failed to fetch skills:', error)
      setSkills(mockSkills)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateSkill = async () => {
    if (!editorName.trim() || !editorContent.trim()) return
    
    try {
      await axios.post('/api/skills', {
        skillKey: editorName.toLowerCase().replace(/\s+/g, '-'),
        name: editorName,
        description: editorDescription,
        category: 'TOOLS',
        skillContent: editorContent,
        tags: [],
        isPublic: true
      })
      setActiveTab('list')
      setEditorName('')
      setEditorDescription('')
      setEditorContent('')
      fetchSkills()
    } catch (error) {
      console.error('Failed to create skill:', error)
    }
  }

  const handleExecuteSkill = async (skillKey: string) => {
    try {
      await axios.post(`/api/skills/${skillKey}/execute`, { parameters: {} })
      fetchSkills()
    } catch (error) {
      console.error('Failed to execute skill:', error)
    }
  }

  

  const handleExport = async (skillKey: string) => {
    try {
      const response = await axios.get(`/api/skills/${skillKey}/export`)
      const { filename, content } = response.data
      
      const blob = new Blob([content], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to export skill:', error)
    }
  }

  const handleImportClick = () => {
    setShowImportModal(true)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setImportFile(file)
      const reader = new FileReader()
      reader.onload = (event) => {
        setImportPreview(event.target?.result as string || '')
      }
      reader.readAsText(file)
    }
  }

  const handleImport = async () => {
    if (!importPreview) return
    
    try {
      const response = await axios.post('/api/skills/import', {
        filename: importFile?.name || 'skill.md',
        content: importPreview
      })
      
      if (response.data.success) {
        setShowImportModal(false)
        setImportFile(null)
        setImportPreview('')
        fetchSkills()
      }
    } catch (error) {
      console.error('Failed to import skill:', error)
    }
  }

  const handleViewVersions = async (skillKey: string) => {
    try {
      const response = await axios.get(`/api/skills/${skillKey}/versions`)
      setVersions(response.data.versions)
      setShowVersionModal(true)
    } catch (error) {
      console.error('Failed to fetch versions:', error)
    }
  }

  const handleRollback = async (skillKey: string, targetVersion: string) => {
    try {
      await axios.post(`/api/skills/${skillKey}/rollback`, {
        target_version: targetVersion
      })
      fetchSkills()
      setShowVersionModal(false)
    } catch (error) {
      console.error('Failed to rollback:', error)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await axios.get('/api/skills/stats')
      setStats(response.data)
    }

  const handleCreateReview = async () => {
    if (!selectedSkill || !reviewComment.trim()) return
    
    try {
      await axios.post(`/api/skills/${selectedSkill.skillKey}/reviews`, {
        rating: reviewRating,
        comment: reviewComment
      })
      fetchReviews(selectedSkill.skillKey)
      setShowReviewModal(false)
      setReviewComment('')
      setReviewRating(5)
    } catch (error) {
      console.error('Failed to create review:', error)
    }
  }

  const fetchReviews = async (skillKey: string) => {
    try {
      const response = await axios.get(`/api/skills/${skillKey}/reviews`)
      setReviews(response.data.reviews || [])
    } catch (error) {
      console.error('Failed to fetch reviews:', error)
    }
  }

 catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

const mockSkills: Skill[] = [
    {
      id: 1,
      skillKey: 'weather-forecast',
      name: '天气预报',
      description: '获取指定城市的实时天气信息和未来天气预报',
      category: 'TOOLS',
      author: { id: 1, username: 'admin' },
      version: '1.0.0',
      usageCount: 150,
      rating: 4.5,
      tags: ['天气', 'API', '实用工具'],
      isPublic: true,
      createdAt: '2026-03-17T08:00:00Z'
    },
    {
      id: 2,
      skillKey: 'code-review',
      name: '代码审查',
      description: '自动审查代码质量，发现潜在问题和改进建议',
      category: 'AI',
      author: { id: 1, username: 'admin' },
      version: '2.1.0',
      usageCount: 320,
      rating: 4.8,
      tags: ['代码', 'AI', '质量'],
      isPublic: true,
      createdAt: '2026-03-16T10:00:00Z'
    },
    {
      id: 3,
      skillKey: 'data-extraction',
      name: '数据抽取',
      description: '从非结构化文本中抽取结构化数据',
      category: 'DATA',
      author: { id: 2, username: 'developer' },
      version: '1.5.0',
      usageCount: 89,
      rating: 4.2,
      tags: ['数据', 'NLP', '抽取'],
      isPublic: true,
      createdAt: '2026-03-15T14:30:00Z'
    }
  ]

  const skillTemplate = `# Skill Name

## Description
Brief description of what this skill does.

## Parameters
- param1 (string): Description of parameter
- param2 (number): Description of parameter

## Usage
\`\`\`python
# Example usage code
result = execute_skill("skill-key", {"param1": "value"})
\`\`\`

## Returns
Description of the return value.

## Examples
Example 1: ...
Example 2: ...
`

  return (
    <div className="h-[calc(100vh-7rem)] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary-600" />
            <h1 className="text-2xl font-bold text-gray-900">技能管理</h1>
          </div>
          <span className="px-2 py-1 bg-primary-100 text-primary-700 text-xs rounded-full">
            {skills.length} 个技能
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => { setEditorContent(skillTemplate);
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importPreview, setImportPreview] = useState<string>('')
  const [showImportModal, setShowImportModal] = useState(false)
  const [showVersionModal, setShowVersionModal] = useState(false)
  const [versions, setVersions] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)

 setActiveTab('editor');
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [reviewRating, setReviewRating] = useState(5)
  const [reviewComment, setReviewComment] = useState('')
  const [reviews, setReviews] = useState<any[]>([])

 }}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            创建技能
          </button>
          <button onClick={handleImportClick} className="btn btn-secondary flex items-center gap-2">
            <FileUp className="w-4 h-4" />
            导入
          </button>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('list')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'list' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <BookOpen className="w-4 h-4 inline mr-2" />
          我的技能
        </button>
        <button
          onClick={() => setActiveTab('market')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'market' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <Zap className="w-4 h-4 inline mr-2" />
          技能市场
        </button>
        <button
          onClick={() => setActiveTab('editor')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'editor' ? 'bg-primary-100 text-primary-700' : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <Code className="w-4 h-4 inline mr-2" />
          技能编辑器
        </button>
      </div>

      {activeTab === 'list' && (
        <>
          <div className="flex gap-4 mb-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索技能..."
                className="input pl-10 w-full"
              />
            </div>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="input w-48"
            >
              {categories.map(cat => (
                <option key={cat.value} value={cat.value}>{cat.label}</option>
              ))}
            </select>
          </div>

          <div className="flex-1 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 overflow-auto">
            {loading ? (
              <div className="col-span-full text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
              </div>
            ) : skills.length === 0 ? (
              <div className="col-span-full text-center py-8 text-gray-500">
                <Sparkles className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p>暂无技能，点击"创建技能"开始</p>
              </div>
            ) : (
              skills.map(skill => (
                <div key={skill.id} className="card hover:shadow-md transition-shadow cursor-pointer"
                     onClick={() => setSelectedSkill(skill as SkillDetail)}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
                        <Sparkles className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-900">{skill.name}</h3>
                        <p className="text-xs text-gray-500">v{skill.version}</p>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                      {skill.category}
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-600 mb-3 line-clamp-2">{skill.description}</p>
                  
                  <div className="flex flex-wrap gap-1 mb-3">
                    {skill.tags.slice(0, 3).map((tag, idx) => (
                      <span key={idx} className="px-2 py-0.5 bg-primary-50 text-primary-600 text-xs rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                  
                  <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <Star className="w-3 h-3 text-yellow-500" />
                        {skill.rating}
                      </span>
                      <span className="flex items-center gap-1">
                        <Download className="w-3 h-3" />
                        {skill.usageCount}
                      </span>
                    </div>
                    <div className="flex gap-1">
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleExecuteSkill(skill.skillKey); }}
                        className="p-1.5 text-primary-600 hover:bg-primary-50 rounded"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                      <button className="p-1.5 text-gray-500 hover:bg-gray-100 rounded">
                        <Edit className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}

      {activeTab === 'market' && (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 overflow-auto">
          <div className="lg:col-span-2 space-y-4">
            <div className="card">
              <h3 className="font-medium text-gray-900 mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                技能统计概览
              </h3>
              {stats && (
                <div className="grid grid-cols-4 gap-4 mb-6">
                  <div className="bg-primary-50 p-4 rounded-lg text-center">
                    <p className="text-2xl font-bold text-primary-600">{stats.total_skills}</p>
                    <p className="text-sm text-gray-600">总技能数</p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg text-center">
                    <p className="text-2xl font-bold text-green-600">{stats.total_usage}</p>
                    <p className="text-sm text-gray-600">总使用次数</p>
                  </div>
                  <div className="bg-yellow-50 p-4 rounded-lg text-center">
                    <p className="text-2xl font-bold text-yellow-600">{stats.avg_rating}</p>
                    <p className="text-sm text-gray-600">平均评分</p>
                  </div>
                  <div className="bg-blue-50 p-4 rounded-lg text-center">
                    <p className="text-2xl font-bold text-blue-600">{stats.recent_created}</p>
                    <p className="text-sm text-gray-600">本月新增</p>
                  </div>
                </div>
              )}
              
              <h4 className="text-sm font-medium text-gray-700 mb-3">分类分布</h4>
              {stats && stats.top_categories && (
                <div className="space-y-2">
                  {stats.top_categories.map((cat: any, idx: number) => (
                    <div key={idx} className="flex items-center gap-3">
                      <div className="w-24 text-sm text-gray-600">{cat.category}</div>
                      <div className="flex-1 bg-gray-100 rounded-full h-4">
                        <div 
                          className="bg-primary-500 h-4 rounded-full"
                          style={{ width: `${(cat.count / stats.total_skills) * 100}%` }}
                        ></div>
                      </div>
                      <div className="w-8 text-sm text-gray-600">{cat.count}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          
          <div className="space-y-4">
            <div className="card">
              <h3 className="font-medium text-gray-900 mb-4 flex items-center gap-2">
                <Star className="w-5 h-5 text-yellow-500" />
                热门技能排行
              </h3>
              <div className="space-y-3">
                {skills.slice(0, 5).sort((a, b) => b.usageCount - a.usageCount).map((skill, idx) => (
                  <div key={skill.id} className="flex items-center gap-3 p-2 hover:bg-gray-50 rounded-lg cursor-pointer"
                       onClick={() => setSelectedSkill(skill as SkillDetail)}>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      idx === 0 ? 'bg-yellow-100 text-yellow-700' :
                      idx === 1 ? 'bg-gray-100 text-gray-700' :
                      idx === 2 ? 'bg-orange-100 text-orange-700' :
                      'bg-gray-50 text-gray-500'
                    }`}>
                      {idx + 1}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{skill.name}</p>
                      <p className="text-xs text-gray-500">{skill.usageCount} 次使用</p>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-yellow-600">
                      <Star className="w-3 h-3 fill-current" />
                      {skill.rating}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="card">
              <h3 className="font-medium text-gray-900 mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-primary-500" />
                最新技能
              </h3>
              <div className="space-y-3">
                {skills.slice(0, 5).sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()).map((skill) => (
                  <div key={skill.id} className="flex items-center gap-3 p-2 hover:bg-gray-50 rounded-lg cursor-pointer"
                       onClick={() => setSelectedSkill(skill as SkillDetail)}>
                    <div className="w-8 h-8 bg-gradient-to-br from-primary-400 to-accent-400 rounded flex items-center justify-center">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{skill.name}</p>
                      <p className="text-xs text-gray-500">{skill.category}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'editor' && (
        <div className="flex-1 grid grid-cols-2 gap-4">
          <div className="card flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-gray-900">技能配置</h3>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">技能名称</label>
                <input
                  type="text"
                  value={editorName}
                  onChange={(e) => setEditorName(e.target.value)}
                  placeholder="输入技能名称"
                  className="input w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                <textarea
                  value={editorDescription}
                  onChange={(e) => setEditorDescription(e.target.value)}
                  placeholder="描述这个技能的功能"
                  className="input w-full h-20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">分类</label>
                <select className="input w-full">
                  {categories.filter(c => c.value !== 'all').map(cat => (
                    <option key={cat.value} value={cat.value}>{cat.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
          
          <div className="card flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-gray-900">skill.md 内容</h3>
              <button className="text-sm text-primary-600 hover:text-primary-700">使用模板</button>
            </div>
            <textarea
              value={editorContent}
              onChange={(e) => setEditorContent(e.target.value)}
              className="flex-1 font-mono text-sm bg-gray-900 text-gray-100 p-4 rounded-lg resize-none focus:outline-none"
              placeholder="# 技能名称&#10;&#10;## 描述&#10;描述技能功能..."
            />
            <div className="flex justify-end gap-2 mt-3">
              <button className="btn btn-secondary">预览</button>
              <button className="btn btn-secondary">测试</button>
              <button onClick={handleCreateSkill} className="btn btn-primary">保存技能</button>
            </div>
          </div>
        </div>
      )}

      {selectedSkill && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{selectedSkill.name}</h2>
                  <p className="text-sm text-gray-500">v{selectedSkill.version} · {selectedSkill.category}</p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedSkill(null)}
                className="p-2 text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            
            <div className="p-6 overflow-auto max-h-[60vh]">
              <div className="mb-6">
                <h3 className="font-medium text-gray-900 mb-2">描述</h3>
                <p className="text-gray-600">{selectedSkill.description}</p>
              </div>
              
              <div className="mb-6">
                <h3 className="font-medium text-gray-900 mb-2">标签</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedSkill.tags.map((tag, idx) => (
                    <span key={idx} className="px-3 py-1 bg-primary-50 text-primary-600 text-sm rounded-full">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              
              <div className="mb-6">
                <h3 className="font-medium text-gray-900 mb-2">统计</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gray-50 p-4 rounded-lg text-center">
                    <p className="text-2xl font-bold text-gray-900">{selectedSkill.usageCount}</p>
                    <p className="text-sm text-gray-500">使用次数</p>
                  </div>
                  <div className="bg-gray-50 p-4 rounded-lg text-center">
                    <p className="text-2xl font-bold text-yellow-600">{selectedSkill.rating}</p>
                    <p className="text-sm text-gray-500">评分</p>
                  </div>
                  <div className="bg-gray-50 p-4 rounded-lg text-center">
                    <p className="text-sm font-medium text-gray-900">{selectedSkill.author.username}</p>
                    <p className="text-sm text-gray-500">作者</p>
                  </div>
                </div>
              </div>
              
              {'skillContent' in selectedSkill && selectedSkill.skillContent && (
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">技能内容</h3>
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg text-sm overflow-auto">
                    {selectedSkill.skillContent}
                  </pre>
                </div>
              )}
            </div>
            
            <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
              <button 
                onClick={() => setSelectedSkill(null)}
                className="btn btn-secondary"
              >
                关闭
              </button>
              <button 
                onClick={() => handleExport(selectedSkill.skillKey)}
                className="btn btn-secondary flex items-center gap-2"
              >
                <FileDown className="w-4 h-4" />
                导出
              </button>
              <button 
                onClick={() => handleViewVersions(selectedSkill.skillKey)}
                className="btn btn-secondary flex items-center gap-2"
              >
                <History className="w-4 h-4" />
                版本
              </button>
              <button className="btn btn-secondary flex items-center gap-2">
                <Edit className="w-4 h-4" />
                编辑
              </button>
              <button 
                onClick={() => { fetchReviews(selectedSkill.skillKey); setShowReviewModal(true); }}
                className="btn btn-secondary flex items-center gap-2"
              >
                <Star className="w-4 h-4" />
                评价
              </button>
              <button 
                onClick={() => handleExecuteSkill(selectedSkill.skillKey)}
                className="btn btn-primary flex items-center gap-2"
              >
                <Play className="w-4 h-4" />
                执行
              </button>
            </div>
          </div>
        </div>
      )}


      {showImportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">导入技能</h2>
              <button 
                onClick={() => setShowImportModal(false)}
                className="p-2 text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            
            <div className="p-6">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center mb-4">
                <input
                  type="file"
                  accept=".md"
                  onChange={handleFileSelect}
                  className="hidden"
                  id="import-file"
                />
                <label htmlFor="import-file" className="cursor-pointer">
                  <FileUp className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                  <p className="text-gray-600">点击选择 .md 文件或拖拽到此处</p>
                  {importFile && (
                    <p className="text-sm text-primary-600 mt-2">{importFile.name}</p>
                  )}
                </label>
              </div>
              
              {importPreview && (
                <div className="mb-4">
                  <h3 className="font-medium text-gray-900 mb-2">预览</h3>
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg text-sm overflow-auto max-h-60">
                    {importPreview}
                  </pre>
                </div>
              )}
            </div>
            
            <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
              <button 
                onClick={() => setShowImportModal(false)}
                className="btn btn-secondary"
              >
                取消
              </button>
              <button 
                onClick={handleImport}
                disabled={!importPreview}
                className="btn btn-primary"
              >
                导入
              </button>
            </div>
          </div>
        </div>
      )}

      {showVersionModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-xl overflow-hidden">
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">版本历史</h2>
              <button 
                onClick={() => setShowVersionModal(false)}
                className="p-2 text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            
            <div className="p-6 max-h-96 overflow-auto">
              {versions.length === 0 ? (
                <p className="text-center text-gray-500 py-4">暂无版本历史</p>
              ) : (
                <div className="space-y-3">
                  {versions.map((version, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">v{version.version_number}</p>
                        <p className="text-sm text-gray-500">{new Date(version.created_at).toLocaleString()}</p>
                      </div>
                      <button 
                        onClick={() => handleRollback(selectedSkill?.skillKey || '', version.version_number)}
                        className="text-sm text-primary-600 hover:text-primary-700"
                      >
                        恢复
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div className="p-4 border-t bg-gray-50 flex justify-end">
              <button 
                onClick={() => setShowVersionModal(false)}
                className="btn btn-secondary"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}



      {showReviewModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900">评价技能</h2>
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">评分</label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => setReviewRating(star)}
                      className="p-1"
                    >
                      <Star 
                        className={`w-8 h-8 ${star <= reviewRating ? 'text-yellow-400 fill-current' : 'text-gray-300'}`}
                      />
                    </button>
                  ))}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">评论</label>
                <textarea
                  value={reviewComment}
                  onChange={(e) => setReviewComment(e.target.value)}
                  placeholder="分享你使用这个技能的体验..."
                  className="input w-full h-32"
                />
              </div>
            </div>
            
            <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
              <button 
                onClick={() => setShowReviewModal(false)}
                className="btn btn-secondary"
              >
                取消
              </button>
              <button 
                onClick={handleCreateReview}
                disabled={!reviewComment.trim()}
                className="btn btn-primary"
              >
                提交评价
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

export default Skills
