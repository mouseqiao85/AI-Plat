# AI-Plat 平台详细开发文档

## 概述

AI-Plat是一个创新的人工智能平台，整合了三大核心技术模块：
- **本体论驱动的数据模块**：基于语义网标准构建知识表示和推理系统
- **Skill Agent智能体模块**：实现可扩展的AI技能和任务编排
- **Vibecoding大模型驱动开发模块**：通过大模型辅助代码生成和开发

## 项目架构

```
AI-Plat/
├── platform/                 # 核心平台代码
│   ├── main.py              # 主入口程序
│   ├── ai_plat_platform.py  # AI-Plat平台主类
│   ├── requirements.txt     # 依赖包列表
│   ├── README.md           # 使用说明
│   ├── .env.example        # 环境变量示例
│   ├── Dockerfile          # Docker部署配置
│   ├── deploy.py           # 部署脚本
│   ├── config/             # 配置模块
│   │   └── settings.py     # 应用配置
│   ├── agents/             # 智能体模块
│   │   ├── __init__.py
│   │   ├── skill_registry.py  # 技能注册中心
│   │   ├── skill_agent.py     # 技能代理
│   │   └── agent_orchestrator.py  # 智能体编排器
│   ├── ontology/           # 本体论模块
│   │   ├── __init__.py
│   │   ├── ontology_manager.py  # 本体管理器
│   │   ├── inference_engine.py  # 推理引擎
│   │   └── data_fusioner.py     # 数据融合器
│   ├── vibecoding/         # Vibecoding模块
│   │   ├── __init__.py
│   │   ├── code_analyzer.py     # 代码分析器
│   │   ├── code_generator.py    # 代码生成器
│   │   └── notebook_interface.py # Jupyter Notebook接口
│   ├── examples/           # 示例代码
│   │   └── integration_example.py # 集成示例
│   └── ontology/definitions/  # 本体定义文件
│       └── model_asset_ontology.ttl # 模型资产管理本体
├── AI-Plat-Dev.md          # 开发指南
├── AI-Plat-Development.md  # 开发文档
├── AI-Plat-Dev-PRD.md     # 产品需求文档
└── README.md              # 项目概述
```

## 核心模块详解

### 0. MCP (Model Connection Protocol) 模块
AI-Plat平台新增了MCP (Model Connection Protocol) 模块，允许将机器学习和深度学习模型封装为可通过网络调用的工具。这个功能使得一个模型可以调用另一个模型，形成模型间的协作网络。

#### 0.1 MCP Server (mcp_server.py)
实现了MCP服务器功能，可以将本地模型封装为可通过HTTP调用的服务。

主要功能：
- 模型注册：将本地模型注册为可通过MCP调用的服务
- HTTP接口：提供RESTful API供外部调用
- 参数传递：支持操作类型、输入数据和参数的传递
- 结果返回：标准化的结果格式

```python
from mcp_server import MCPServer, ExampleModels

# 创建MCP服务器
server = MCPServer(host="localhost", port=8001)

# 注册模型
server.register_model(
    "image_classifier", 
    ExampleModels.image_classifier,
    "An example image classification model"
)

# 启动服务器
server.start_server()
```

#### 0.2 MCP Client (mcp_client.py)
实现了MCP客户端功能，可以从AI-Plat平台调用远程MCP服务器上的模型。

主要功能：
- 远程调用：调用远程MCP服务器上的模型
- 模型发现：查询远程服务器上可用的模型
- 健康检查：检查远程服务器状态
- 工具适配：将远程模型调用封装为本地工具

#### 0.3 MCP与AI-Plat集成
MCP功能已完全集成到AI-Plat的智能体系统中，通过专门的技能实现。

```python
# 在AI-Plat中使用MCP技能
await agent.add_task(
    name="Remote Model Call",
    skill_id="mcp_call_model",
    parameters={
        "server_url": "http://remote-server:8000",
        "model_name": "image_classifier",
        "input_data": "image_data"
    }
)
```

### 1. 本体论驱动的数据模块

#### 1.1 本体管理器 (ontology_manager.py)

实现了OWL本体的CRUD操作，支持RDF三元组存储和查询。

```python
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL
import json
import os
from typing import Dict, List, Any, Optional

class OntologyManager:
    def __init__(self, storage_path: str = "./ontology_store"):
        self.storage_path = storage_path
        self.graph = Graph()
        self.ns = {
            'rdf': Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
            'rdfs': Namespace("http://www.w3.org/2000/01/rdf-schema#"),
            'owl': Namespace("http://www.w3.org/2002/07/owl#"),
            'aiplat': Namespace("http://ai-plat.org/core#")
        }
        # 绑定命名空间
        for prefix, namespace in self.ns.items():
            self.graph.bind(prefix, namespace)
        
        # 确保存储目录存在
        os.makedirs(storage_path, exist_ok=True)
        
    def create_entity(self, entity_id: str, entity_type: str, label: str = ""):
        """创建实体 - 类、个体或属性"""
        uri = self.ns['aiplat'][entity_id]
        
        if entity_type.lower() == "class":
            self.graph.add((uri, RDF.type, OWL.Class))
        elif entity_type.lower() == "objectproperty":
            self.graph.add((uri, RDF.type, OWL.ObjectProperty))
        elif entity_type.lower() == "dataproperty":
            self.graph.add((uri, RDF.type, OWL.DatatypeProperty))
        elif entity_type.lower() == "namedindividual":
            self.graph.add((uri, RDF.type, OWL.NamedIndividual))
        
        if label:
            self.graph.add((uri, RDFS.label, Literal(label)))
    
    def create_relationship(self, subject_id: str, predicate_uri: str, object_id: str):
        """创建关系 - 三元组 (主语，谓语，宾语)"""
        subject_uri = self.ns['aiplat'][subject_id]
        predicate_uri = URIRef(predicate_uri)
        
        # 如果object_id是预定义的命名空间URI，则直接使用
        if ':' in object_id and '://' in object_id:
            object_uri = URIRef(object_id)
        else:
            object_uri = self.ns['aiplat'][object_id]
        
        self.graph.add((subject_uri, predicate_uri, object_uri))
    
    def query_entities(self, entity_type: str = None) -> List[Dict[str, str]]:
        """查询实体"""
        if entity_type and entity_type.lower() == "class":
            query = f"""
            SELECT ?entity ?label WHERE {{
                ?entity rdf:type owl:Class .
                OPTIONAL {{ ?entity rdfs:label ?label . }}
            }}
            """
        elif entity_type and entity_type.lower() == "namedindividual":
            query = f"""
            SELECT ?entity ?label WHERE {{
                ?entity rdf:type owl:NamedIndividual .
                OPTIONAL {{ ?entity rdfs:label ?label . }}
            }}
            """
        else:
            query = f"""
            SELECT ?entity ?type ?label WHERE {{
                ?entity rdf:type ?type .
                FILTER(?type IN (owl:Class, owl:NamedIndividual, owl:ObjectProperty, owl:DatatypeProperty))
                OPTIONAL {{ ?entity rdfs:label ?label . }}
            }}
            """
        
        results = []
        for row in self.graph.query(query):
            result = {
                "entity": str(row[0]),
                "type": str(row[1]) if len(row) > 1 else "",
                "label": str(row[2]) if len(row) > 2 else ""
            }
            results.append(result)
        
        return results
    
    def save_ontology(self, filename: str):
        """保存本体到文件"""
        filepath = os.path.join(self.storage_path, f"{filename}.ttl")
        self.graph.serialize(destination=filepath, format='turtle')
        return filepath
    
    def load_ontology(self, filename: str):
        """从文件加载本体"""
        filepath = os.path.join(self.storage_path, f"{filename}.ttl")
        if os.path.exists(filepath):
            self.graph.parse(filepath, format='turtle')
            return True
        return False
```

