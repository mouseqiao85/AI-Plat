# AI-Plat Web Frontend

NexusMind OS (AI-Plat V3.0) 前端Web界面

## 技术栈

- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router v6
- TanStack Query (React Query)
- Zustand (状态管理)
- Recharts (图表)
- Lucide React (图标)

## 快速开始

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview
```

## 项目结构

```
src/
├── components/        # 可复用组件
│   ├── Layout.tsx     # 主布局
│   ├── Sidebar.tsx    # 侧边栏
│   └── Header.tsx     # 顶部导航
├── pages/             # 页面组件
│   ├── Dashboard.tsx  # 仪表盘
│   ├── Ontology.tsx   # 智能本体引擎
│   ├── Agents.tsx     # 代理系统管理
│   ├── Vibecoding.tsx # Vibecoding Pro
│   ├── MCP.tsx        # 模型连接管理
│   ├── Assets.tsx     # 资产广场
│   └── Settings.tsx   # 系统设置
├── services/          # API服务
│   └── api.ts         # API调用封装
├── stores/            # 状态管理
│   └── appStore.ts    # 全局状态
├── utils/             # 工具函数
│   └── helpers.ts     # 辅助函数
├── styles/            # 样式文件
│   └── globals.css    # 全局样式
├── App.tsx            # 应用入口
└── main.tsx           # 渲染入口
```

## 功能模块

### 1. 仪表盘 (Dashboard)
- 平台概览
- ROI分析
- 任务状态
- 最近活动

### 2. 智能本体引擎 (Ontology)
- 本体列表管理
- 实体关系可视化
- 推理引擎集成

### 3. 代理系统 (Agents)
- 代理状态监控
- 技能管理
- 任务编排

### 4. Vibecoding Pro
- 自然语言代码生成
- 代码编辑器
- 运行调试

### 5. 模型连接 (MCP)
- 模型连接管理
- 性能监控
- 拓扑可视化

### 6. 资产广场 (Assets)
- 模型广场
- 数据广场
- 应用广场

### 7. 系统设置 (Settings)
- 用户管理
- 权限配置
- 系统信息

## 开发规范

- 组件采用函数式组件 + Hooks
- 样式使用Tailwind CSS
- 状态管理使用Zustand
- API调用使用React Query
- 类型定义使用TypeScript

## 与后端集成

前端通过代理配置连接到后端API (默认 http://localhost:8000)

确保后端服务已启动:
```bash
cd ../platform
python main.py
```
