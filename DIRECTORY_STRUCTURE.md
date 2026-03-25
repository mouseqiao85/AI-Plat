# AI-Plat 目录结构说明

## 概述
AI-Plat 是一个集成了本体论驱动的认知连接、智能体系统和大模型驱动开发体验的下一代AI平台。本目录包含了AI-Plat平台的所有相关文档、代码和资源。

## 当前目录结构

```
AI-Plat/
├── docs/                     # 文档目录
│   ├── AI-Plat-Dev.md            # AI-Plat开发文档
│   ├── AI-Plat-Development-Detailed.md  # AI-Plat详细开发文档
│   ├── AI-Plat-Development.md    # AI-Plat开发概述
│   ├── AI-Platform-Development-Guide.md  # AI平台开发指南
│   ├── AI-Plat-Platform-Overview.md  # AI平台概览
│   ├── COMPLETION-NOTE.md        # 完成笔记
│   ├── FINAL-INTEGRATION-REPORT.md  # 最终集成报告
│   ├── integration_plan.md       # 集成计划
│   └── MCP-FEATURE-ADDITION.md   # MCP功能添加文档
├── specs/                    # 规格说明目录
│   └── fusion_design_spec.txt    # 融合设计规格说明
├── prd_docs/                 # 产品需求文档 (PRD) 存放目录
│   ├── AI-Plat-Dev-PRD.md        # V1.0版本PRD文档
│   ├── final_ai_plat_prd.md      # V2.0版本PRD文档
│   ├── nexusmind_os_v3_prd.md    # V3.0版本PRD文档 (NexusMind OS)
│   ├── nexusmind_os_aiplat_v3.0_prd_final.md  # V3.0最终版PRD文档
│   └── NexusMind_OS_AIPlat_V3.0_PRD_Integrated.md  # V3.0集成版PRD文档 (最新整合版)
├── archive/                  # 归档文档目录
│   └── ARCHIVE-INDEX.md          # 归档文档索引
├── archives/                 # 备份归档目录
├── platform/                 # 平台代码实现目录
│   ├── agents/                   # 智能体系统相关代码
│   ├── config/                   # 配置文件
│   ├── data/                     # 数据相关文件
│   ├── examples/                 # 示例代码
│   ├── ontology/                 # 本体论模块相关代码
│   ├── src/                      # 源代码
│   ├── vibecoding/               # Vibecoding模块相关代码
│   ├── test_enhanced_features.py # 测试增强功能脚本
│   └── verify_integration.py     # 验证集成脚本
├── utils/                    # 工具脚本目录
│   ├── document_processor.py     # 文档处理工具
│   ├── docx_to_text.py           # DOCX转文本工具
│   ├── convert_docx.bat          # 批处理转换工具
│   └── DOCUMENT-PROCESSOR-README.md  # 文档处理器说明
└── README.md                 # 项目说明文档
└── DIRECTORY_STRUCTURE.md    # 当前目录结构说明 (本文档)
```

## 目录内容说明

### docs/ - 文档目录
- **用途**: 存放项目相关的各类文档
- **内容**: 开发文档、平台概览、开发指南、完成笔记、集成报告等

### specs/ - 规格说明目录
- **用途**: 存放系统设计和技术规格说明文档
- **内容**: 各种技术规格和设计规范文档

### prd_docs/ - 产品需求文档目录
- **用途**: 存放所有版本的产品需求文档 (PRD)
- **内容**:
  - V1.0: AI-Plat V1.0版本的PRD文档
  - V2.0: AI-Plat V2.0版本的PRD文档，增加了MCP协议
  - V3.0: NexusMind OS (AI-Plat V3.0)版本的PRD文档，升级为AI操作系统

### archive/ - 归档目录
- **用途**: 存放历史文档和归档文件
- **内容**: 归档文档索引和其他不再活跃使用的文档

### archives/ - 备份归档目录
- **用途**: 用于存放额外的备份和归档资料

### platform/ - 平台代码目录
- **用途**: 存放AI-Plat平台的实现代码
- **内容**:
  - agents/: Skill Agent框架和智能体系统
  - config/: 系统配置文件
  - data/: 数据处理相关文件
  - examples/: 使用示例和演示代码
  - ontology/: 本体论驱动的数据模块
  - src/: 核心源代码
  - vibecoding/: Vibecoding开发模块
  - test_enhanced_features.py: 测试增强功能的脚本
  - verify_integration.py: 验证集成的脚本

### utils/ - 工具目录
- **用途**: 存放各种实用工具脚本
- **内容**: 
  - document_processor.py: 文档处理工具
  - docx_to_text.py: DOCX转文本工具
  - convert_docx.bat: 批处理转换工具
  - DOCUMENT-PROCESSOR-README.md: 文档处理器说明

## 版本演进

- **V1.0 (AI-Plat)**: 基础AI平台，包含本体论、智能体和Vibecoding三大核心能力
- **V2.0 (AI-Plat)**: 增加八层架构设计，引入MCP (Model Connection Protocol) 模块
- **V3.0 (NexusMind OS)**: 升级为AI操作系统，增强自主代理能力，引入智能决策层

## 文件保留策略

- PRD文档: 所有版本的PRD文档均已保留，按版本分类存储
- 代码文件: 保留平台实现代码，便于后续开发和维护
- 工具脚本: 保留有用的工具脚本
- 临时文件: 已清理不必要的临时文件和重复文件