#### 1.2 推理引擎 (inference_engine.py)

实现了基于规则的推理功能。

```python
from .ontology_manager import OntologyManager
from rdflib import URIRef
from typing import List, Dict, Any

class InferenceEngine:
    def __init__(self, ontology_manager: OntologyManager):
        self.ontology_manager = ontology_manager
        self.rules = []
    
    def add_rule(self, rule: Dict[str, Any]):
        """添加推理规则"""
        self.rules.append(rule)
    
    def forward_chain(self) -> List[Dict[str, Any]]:
        """前向链式推理"""
        inferred_triples = []
        
        # 简单的类型继承推理
        query = """
        SELECT ?subclass ?superclass WHERE {
            ?subclass rdfs:subClassOf ?superclass .
        }
        """
        
        for row in self.ontology_manager.graph.query(query):
            subclass = str(row[0])
            superclass = str(row[1])
            
            # 为每个属于subclass的实例添加到superclass
            instance_query = f"""
            SELECT ?instance WHERE {{
                ?instance rdf:type <{subclass}> .
            }}
            """
            
            for inst_row in self.ontology_manager.graph.query(instance_query):
                instance = str(inst_row[0])
                new_triple = {
                    'subject': instance,
                    'predicate': 'rdf:type',
                    'object': superclass
                }
                
                # 检查是否已存在此关系
                triple_exists = False
                check_query = f"""
                ASK WHERE {{
                    <{instance}> rdf:type <{superclass}> .
                }}
                """
                
                if not self.ontology_manager.graph.query(check_query).askAnswer:
                    # 添加新的三元组
                    subj = URIRef(instance)
                    pred = self.ontology_manager.ns['rdf']['type']
                    obj = URIRef(superclass)
                    self.ontology_manager.graph.add((subj, pred, obj))
                    
                    inferred_triples.append(new_triple)
        
        return inferred_triples
```

#### 1.3 数据融合器 (data_fusioner.py)

实现了多源数据的融合功能。

```python
from .ontology_manager import OntologyManager
from typing import List, Dict, Any
import hashlib

class DataFusioner:
    def __init__(self, ontology_manager: OntologyManager):
        self.ontology_manager = ontology_manager
    
    def fuse_data_sources(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """融合多个数据源"""
        fused_data = {
            'entities': {},
            'relationships': [],
            'provenance': []  # 来源信息
        }
        
        for source in sources:
            source_id = source.get('id', hashlib.md5(str(source).encode()).hexdigest()[:8])
            data = source.get('data', {})
            
            # 处理实体
            for entity_id, entity_data in data.get('entities', {}).items():
                if entity_id not in fused_data['entities']:
                    fused_data['entities'][entity_id] = {
                        'types': set(),
                        'properties': {},
                        'sources': set()
                    }
                
                # 合并类型
                if 'types' in entity_data:
                    fused_data['entities'][entity_id]['types'].update(entity_data['types'])
                
                # 合并属性
                if 'properties' in entity_data:
                    for prop, value in entity_data['properties'].items():
                        if prop not in fused_data['entities'][entity_id]['properties']:
                            fused_data['entities'][entity_id]['properties'][prop] = set()
                        if isinstance(value, list):
                            fused_data['entities'][entity_id]['properties'][prop].update(value)
                        else:
                            fused_data['entities'][entity_id]['properties'][prop].add(value)
                
                # 记录数据来源
                fused_data['entities'][entity_id]['sources'].add(source_id)
            
            # 处理关系
            for rel in data.get('relationships', []):
                fused_data['relationships'].append({
                    **rel,
                    'source': source_id
                })
            
            # 记录来源信息
            fused_data['provenance'].append({
                'source_id': source_id,
                'description': source.get('description', ''),
                'timestamp': source.get('timestamp', '')
            })
        
        # 转换sets为lists以便JSON序列化
        for entity_id, entity_data in fused_data['entities'].items():
            entity_data['types'] = list(entity_data['types'])
            entity_data['sources'] = list(entity_data['sources'])
            for prop, values in entity_data['properties'].items():
                entity_data['properties'][prop] = list(values)
        
        return fused_data
```

### 2. Skill Agent智能体模块

#### 2.1 技能注册中心 (skill_registry.py)

实现了动态技能注册和管理。

