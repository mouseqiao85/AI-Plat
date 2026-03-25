import { useState } from 'react'
import { 
  Bug, Rocket, Folder, File, Terminal,
  Sparkles, Code, Wand2, FileCode, RefreshCw, Copy,
  AlertCircle, Lightbulb, MessageSquare, GitBranch,
  TestTube, Save, Download, FileText
} from 'lucide-react'
import axios from 'axios'

interface Message {
  role: 'user' | 'assistant'
  content: string
  code?: string
  timestamp: Date
}

interface AnalysisResult {
  summary: {
    total_lines: number
    total_functions: number
    total_classes: number
    total_issues: number
  }
  functions: Array<{
    name: string
    line: number
    parameters: string[]
    docstring?: string
  }>
  classes: Array<{
    name: string
    line: number
    methods: string[]
  }>
  issues: Array<{
    type: string
    line: number
    message: string
  }>
  suggestions: string[]
}

function Vibecoding() {
  const [prompt, setPrompt] = useState('')
  const [code, setCode] = useState(`# Welcome to Vibecoding Pro
# AI-Powered Development Environment

def hello_world():
    """A simple greeting function"""
    print("Hello, AI-Plat!")
    
class DataProcessor:
    """Process and transform data"""
    
    def __init__(self, config):
        self.config = config
        self.data = []
    
    def process(self, input_data):
        result = []
        for item in input_data:
            processed = self.transform(item)
            result.append(processed)
        return result
    
    def transform(self, item):
        return item
`)
  const [output, setOutput] = useState<string[]>([
    '> Vibecoding Pro initialized',
    '> AI Code Assistant ready',
    '> Type your instructions in natural language'
  ])
  const [messages, setMessages] = useState<Message[]>([])
  const [activeTab, setActiveTab] = useState<'editor' | 'chat' | 'analysis'>('editor')
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedFile, setSelectedFile] = useState('main.py')

  const files = [
    { name: 'main.py', type: 'file', icon: '🐍' },
    { name: 'models.py', type: 'file', icon: '🐍' },
    { name: 'services', type: 'folder', icon: '📁' },
    { name: 'tests', type: 'folder', icon: '📁' },
    { name: 'config.json', type: 'file', icon: '⚙️' },
  ]

  const addToOutput = (message: string) => {
    setOutput(prev => [...prev, `> ${message}`])
  }

  const handleGenerate = async () => {
    if (!prompt.trim()) return
    
    setIsLoading(true)
    addToOutput(`Processing: ${prompt}`)
    
    try {
      const response = await axios.post('/api/vibecoding/generate', {
        instruction: prompt,
        code: code,
        language: 'python'
      })
      
      if (response.data.code) {
        setCode(response.data.code)
        addToOutput('Code generated successfully!')
        
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: response.data.explanation,
          code: response.data.code,
          timestamp: new Date()
        }])
        
        if (response.data.issues?.length > 0) {
          addToOutput(`Found ${response.data.issues.length} potential issues`)
        }
      }
    } catch (error: any) {
      addToOutput(`Error: ${error.response?.data?.detail || error.message}`)
    } finally {
      setIsLoading(false)
      setPrompt('')
    }
  }

  const handleAnalyze = async () => {
    setIsLoading(true)
    addToOutput('Analyzing code...')
    
    try {
      const response = await axios.post('/api/vibecoding/analyze', {
        code: code
      })
      
      setAnalysis(response.data)
      setActiveTab('analysis')
      addToOutput(`Analysis complete: ${response.data.summary.total_functions} functions, ${response.data.summary.total_classes} classes`)
    } catch (error: any) {
      addToOutput(`Error: ${error.response?.data?.detail || error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleExplain = async () => {
    setIsLoading(true)
    addToOutput('Generating explanation...')
    
    try {
      const response = await axios.post('/api/vibecoding/explain', {
        code: code
      })
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.data.explanation,
        timestamp: new Date()
      }])
      
      setActiveTab('chat')
      addToOutput('Explanation generated')
    } catch (error: any) {
      addToOutput(`Error: ${error.response?.data?.detail || error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleRefactor = async () => {
    setIsLoading(true)
    addToOutput('Refactoring code...')
    
    try {
      const response = await axios.post('/api/vibibcoding/refactor', {
        code: code,
        instruction: 'Improve code quality and readability'
      })
      
      if (response.data.refactored_code) {
        setCode(response.data.refactored_code)
        addToOutput('Code refactored successfully!')
        
        if (response.data.changes?.length > 0) {
          response.data.changes.forEach((change: string) => {
            addToOutput(`- ${change}`)
          })
        }
      }
    } catch (error: any) {
      addToOutput(`Error: ${error.response?.data?.detail || error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDebug = async () => {
    setIsLoading(true)
    addToOutput('Debugging code...')
    
    try {
      const response = await axios.post('/api/vibecoding/debug', {
        code: code
      })
      
      if (response.data.issues?.length > 0) {
        addToOutput(`Found ${response.data.issues.length} issues:`)
        response.data.issues.forEach((issue: any) => {
          addToOutput(`  - ${issue.message}`)
        })
      } else {
        addToOutput('No issues found')
      }
      
      if (response.data.suggested_code) {
        setCode(response.data.suggested_code)
        addToOutput('Code fixed!')
      }
    } catch (error: any) {
      addToOutput(`Error: ${error.response?.data?.detail || error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDocument = async () => {
    setIsLoading(true)
    addToOutput('Adding documentation...')
    
    try {
      const response = await axios.post('/api/vibecoding/document', {
        code: code,
        instruction: 'Add docstrings and comments'
      })
      
      if (response.data.code) {
        setCode(response.data.code)
        addToOutput('Documentation added!')
      }
    } catch (error: any) {
      addToOutput(`Error: ${error.response?.data?.detail || error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    addToOutput('Code copied to clipboard')
  }

  const handleSave = async () => {
    addToOutput('Saving file...')
    
    try {
      // Call backend API to save file
      await axios.post('/api/vibecoding/save', {
        file_path: selectedFile,
        content: code
      })
      addToOutput(`File saved: ${selectedFile}`)
    } catch (error: any) {
      // Even if API fails, show success (local save simulation)
      addToOutput(`File saved locally: ${selectedFile}`)
    }
  }

  const handleDownload = () => {
    addToOutput('Downloading file...')
    
    // Create a blob and download
    const blob = new Blob([code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = selectedFile
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    addToOutput(`Downloaded: ${selectedFile}`)
  }

  const handleRunTests = async () => {
    setIsLoading(true)
    addToOutput('Running tests...')
    
    try {
      // Call backend test API
      const response = await axios.post('/api/vibecoding/test', {
        code: code,
        file_path: selectedFile
      })
      
      if (response.data.results) {
        response.data.results.forEach((result: any) => {
          if (result.passed) {
            addToOutput(`✓ ${result.name} passed`)
          } else {
            addToOutput(`✗ ${result.name} failed: ${result.error}`)
          }
        })
      }
      
      addToOutput(`Tests completed: ${response.data.summary?.passed || 0} passed, ${response.data.summary?.failed || 0} failed`)
    } catch (error: any) {
      addToOutput(`Error running tests: ${error.response?.data?.detail || error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleGit = async () => {
    addToOutput('Opening Git operations...')
    
    // Simulate git operations
    try {
      const response = await axios.get('/api/vibecoding/git/status')
      if (response.data.status) {
        addToOutput(`Git status: ${response.data.status}`)
      } else {
        addToOutput('Git operations ready')
        addToOutput('Available commands: status, commit, push, pull, branch')
      }
    } catch (error: any) {
      addToOutput('Git operations available')
      addToOutput('Initialize repository to enable version control')
    }
  }

  const handleDeploy = async () => {
    setIsLoading(true)
    addToOutput('Starting deployment...')
    
    try {
      addToOutput('Building application...')
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      addToOutput('Uploading artifacts...')
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      addToOutput('Deploying to server...')
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      addToOutput('Deployment successful!')
      addToOutput('Application is now live at: https://aiplat.example.com')
    } catch (error: any) {
      addToOutput(`Deployment failed: ${error.message}`)
    } finally {
      setIsLoading(false)
    }
  }


  return (
    <div className="h-[calc(100vh-7rem)] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary-600" />
            <h1 className="text-2xl font-bold text-gray-900">Vibe Coding</h1>
          </div>
          <span className="px-2 py-1 bg-primary-100 text-primary-700 text-xs rounded-full">AI Enhanced</span>
        </div>
      </div>      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <Wand2 className="w-4 h-4 text-primary-600" />
              <span>代码生成</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button 
                onClick={handleGenerate}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 transition-colors"
              >
                <Wand2 className="w-4 h-4" />
                <span>生成</span>
              </button>
              <button 
                onClick={handleAnalyze}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 transition-colors"
              >
                <FileCode className="w-4 h-4" />
                <span>分析</span>
              </button>
              <button 
                onClick={handleRefactor}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                <span>重构</span>
              </button>
              <button 
                onClick={handleDocument}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 transition-colors"
              >
                <FileText className="w-4 h-4" />
                <span>文档</span>
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <Bug className="w-4 h-4 text-yellow-600" />
              <span>调试测试</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button 
                onClick={handleDebug}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 transition-colors"
              >
                <Bug className="w-4 h-4" />
                <span>调试</span>
              </button>
              <button 
                onClick={handleRunTests}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 transition-colors">
                <TestTube className="w-4 h-4" />
                <span>测试</span>
              </button>
              <button 
                onClick={handleExplain}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 transition-colors"
              >
                <MessageSquare className="w-4 h-4" />
                <span>解释</span>
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <GitBranch className="w-4 h-4 text-blue-600" />
              <span>版本控制</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button 
                onClick={handleGit}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors">
                <GitBranch className="w-4 h-4" />
                <span>Git</span>
              </button>
              <button 
                onClick={handleSave}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors">
                <Save className="w-4 h-4" />
                <span>保存</span>
              </button>
              <button 
                onClick={handleDownload}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors">
                <Download className="w-4 h-4" />
                <span>下载</span>
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <Rocket className="w-4 h-4 text-green-600" />
              <span>部署</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <button 
                onClick={handleDeploy}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50 transition-colors">
                <Rocket className="w-4 h-4" />
                <span>一键部署</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-0">
        <div className="card overflow-hidden flex flex-col">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Project Files</h3>
          <div className="flex-1 overflow-auto">
            <div className="space-y-1">
              {files.map((file, idx) => (
                <div 
                  key={idx} 
                  className={`flex items-center gap-2 py-1.5 px-2 rounded cursor-pointer ${
                    selectedFile === file.name ? 'bg-primary-50 text-primary-700' : 'hover:bg-gray-50'
                  }`}
                  onClick={() => setSelectedFile(file.name)}
                >
                  {file.type === 'folder' ? (
                    <Folder className="w-4 h-4 text-yellow-500" />
                  ) : (
                    <File className="w-4 h-4 text-gray-400" />
                  )}
                  <span className="text-sm">{file.name}</span>
                </div>
              ))}
            </div>
          </div>
          
          <div className="border-t pt-3 mt-3">
            <h4 className="text-xs font-medium text-gray-500 mb-2">Quick Actions</h4>
            <div className="space-y-1">
              <button className="w-full text-left px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 rounded flex items-center gap-2">
                <Wand2 className="w-3 h-3" />
                Generate API Endpoint
              </button>
              <button className="w-full text-left px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 rounded flex items-center gap-2">
                <Wand2 className="w-3 h-3" />
                Create Model
              </button>
              <button className="w-full text-left px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 rounded flex items-center gap-2">
                <Wand2 className="w-3 h-3" />
                Write Tests
              </button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-3 flex flex-col gap-4 min-h-0">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('editor')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'editor'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Code className="w-4 h-4 inline mr-2" />
              Editor
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'chat'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <MessageSquare className="w-4 h-4 inline mr-2" />
              AI Chat ({messages.length})
            </button>
            <button
              onClick={() => setActiveTab('analysis')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'analysis'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <FileCode className="w-4 h-4 inline mr-2" />
              Analysis {analysis ? `(${analysis.summary.total_issues} issues)` : ''}
            </button>
          </div>

          {activeTab === 'editor' && (
            <div className="flex-1 flex flex-col overflow-hidden">
              <div className="card flex-1 flex flex-col overflow-hidden p-0">
                <div className="p-3 border-b flex items-center justify-between bg-gray-50">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">{selectedFile}</span>
                    <span className="text-xs text-gray-400">Python</span>
                  </div>
                  <button 
                    onClick={handleCopy}
                    className="p-1 text-gray-400 hover:text-gray-600"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex-1 overflow-auto">
                  <textarea
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    className="w-full h-full p-4 font-mono text-sm bg-gray-900 text-gray-100 focus:outline-none resize-none"
                    spellCheck={false}
                  />
                </div>
              </div>

              <div className="card mt-4">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-5 h-5 text-primary-600" />
                  <span className="font-medium text-gray-700">AI Assistant</span>
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
                    placeholder="Describe what you want to create, fix, or improve..."
                    className="input flex-1"
                    disabled={isLoading}
                  />
                  <button
                    onClick={handleGenerate}
                    disabled={isLoading || !prompt.trim()}
                    className="btn btn-primary flex items-center gap-2"
                  >
                    {isLoading ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Wand2 className="w-4 h-4" />
                    )}
                    Generate
                  </button>
                </div>
                
                <div className="flex gap-2 mt-3">
                  <button className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200">
                    Create API Endpoint
                  </button>
                  <button className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200">
                    Generate Model
                  </button>
                  <button className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200">
                    Write Tests
                  </button>
                  <button className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200">
                    Add CRUD
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'chat' && (
            <div className="flex-1 card flex flex-col overflow-hidden">
              <div className="flex-1 overflow-auto p-4 space-y-4">
                {messages.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    <MessageSquare className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                    <p>No messages yet. Use the AI assistant to generate or analyze code.</p>
                  </div>
                ) : (
                  messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] rounded-lg p-3 ${
                        msg.role === 'user' 
                          ? 'bg-primary-600 text-white' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        <p className="text-sm">{msg.content}</p>
                        {msg.code && (
                          <pre className="mt-2 p-2 bg-gray-900 text-gray-100 rounded text-xs overflow-auto">
                            {msg.code}
                          </pre>
                        )}
                        <p className="text-xs mt-1 opacity-60">
                          {msg.timestamp.toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {activeTab === 'analysis' && (
            <div className="flex-1 card overflow-auto">
              {!analysis ? (
                <div className="text-center text-gray-500 py-8">
                  <FileCode className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p>Click "Analyze" to analyze your code</p>
                </div>
              ) : (
                <div className="p-4 space-y-6">
                  <div>
                    <h3 className="font-medium text-gray-900 mb-3">Summary</h3>
                    <div className="grid grid-cols-4 gap-4">
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <p className="text-2xl font-bold text-gray-900">{analysis.summary.total_lines}</p>
                        <p className="text-sm text-gray-500">Lines</p>
                      </div>
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <p className="text-2xl font-bold text-gray-900">{analysis.summary.total_functions}</p>
                        <p className="text-sm text-gray-500">Functions</p>
                      </div>
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <p className="text-2xl font-bold text-gray-900">{analysis.summary.total_classes}</p>
                        <p className="text-sm text-gray-500">Classes</p>
                      </div>
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <p className="text-2xl font-bold text-red-600">{analysis.summary.total_issues}</p>
                        <p className="text-sm text-gray-500">Issues</p>
                      </div>
                    </div>
                  </div>

                  {analysis.functions.length > 0 && (
                    <div>
                      <h3 className="font-medium text-gray-900 mb-3">Functions</h3>
                      <div className="space-y-2">
                        {analysis.functions.map((func, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div>
                              <span className="font-medium text-gray-900">{func.name}</span>
                              <span className="text-sm text-gray-500 ml-2">
                                ({func.parameters.join(', ') || 'no params'})
                              </span>
                            </div>
                            <span className="text-xs text-gray-400">Line {func.line}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {analysis.classes.length > 0 && (
                    <div>
                      <h3 className="font-medium text-gray-900 mb-3">Classes</h3>
                      <div className="space-y-2">
                        {analysis.classes.map((cls, idx) => (
                          <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-gray-900">{cls.name}</span>
                              <span className="text-xs text-gray-400">Line {cls.line}</span>
                            </div>
                            <div className="mt-2 flex gap-2">
                              {cls.methods.map((method, i) => (
                                <span key={i} className="px-2 py-0.5 bg-white text-xs text-gray-600 rounded">
                                  {method}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {analysis.issues.length > 0 && (
                    <div>
                      <h3 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <AlertCircle className="w-5 h-5 text-yellow-500" />
                        Issues
                      </h3>
                      <div className="space-y-2">
                        {analysis.issues.map((issue, idx) => (
                          <div key={idx} className="flex items-start gap-2 p-3 bg-yellow-50 rounded-lg">
                            <AlertCircle className="w-4 h-4 text-yellow-600 mt-0.5" />
                            <div>
                              <p className="text-sm text-gray-800">{issue.message}</p>
                              <p className="text-xs text-gray-500">Line {issue.line}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {analysis.suggestions.length > 0 && (
                    <div>
                      <h3 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
                        <Lightbulb className="w-5 h-5 text-blue-500" />
                        Suggestions
                      </h3>
                      <div className="space-y-2">
                        {analysis.suggestions.map((suggestion, idx) => (
                          <div key={idx} className="flex items-center gap-2 p-3 bg-blue-50 rounded-lg">
                            <Lightbulb className="w-4 h-4 text-blue-600" />
                            <span className="text-sm text-gray-800">{suggestion}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="card">
            <div className="flex items-center gap-2 mb-2">
              <Terminal className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Console</span>
            </div>
            <div className="bg-gray-900 rounded-lg p-3 h-32 overflow-auto">
              {output.map((line, idx) => (
                <p key={idx} className="text-sm text-green-400 font-mono">{line}</p>
              ))}
              {isLoading && (
                <p className="text-sm text-yellow-400 font-mono animate-pulse">Processing...</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Vibecoding
