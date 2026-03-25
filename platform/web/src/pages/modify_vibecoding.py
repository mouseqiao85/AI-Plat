import re

# 读取原始文件
with open('Vibecoding.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 定义要替换的旧工具栏代码（从第265行开始的工具栏div）
old_toolbar = '''      <div className="bg-white border border-gray-200 rounded-lg p-3 mb-4">
        <div className="flex flex-wrap gap-6">
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-400 mr-2">代码操作</span>
            <button 
              onClick={handleGenerate}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary-50 text-primary-700 rounded hover:bg-primary-100 disabled:opacity-50"
            >
              <Wand2 className="w-4 h-4" />
              生成代码
            </button>
            <button 
              onClick={handleAnalyze}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded disabled:opacity-50"
            >
              <FileCode className="w-4 h-4" />
              代码分析
            </button>
            <button 
              onClick={handleRefactor}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded disabled:opacity-50"
            >
              <RefreshCw className="w-4 h-4" />
              重构
            </button>
            <button 
              onClick={handleDocument}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded disabled:opacity-50"
            >
              <FileText className="w-4 h-4" />
              文档生成
            </button>
          </div>
          
          <div className="w-px bg-gray-200"></div>
          
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-400 mr-2">调试测试</span>
            <button 
              onClick={handleDebug}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded disabled:opacity-50"
            >
              <Bug className="w-4 h-4" />
              调试
            </button>
            <button 
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded disabled:opacity-50"
            >
              <TestTube className="w-4 h-4" />
              运行测试
            </button>
            <button 
              onClick={handleExplain}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded disabled:opacity-50"
            >
              <MessageSquare className="w-4 h-4" />
              AI解释
            </button>
          </div>
          
          <div className="w-px bg-gray-200"></div>
          
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-400 mr-2">版本控制</span>
            <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded">
              <GitBranch className="w-4 h-4" />
              Git操作
            </button>
            <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded">
              <Save className="w-4 h-4" />
              保存
            </button>
            <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded">
              <Download className="w-4 h-4" />
              下载
            </button>
          </div>
          
          <div className="w-px bg-gray-200"></div>
          
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-400 mr-2">部署</span>
            <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-50 text-green-700 rounded hover:bg-green-100">
              <Rocket className="w-4 h-4" />
              一键部署
            </button>
          </div>
        </div>
      </div>'''

# 定义新的工具栏代码
new_toolbar = '''      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
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
              <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 transition-colors">
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
              <button className="inline-flex items-c