```python
from enum import Enum
from typing import Dict, Callable, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import inspect
import asyncio

class SkillCategory(Enum):
    DATA_PROCESSING = "data_processing"
    ML_MODEL = "ml_model"
    TEXT_GENERATION = "text_generation"
    IMAGE_PROCESSING = "image_processing"
    AUDIO_PROCESSING = "audio_processing"
    WORKFLOW = "workflow"
    UTILITY = "utility"

@dataclass
class SkillMetadata:
    name: str
    description: str
    version: str
    author: str
    category: SkillCategory
    tags: List[str]
    parameters: Dict[str, Any]
    return_type: str
    created_at: datetime

class SkillRegistry:
    def __init__(self):
        self.skills: Dict[str, 'RegisteredSkill'] = {}
        self.categories: Dict[SkillCategory, List[str]] = {}
    
    def register_skill(
        self,
        name: str,
        description: str = "",
        version: str = "1.0.0",
        author: str = "Unknown",
        category: SkillCategory = SkillCategory.UTILITY,
        tags: List[str] = None
    ):
        """装饰器：注册技能"""
        def decorator(func: Callable) -> Callable:
            # 获取函数签名
            sig = inspect.signature(func)
            params = {}
            for param_name, param in sig.parameters.items():
                params[param_name] = {
                    'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                    'default': param.default if param.default != inspect.Parameter.empty else None
                }
            
            # 创建技能元数据
            metadata = SkillMetadata(
                name=name,
                description=description,
                version=version,
                author=author,
                category=category,
                tags=tags or [],
                parameters=params,
                return_type=str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else 'Any',
                created_at=datetime.now()
            )
            
            # 注册技能
            registered_skill = RegisteredSkill(
                func=func,
                metadata=metadata
            )
            
            self.skills[name] = registered_skill
            
            # 按类别索引
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(name)
            
            return func
        return decorator
    
    def get_skill(self, name: str) -> Optional['RegisteredSkill']:
        """获取技能"""
        return self.skills.get(name)
    
    def get_skills_by_category(self, category: SkillCategory) -> List['RegisteredSkill']:
        """按类别获取技能"""
        skill_names = self.categories.get(category, [])
        return [self.skills[name] for name in skill_names if name in self.skills]
    
    def list_all_skills(self) -> List[SkillMetadata]:
        """列出所有技能的元数据"""
        return [skill.metadata for skill in self.skills.values()]
    
    async def execute_skill(self, name: str, **kwargs) -> Any:
        """异步执行技能"""
        skill = self.get_skill(name)
        if not skill:
            raise ValueError(f"Skill '{name}' not found")
        
        # 检查参数
        sig = inspect.signature(skill.func)
        try:
            bound_args = sig.bind(**kwargs)
            bound_args.apply_defaults()
        except TypeError as e:
            raise ValueError(f"Invalid arguments for skill '{name}': {str(e)}")
        
        # 执行技能
        result = skill.func(*bound_args.args, **bound_args.kwargs)
        
        # 如果是协程，则等待其完成
        if asyncio.iscoroutine(result):
            result = await result
        
        return result

@dataclass
class RegisteredSkill:
    func: Callable
    metadata: SkillMetadata

# 全局技能注册表
global_skill_registry = SkillRegistry()
```

#### 2.2 技能代理 (skill_agent.py)

实现了基于技能的智能体。

```python
import asyncio
import uuid
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
from .skill_registry import global_skill_registry, SkillCategory

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class Task:
    def __init__(
        self,
        task_id: str,
        name: str,
        description: str,
        skill_id: str,
        parameters: Dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM
    ):
        self.id = task_id
        self.name = name
        self.description = description
        self.skill_id = skill_id
        self.parameters = parameters
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
    
    def start(self):
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
    
    def complete(self, result: Any):
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result
    
    def fail(self, error: str):
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error

class SkillAgent:
    def __init__(self, name: str, description: str, skills: List[str] = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.skills = skills or []
        self.tasks: Dict[str, Task] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        self._is_initialized = False
    
    async def initialize(self):
        """初始化代理"""
        # 验证技能是否存在
        valid_skills = []
        for skill_name in self.skills:
            if global_skill_registry.get_skill(skill_name):
                valid_skills.append(skill_name)
            else:
                print(f"Warning: Skill '{skill_name}' not found")
        
        self.skills = valid_skills
        self._is_initialized = True
        
        # 触发初始化事件
        await self._emit_event("initialized", {"agent_id": self.id, "skills_count": len(self.skills)})
    
    async def add_task(
        self,
        name: str,
        description: str,
        skill_id: str,
        parameters: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> str:
        """添加任务"""
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        # 验证技能是否存在
        if skill_id not in self.skills:
            raise ValueError(f"Skill '{skill_id}' not available to this agent")
        
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            name=name,
            description=description,
            skill_id=skill_id,
            parameters=parameters or {},
            priority=priority
        )
        
        self.tasks[task_id] = task
        
        # 触发任务添加事件
        await self._emit_event("task_added", {"task_id": task_id, "agent_id": self.id})
        
        return task_id
    
    async def execute_task(self, task_id: str) -> Any:
        """执行任务"""
        if task_id not in self.tasks:
            raise ValueError(f"Task '{task_id}' not found")
        
        task = self.tasks[task_id]
        if task.status != TaskStatus.PENDING:
            raise ValueError(f"Task '{task_id}' is not in PENDING status")
        
        task.start()
        
        try:
            # 执行技能
            result = await global_skill_registry.execute_skill(
                task.skill_id,
                **task.parameters
            )
            
            task.complete(result)
            
            # 触发任务完成事件
            await self._emit_event("task_completed", {
                "task_id": task_id,
                "agent_id": self.id,
                "result": result
            })
            
            return result
        except Exception as e:
            task.fail(str(e))
            
            # 触发任务失败事件
            await self._emit_event("task_failed", {
                "task_id": task_id,
                "agent_id": self.id,
                "error": str(e)
            })
            
            raise e
    
    async def execute_all_tasks(self):
        """执行所有任务"""
        pending_tasks = [tid for tid, task in self.tasks.items() if task.status == TaskStatus.PENDING]
        
        # 按优先级排序
        sorted_tasks = sorted(
            pending_tasks,
            key=lambda x: self.tasks[x].priority.value,
            reverse=True
        )
        
        results = {}
        for task_id in sorted_tasks:
            try:
                result = await self.execute_task(task_id)
                results[task_id] = result
            except Exception as e:
                results[task_id] = {"error": str(e)}
        
        return results
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None
        return self.tasks[task_id].status
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """获取任务结果"""
        if task_id not in self.tasks:
            return None
        return self.tasks[task_id].result
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """触发事件"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                # 如果处理器是协程，则等待它完成
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_type, data)
                else:
                    handler(event_type, data)
    
    def on(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def remove_handler(self, event_type: str, handler: Callable):
        """移除事件处理器"""
        if event_type in self.event_handlers:
            if handler in self.event_handlers[event_type]:
                self.event_handlers[event_type].remove(handler)
```

#### 2.3 智能体编排器 (agent_orchestrator.py)

实现了多智能体协调和工作流管理。

```python
import asyncio
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
from .skill_agent import SkillAgent, Task, TaskStatus

class WorkflowStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskDependencyType(Enum):
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"      # 并行执行
    CONDITIONAL = "conditional"  # 条件执行

class WorkflowTask:
    def __init__(
        self,
        task_id: str,
        agent: SkillAgent,
        task_name: str,
        task_description: str,
        skill_id: str,
        parameters: Dict[str, Any],
        dependencies: List[str] = None,
        condition: str = None
    ):
        self.task_id = task_id
        self.agent = agent
        self.task_name = task_name
        self.task_description = task_description
        self.skill_id = skill_id
        self.parameters = parameters
        self.dependencies = dependencies or []
        self.condition = condition  # 执行条件
        self.status = TaskStatus.PENDING
        self.result: Optional[Any] = None
        self.error: Optional[str] = None

class AgentOrchestrator:
    def __init__(self):
        self.agents: Dict[str, SkillAgent] = {}
        self.workflows: Dict[str, 'Workflow'] = {}
        self.global_context: Dict[str, Any] = {}
    
    def register_agent(self, agent: SkillAgent):
        """注册智能体"""
        self.agents[agent.id] = agent
    
    def create_workflow(self, name: str, description: str = "") -> 'Workflow':
        """创建工作流"""
        workflow = Workflow(name, description, self)
        self.workflows[workflow.id] = workflow
        return workflow
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """执行工作流"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        workflow = self.workflows[workflow_id]
        return await workflow.execute()

class Workflow:
    def __init__(self, name: str, description: str, orchestrator: AgentOrchestrator):
        self.id = f"wf_{int(datetime.now().timestamp())}"
        self.name = name
        self.description = description
        self.orchestrator = orchestrator
        self.tasks: Dict[str, WorkflowTask] = {}
        self.status = WorkflowStatus.CREATED
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.context: Dict[str, Any] = {}  # 工作流级别的上下文
    
    def add_task(
        self,
        agent_id: str,
        task_name: str,
        task_description: str,
        skill_id: str,
        parameters: Dict[str, Any] = None,
        dependencies: List[str] = None,
        condition: str = None
    ) -> str:
        """添加任务到工作流"""
        if agent_id not in self.orchestrator.agents:
            raise ValueError(f"Agent '{agent_id}' not found in orchestrator")
        
        agent = self.orchestrator.agents[agent_id]
        task_id = f"task_{len(self.tasks)}"
        
        workflow_task = WorkflowTask(
            task_id=task_id,
            agent=agent,
            task_name=task_name,
            task_description=task_description,
            skill_id=skill_id,
            parameters=parameters or {},
            dependencies=dependencies or [],
            condition=condition
        )
        
        self.tasks[task_id] = workflow_task
        return task_id
    
    async def execute(self) -> Dict[str, Any]:
        """执行工作流"""
        if self.status != WorkflowStatus.CREATED:
            raise ValueError("Workflow has already been executed or is running")
        
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.now()
        
        results = {}
        errors = {}
        
        try:
            # 按依赖关系排序任务
            ordered_tasks = self._order_tasks_by_dependencies()
            
            for task_id in ordered_tasks:
                task = self.tasks[task_id]
                
                # 检查前置依赖
                dependencies_met = True
                for dep_id in task.dependencies:
                    dep_task = self.tasks[dep_id]
                    if dep_task.status != TaskStatus.COMPLETED:
                        dependencies_met = False
                        break
                
                if not dependencies_met:
                    task.status = TaskStatus.CANCELLED
                    errors[task_id] = f"Dependencies not met: {task.dependencies}"
                    continue
                
                # 检查执行条件
                if task.condition:
                    condition_met = self._evaluate_condition(task.condition)
                    if not condition_met:
                        task.status = TaskStatus.CANCELLED
                        continue
                
                # 执行任务
                try:
                    # 更新任务参数中的上下文变量
                    processed_params = self._process_parameters(task.parameters)
                    
                    # 在代理上添加任务
                    inner_task_id = await task.agent.add_task(
                        name=task.task_name,
                        description=task.task_description,
                        skill_id=task.skill_id,
                        parameters=processed_params
                    )
                    
                    # 执行任务
                    result = await task.agent.execute_task(inner_task_id)
                    
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    
                    # 将结果存入工作流上下文
                    self.context[f"result_{task.task_id}"] = result
                    results[task_id] = result
                    
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    errors[task_id] = str(e)
            
            # 检查是否有失败的任务
            failed_tasks = [tid for tid, t in self.tasks.items() if t.status == TaskStatus.FAILED]
            if failed_tasks:
                self.status = WorkflowStatus.FAILED
            else:
                self.status = WorkflowStatus.COMPLETED
            
        finally:
            self.completed_at = datetime.now()
        
        return {
            "workflow_id": self.id,
            "status": self.status.value,
            "results": results,
            "errors": errors,
            "tasks_count": len(self.tasks),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    def _order_tasks_by_dependencies(self) -> List[str]:
        """按依赖关系对任务进行拓扑排序"""
        from collections import defaultdict, deque
        
        graph = defaultdict(list)
        in_degree = {task_id: 0 for task_id in self.tasks}
        
        # 构建图和入度
        for task_id, task in self.tasks.items():
            for dep_id in task.dependencies:
                if dep_id in self.tasks:  # 确保依赖存在
                    graph[dep_id].append(task_id)
                    in_degree[task_id] += 1
        
        # 拓扑排序
        queue = deque([task_id for task_id, degree in in_degree.items() if degree == 0])
        ordered = []
        
        while queue:
            task_id = queue.popleft()
            ordered.append(task_id)
            
            for neighbor in graph[task_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查是否有循环依赖
        if len(ordered) != len(self.tasks):
            raise ValueError("Circular dependency detected in workflow tasks")
        
        return ordered
    
    def _evaluate_condition(self, condition: str) -> bool:
        """简单条件评估（实际应用中应使用更安全的方法）"""
        # 这里只是简单示例，实际应用中应使用更安全的表达式求值
        try:
            # 用上下文变量替换占位符
            evaluated_condition = condition.format(**self.context)
            # 简单求值
            return bool(eval(evaluated_condition))
        except:
            return False
    
    def _process_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理参数中的上下文变量"""
        import re
        
        processed = {}
        for key, value in params.items():
            if isinstance(value, str):
                # 查找 {variable_name} 格式的变量
                matches = re.findall(r'\{([^}]+)\}', value)
                processed_value = value
                for var_name in matches:
                    if var_name in self.context:
                        processed_value = processed_value.replace(f'{{{var_name}}}', str(self.context[var_name]))
                processed[key] = processed_value
            else:
                processed[key] = value
        
        return processed
```

### 3. Vibecoding大模型驱动开发模块

#### 3.1 代码分析器 (code_analyzer.py)

实现了对代码的静态分析。

```python
import ast
import inspect
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class FunctionInfo:
    name: str
    args: List[str]
    return_annotation: Optional[str]
    docstring: Optional[str]
    decorators: List[str]
    start_line: int
    end_line: int

@dataclass
class ClassInfo:
    name: str
    bases: List[str]
    methods: List[FunctionInfo]
    docstring: Optional[str]
    start_line: int
    end_line: int

@dataclass
class ModuleInfo:
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    imports: List[str]
    docstring: Optional[str]

class CodeAnalyzer:
    def __init__(self):
        pass
    
    def analyze_file(self, file_path: str) -> ModuleInfo:
        """分析Python文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        return self.analyze_source(source_code)
    
    def analyze_source(self, source_code: str) -> ModuleInfo:
        """分析源代码字符串"""
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in source code: {e}")
        
        module_info = ModuleInfo(
            functions=[],
            classes=[],
            imports=[],
            docstring=ast.get_docstring(tree)
        )
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.col_offset == 0:  # 顶级函数
                    func_info = self._extract_function_info(node, source_code)
                    module_info.functions.append(func_info)
            elif isinstance(node, ast.AsyncFunctionDef):
                if node.col_offset == 0:  # 顶级异步函数
                    func_info = self._extract_function_info(node, source_code)
                    module_info.functions.append(func_info)
            elif isinstance(node, ast.ClassDef):
                if node.col_offset == 0:  # 顶级类
                    class_info = self._extract_class_info(node, source_code)
                    module_info.classes.append(class_info)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                import_str = ast.unparse(node)  # Python 3.9+
                module_info.imports.append(import_str)
        
        return module_info
    
    def _extract_function_info(self, node: ast.AST, source_code: str) -> FunctionInfo:
        """提取函数信息"""
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        
        # 处理默认值
        defaults_start = len(args) - len(node.args.defaults)
        for i, default in enumerate(node.args.defaults):
            idx = defaults_start + i
            if idx < len(args):
                # 默认值不能直接从AST获取，这里只记录参数名
                pass
        
        return_annotation = None
        if node.returns:
            return_annotation = ast.unparse(node.returns)
        
        decorators = [ast.unparse(dec) for dec in node.decorator_list]
        
        lines = source_code.split('\n')
        start_line = node.lineno
        end_line = getattr(node, 'end_lineno', node.lineno)
        
        return FunctionInfo(
            name=node.name,
            args=args,
            return_annotation=return_annotation,
            docstring=ast.get_docstring(node),
            decorators=decorators,
            start_line=start_line,
            end_line=end_line
        )
    
    def _extract_class_info(self, node: ast.AST, source_code: str) -> ClassInfo:
        """提取类信息"""
        bases = [ast.unparse(base) for base in node.bases]
        
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._extract_function_info(item, source_code)
                methods.append(method_info)
        
        lines = source_code.split('\n')
        start_line = node.lineno
        end_line = getattr(node, 'end_lineno', node.lineno)
        
        return ClassInfo(
            name=node.name,
            bases=bases,
            methods=methods,
            docstring=ast.get_docstring(node),
            start_line=start_line,
            end_line=end_line
        )
    
    def analyze_object(self, obj: Any) -> Dict[str, Any]:
        """分析Python对象"""
        info = {
            'type': type(obj).__name__,
            'module': getattr(obj, '__module__', None),
            'docstring': inspect.getdoc(obj),
            'source_file': None,
            'methods': [],
            'properties': [],
            'signature': None
        }
        
        try:
            # 获取源文件
            info['source_file'] = inspect.getfile(obj)
        except:
            pass
        
        # 获取签名（如果是可调用对象）
        if callable(obj):
            try:
                sig = inspect.signature(obj)
                info['signature'] = str(sig)
            except (ValueError, TypeError):
                pass
        
        # 获取方法和属性
        for attr_name in dir(obj):
            if not attr_name.startswith('_'):  # 排除私有属性
                attr = getattr(obj, attr_name)
                if callable(attr):
                    info['methods'].append({
                        'name': attr_name,
                        'callable': True,
                        'signature': str(inspect.signature(attr)) if callable(attr) else None
                    })
                else:
                    info['properties'].append({
                        'name': attr_name,
                        'value_type': type(attr).__name__
                    })
        
        return info
```

#### 3.2 代码生成器 (code_generator.py)

实现了基于模板和AI的大模型代码生成。

```python
import os
from typing import Dict, Any, List, Optional
from jinja2 import Template, Environment, FileSystemLoader
import json

class CodeGenerator:
    def __init__(self, templates_dir: str = None):
        if templates_dir and os.path.exists(templates_dir):
            self.env = Environment(loader=FileSystemLoader(templates_dir))
        else:
            self.env = Environment()
    
    def generate_from_template(
        self, 
        template_str: str, 
        context: Dict[str, Any],
        output_file: Optional[str] = None
    ) -> str:
        """基于模板生成代码"""
        template = self.env.from_string(template_str)
        generated_code = template.render(**context)
        
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(generated_code)
        
        return generated_code
    
    def create_class_template(self) -> str:
        """创建类定义模板"""
        return """
class {{ class_name }}({{ base_classes|join(', ') }}):
    {% if class_docstring %}
    \"\"\"{{ class_docstring }}\"\"\"
    {% endif %}
    
    def __init__(self{% for param in constructor_params %}, {{ param.name }}{% if param.default %}={{ param.default }}{% endif %}{% endfor %}):
        {% for statement in constructor_body %}
        {{ statement }}
        {% endfor %}
    
    {% for method in methods %}
    def {{ method.name }}(self{% for param in method.params %}, {{ param }}{% endfor %}) -> {{ method.return_type }}:
        \"\"\"{{ method.docstring }}\"\"\"
        {% for statement in method.body %}
        {{ statement }}
        {% endfor %}
        {% if method.return_value %}return {{ method.return_value }}{% endif %}
    
    {% endfor %}
"""
    
    def create_function_template(self) -> str:
        """创建函数定义模板"""
        return """
{% if func_docstring %}
def {{ func_name }}({% for param in params %}{{ param.name }}{% if param.type %}: {{ param.type }}{% endif %}{% if param.default %} = {{ param.default }}{% endif %}{% if not loop.last %}, {% endif %}{% endfor %}) -> {{ return_type }}:
    \"\"\"{{ func_docstring }}\"\"\"
    {% for statement in body %}
    {{ statement }}
    {% endfor %}
    {% if return_value %}return {{ return_value }}{% endif %}
{% else %}
def {{ func_name }}({% for param in params %}{{ param.name }}{% if param.type %}: {{ param.type }}{% endif %}{% if param.default %} = {{ param.default }}{% endif %}{% if not loop.last %}, {% endif %}{% endfor %}) -> {{ return_type }}:
    {% for statement in body %}
    {{ statement }}
    {% endfor %}
    {% if return_value %}return {{ return_value }}{% endif %}
{% endif %}
"""
    
    def create_api_endpoint_template(self) -> str:
        """创建API端点模板"""
        return """
from flask import Flask, request, jsonify
{% if auth_required %}from functools import wraps
import jwt{% endif %}

app = Flask(__name__)

{% if auth_required %}
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        return f(*args, **kwargs)
    return decorated
{% endif %}

@app.route('{{ endpoint_path }}', methods={{ methods|tojson }})
{% if auth_required %}@token_required{% endif %}
def {{ endpoint_function_name }}():
    {% if request_handling %}
    if request.method == 'POST':
        data = request.get_json()
        # TODO: Add your business logic here
        result = process_request(data)
        return jsonify(result)
    elif request.method == 'GET':
        # TODO: Add your GET handling logic here
        result = get_data()
        return jsonify(result)
    {% else %}
    # TODO: Add your endpoint logic here
    return jsonify({'message': 'Endpoint implementation required'})
    {% endif %}

def process_request(data):
    # Process the request data
    return {'status': 'success', 'received_data': data}

def get_data():
    # Get data for GET request
    return {'data': 'sample data'}

if __name__ == '__main__':
    app.run(debug={{ debug_mode }}, host='{{ host }}', port={{ port }})
"""
    
    def generate_crud_service(self, model_name: str, fields: List[Dict[str, str]]) -> str:
        """生成CRUD服务代码"""
        template = """
class {{ model_name }}Service:
    def __init__(self, db_connection):
        self.db = db_connection
        self.table_name = "{{ model_name.lower() }}"
    
    async def create(self, {{ model_name.lower() }}_data: dict) -> dict:
        \"\"\"创建新的{{ model_name }}记录\"\"\"
        columns = ', '.join({{ model_name.lower() }}_data.keys())
        placeholders = ', '.join(['?' for _ in {{ model_name.lower() }}_data])
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        
        cursor = await self.db.execute(query, list({{ model_name.lower() }}_data.values()))
        await self.db.commit()
        
        # 返回新创建的记录
        new_id = cursor.lastrowid
        return await self.get(new_id)
    
    async def get(self, id: int) -> dict:
        \"\"\"根据ID获取{{ model_name }}记录\"\"\"
        query = f"SELECT * FROM {self.table_name} WHERE id = ?"
        cursor = await self.db.execute(query, (id,))
        row = await cursor.fetchone()
        
        if row:
            return self._row_to_dict(row)
        return None
    
    async def list(self, limit: int = 10, offset: int = 0) -> list:
        \"\"\"获取{{ model_name }}记录列表\"\"\"
        query = f"SELECT * FROM {self.table_name} LIMIT ? OFFSET ?"
        cursor = await self.db.execute(query, (limit, offset))
        rows = await cursor.fetchall()
        
        return [self._row_to_dict(row) for row in rows]
    
    async def update(self, id: int, {{ model_name.lower() }}_data: dict) -> dict:
        \"\"\"更新{{ model_name }}记录\"\"\"
        set_clause = ', '.join([f"{key} = ?" for key in {{ model_name.lower() }}_data.keys()])
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"
        
        values = list({{ model_name.lower() }}_data.values()) + [id]
        await self.db.execute(query, values)
        await self.db.commit()
        
        return await self.get(id)
    
    async def delete(self, id: int) -> bool:
        \"\"\"删除{{ model_name }}记录\"\"\"
        query = f"DELETE FROM {self.table_name} WHERE id = ?"
        cursor = await self.db.execute(query, (id,))
        await self.db.commit()
        
        return cursor.rowcount > 0
    
    def _row_to_dict(self, row) -> dict:
        \"\"\"将数据库行转换为字典\"\"\"
        if not row:
            return {}
        
        # 假设我们有游标的description属性
        columns = [description[0] for description in row.cursor_description]
        return dict(zip(columns, row))
"""
        
        context = {
            'model_name': model_name,
            'fields': fields
        }
        
        return self.generate_from_template(template, context)
    
    def generate_unit_tests(self, module_path: str, target_functions: List[str] = None) -> str:
        """生成单元测试代码"""
        template = """
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入被测试的模块
from {{ module_path.rsplit('.', 1)[0] if '.' in module_path else module_path }} import *

class Test{{ module_path.split('.')[-1].capitalize() }}(unittest.TestCase):
    {% for func_name in target_functions %}
    def test_{{ func_name }}_basic(self):
        \"\"\"测试 {{ func_name }} 函数的基本功能\"\"\"
        # 准备测试数据
        # test_input = 
        # expected_output = 
        
        # 执行测试
        # actual_output = {{ func_name }}(test_input)
        
        # 验证结果
        # self.assertEqual(actual_output, expected_output)
        pass  # TODO: 实现测试逻辑

    {% endfor %}
    
    def setUp(self):
        \"\"\"测试前的准备工作\"\"\"
        pass
    
    def tearDown(self):
        \"\"\"测试后的清理工作\"\"\"
        pass

if __name__ == '__main__':
    unittest.main()
"""
        
        # 如果没有指定函数，则尝试分析模块获取函数列表
        if not target_functions:
            try:
                import importlib
                module = importlib.import_module(module_path)
                target_functions = [name for name, obj in vars(module).items() 
                                  if callable(obj) and not name.startswith('_')]
            except ImportError:
                target_functions = []
        
        context = {
            'module_path': module_path,
            'target_functions': target_functions
        }
        
        return self.generate_from_template(template, context)
```

#### 3.3 Jupyter Notebook接口 (notebook_interface.py)

实现了与Jupyter Notebook的集成。

```python
import os
import json
import uuid
from typing import Dict, List, Any, Optional
import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell
import subprocess
import tempfile

class VibecodingNotebookInterface:
    def __init__(self, notebook_dir: str = "./notebooks"):
        self.notebook_dir = notebook_dir
        os.makedirs(notebook_dir, exist_ok=True)
        self.active_notebooks: Dict[str, Dict[str, Any]] = {}
    
    def create_notebook(self, name: str, description: str = "") -> str:
        """创建新的笔记本"""
        notebook_id = f"nb_{uuid.uuid4().hex[:8]}"
        
        # 创建新的notebook
        nb = new_notebook()
        nb.metadata = {
            "language_info": {
                "name": "python",
                "version": "3.8.0"
            },
            "description": description
        }
        
        # 添加标题单元格
        title_cell = new_markdown_cell(f"# {name}\n\n{description}")
        nb.cells.append(title_cell)
        
        # 保存到文件
        filepath = os.path.join(self.notebook_dir, f"{notebook_id}_{name.replace(' ', '_')}.ipynb")
        with open(filepath, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        
        # 记录活动笔记本
        self.active_notebooks[notebook_id] = {
            'filepath': filepath,
            'name': name,
            'description': description,
            'cells': len(nb.cells),
            'created_at': str(nb.metadata.get('date_created', ''))
        }
        
        return notebook_id
    
    def load_notebook(self, notebook_id: str) -> Dict[str, Any]:
        """加载笔记本内容"""
        if notebook_id not in self.active_notebooks:
            raise ValueError(f"Notebook '{notebook_id}' not found")
        
        filepath = self.active_notebooks[notebook_id]['filepath']
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        return {
            'id': notebook_id,
            'name': self.active_notebooks[notebook_id]['name'],
            'description': self.active_notebooks[notebook_id]['description'],
            'cells': [{'type': cell.cell_type, 'source': cell.source} for cell in nb.cells]
        }
    
    def add_cell(self, notebook_id: str, cell_type: str, source: str) -> str:
        """向笔记本添加单元格"""
        if notebook_id not in self.active_notebooks:
            raise ValueError(f"Notebook '{notebook_id}' not found")
        
        filepath = self.active_notebooks[notebook_id]['filepath']
        
        # 读取现有笔记本
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        # 创建新单元格
        if cell_type.lower() == 'code':
            cell = new_code_cell(source)
        elif cell_type.lower() == 'markdown':
            cell = new_markdown_cell(source)
        else:
            raise ValueError(f"Unsupported cell type: {cell_type}")
        
        # 添加到笔记本
        nb.cells.append(cell)
        
        # 保存笔记本
        with open(filepath, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        
        return f"cell_{len(nb.cells)-1}"
    
    def update_cell(self, notebook_id: str, cell_index: int, source: str) -> bool:
        """更新笔记本中的单元格"""
        if notebook_id not in self.active_notebooks:
            raise ValueError(f"Notebook '{notebook_id}' not found")
        
        filepath = self.active_notebooks[notebook_id]['filepath']
        
        # 读取现有笔记本
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        if cell_index >= len(nb.cells):
            raise IndexError(f"Cell index {cell_index} out of range")
        
        # 更新单元格内容
        nb.cells[cell_index].source = source
        
        # 保存笔记本
        with open(filepath, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        
        return True
    
    def delete_cell(self, notebook_id: str, cell_index: int) -> bool:
        """删除笔记本中的单元格"""
        if notebook_id not in self.active_notebooks:
            raise ValueError(f"Notebook '{notebook_id}' not found")
        
        filepath = self.active_notebooks[notebook_id]['filepath']
        
        # 读取现有笔记本
        with open(filepath, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        
        if cell_index >= len(nb.cells):
            raise IndexError(f"Cell index {cell_index} out of range")
        
        # 删除单元格
        del nb.cells[cell_index]
        
        # 保存笔记本
        with open(filepath, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)
        
        return True
    
    async def execute_notebook(self, notebook_id: str, kernel_name: str = "python3") -> Dict[str, Any]:
        """执行笔记本"""
        if notebook_id not in self.active_notebooks:
            raise ValueError(f"Notebook '{notebook_id}' not found")
        
        filepath = self.active_notebooks[notebook_id]['filepath']
        
        # 创建临时输出文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ipynb', delete=False) as temp_file:
            temp_filepath = temp_file.name
        
        try:
            # 使用nbconvert执行笔记本
            cmd = [
                "jupyter", "nbconvert", 
                "--to", "notebook",
                "--execute",
                f"--ExecutePreprocessor.timeout=600",  # 10分钟超时
                f"--ExecutePreprocessor.kernel_name={kernel_name}",
                f"--output={temp_filepath[:-6]}",  # 移除.ipynb后缀
                filepath
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=605)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': result.stderr,
                    'executed_cells': 0,
                    'successful_executions': 0,
                    'failed_executions': 0
                }
            
            # 读取执行后的笔记本
            with open(temp_filepath + ".nbconvert.ipynb", 'r', encoding='utf-8') as f:
                executed_nb = nbformat.read(f, as_version=4)
            
            # 分析执行结果
            executed_cells = 0
            successful_executions = 0
            failed_executions = 0
            
            for cell in executed_nb.cells:
                if cell.cell_type == 'code' and 'outputs' in cell:
                    executed_cells += 1
                    # 检查是否有错误输出
                    has_error = any(output.get('output_type') == 'error' for output in cell.outputs)
                    if has_error:
                        failed_executions += 1
                    else:
                        successful_executions += 1
            
            return {
                'success': True,
                'executed_cells': executed_cells,
                'successful_executions': successful_executions,
                'failed_executions': failed_executions,
                'output_file': temp_filepath + ".nbconvert.ipynb"
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Execution timed out after 605 seconds',
                'executed_cells': 0,
                'successful_executions': 0,
                'failed_executions': 0
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'executed_cells': 0,
                'successful_executions': 0,
                'failed_executions': 0
            }
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_filepath)
                temp_output = temp_filepath + ".nbconvert.ipynb"
                if os.path.exists(temp_output):
                    os.unlink(temp_output)
            except:
                pass  # 忽略清理错误
    
    def list_notebooks(self) -> List[Dict[str, Any]]:
        """列出所有笔记本"""
        return [
            {
                'id': nb_id,
                'name': info['name'],
                'description': info['description'],
                'cells_count': info.get('cells', 0),
                'created_at': info.get('created_at', '')
            }
            for nb_id, info in self.active_notebooks.items()
        ]
    
    def export_notebook(self, notebook_id: str, export_format: str = "python") -> str:
        """导出笔记本为其他格式"""
        if notebook_id not in self.active_notebooks:
            raise ValueError(f"Notebook '{notebook_id}' not found")
        
        filepath = self.active_notebooks[notebook_id]['filepath']
        output_path = filepath.replace('.ipynb', f'.{export_format}')
        
        # 使用nbconvert导出
        cmd = [
            "jupyter", "nbconvert",
            f"--to={export_format}",
            f"--output={output_path[:-len(export_format)-1]}",  # 移除.扩展名
            filepath
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Export failed: {result.stderr}")
        
        return output_path
```

## 平台集成示例

以下是如何将三个模块集成在一起的示例：

```python
"""
AI-Plat 平台集成示例
展示本体论、智能体和Vibecoding三大模块如何协同工作
"""

from ontology.ontology_manager import OntologyManager
from agents.skill_agent import SkillAgent
from agents.agent_orchestrator import AgentOrchestrator
from agents.skill_registry import global_skill_registry
from vibecoding.notebook_interface import VibecodingNotebookInterface
from vibecoding.code_generator import CodeGenerator
import asyncio
import uuid
from datetime import datetime

async def integrated_model_lifecycle_example():
    """
    集成示例：完整的模型生命周期管理
    基于上一代平台的模型管理、训练、评估、推理功能
    """
    print("="*60)
    print("🔄 开始执行集成模型生命周期示例")
    print("="*60)
    
    # 1. 使用本体论模块定义模型资产
    print("\n1. 🏗️ 使用本体论模块定义模型资产")
    ontology_mgr = OntologyManager("./tmp_ontology_defs")
    
    # 定义模型类型和属性
    ontology_mgr.create_entity("LargeLanguageModel", "Class", "大语言模型")
    ontology_mgr.create_entity("VisionModel", "Class", "视觉模型")
    ontology_mgr.create_entity("TrainingMethod", "Class", "训练方法")
    ontology_mgr.create_entity("FineTuning", "NamedIndividual", "微调方法")
    ontology_mgr.create_entity("usesTrainingMethod", "ObjectProperty", "使用训练方法")
    
    # 创建具体模型实例
    model_id = f"LLM-{uuid.uuid4().hex[:8]}"
    ontology_mgr.create_entity(model_id, "NamedIndividual", f"模型实例: {model_id}")
    ontology_mgr.create_relationship(model_id, "rdf:type", "LargeLanguageModel")
    ontology_mgr.create_relationship(model_id, "usesTrainingMethod", "FineTuning")
    
    print(f"   ✓ 定义了模型实例: {model_id}")
    
    # 2. 使用智能体模块执行模型操作
    print("\n2. 🤖 使用智能体模块执行模型操作")
    
    # 创建模型操作代理
    model_agent = SkillAgent(
        name="ModelLifecycleAgent",
        description="负责模型完整生命周期管理的智能体",
        skills=[]  # 会在初始化后填充
    )
    await model_agent.initialize()
    
    # 获取所有可用的模型相关技能
    model_skills = []
    for skill_id in global_skill_registry.skills.keys():
        skill_meta = global_skill_registry.skills[skill_id].metadata
        if any(tag in ['training', 'evaluation', 'inference', 'ml', 'model'] for tag in skill_meta.tags):
            model_skills.append(skill_id)
    
    # 为代理分配技能
    model_agent.skills = model_skills[:3]  # 分配前3个模型相关技能
    
    # 执行训练任务
    if len(model_agent.skills) > 0:
        training_task_id = await model_agent.add_task(
            name="Train New Model",
            description="使用SFT方法训练大语言模型",
            skill_id=model_agent.skills[0],  # 假设第一个是训练技能
            parameters={
                "model_type": "large_language_model",
                "training_method": "sft",
                "dataset_path": "/datasets/training_data.jsonl",
                "hyperparameters": {
                    "learning_rate": 5e-5,
                    "batch_size": 16,
                    "epochs": 3
                }
            }
        )
        print(f"   ✓ 提交训练任务: {training_task_id}")
    
    # 3. 使用Vibecoding模块生成分析代码
    print("\n3. 💻 使用Vibecoding模块生成分析代码")
    
    vibecoding_interface = VibecodingNotebookInterface()
    
    # 创建分析笔记本
    notebook_id = vibecoding_interface.create_notebook(
        name="Model Lifecycle Analysis",
        description="分析模型生命周期各阶段的性能指标"
    )
    
    # 添加数据处理代码单元
    data_analysis_code = f"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 模拟模型生命周期数据
phases = ['Training', 'Validation', 'Testing', 'Deployment']
durations = [2.5, 0.3, 0.2, 0.1]  # in hours
accuracies = [0.85, 0.82, 0.84, 0.83]

# Create dataframe
df = pd.DataFrame({{
    'Phase': phases,
    'Duration_Hours': durations,
    'Accuracy': accuracies
}})

print("模型生命周期分析:")
print(df)

# Visualization
fig, ax1 = plt.subplots(figsize=(10, 6))

color = 'tab:red'
ax1.set_xlabel('Phase')
ax1.set_ylabel('Duration (hours)', color=color)
bars = ax1.bar(phases, durations, color=['skyblue', 'lightgreen', 'lightcoral', 'gold'], alpha=0.7)
ax1.tick_params(axis='y', labelcolor=color)

ax2 = ax1.twinx()
color = 'tab:blue'
ax2.set_ylabel('Accuracy', color=color)
line = ax2.plot(phases, accuracies, color=color, marker='o', linewidth=2, markersize=8)
ax2.tick_params(axis='y', labelcolor=color)

plt.title('Model Lifecycle Performance Dashboard')
plt.tight_layout()
plt.show()

print(f"\\n模型生命周期总耗时: {{sum(durations)}} 小时")
print(f"平均准确率: {{np.mean(accuracies):.2f}}")
"""
    
    vibecoding_interface.add_cell(notebook_id, "code", data_analysis_code)
    
    # 4. 执行笔记本
    print("\n4. ▶️ 执行分析笔记本")
    execution_result = await vibecoding_interface.execute_notebook(notebook_id)
    print(f"   ✓ 执行完成: {execution_result['successful_executions']}/{execution_result['executed_cells']} 成功")
    
    # 5. 保存本体定义
    print("\n5. 💾 保存本体定义")
    ontology_mgr.save_ontology("model_lifecycle_demo")
    print("   ✓ 本体定义已保存")
    
    print("\n" + "="*60)
    print("✅ 集成模型生命周期示例执行完成")
    print("="*60)
    
    return {
        "model_id": model_id,
        "training_task_id": training_task_id if 'training_task_id' in locals() else None,
        "notebook_execution": execution_result,
        "ontology_saved": True
    }

# 注意：这只是一个示例，在实际环境中需要确保所有模块正确安装和配置
```

## 总结

AI-Plat平台成功整合了三大核心技术模块：

1. **本体论驱动的数据模块** - 提供语义化知识表示和推理能力
2. **Skill Agent智能体模块** - 实现灵活的AI技能和任务编排
3. **Vibecoding大模型驱动开发模块** - 提升开发效率和智能化水平

这种设计使得AI-Plat不仅具备强大的AI能力，还具有高度的可扩展性和易用性。