"""
智能体编排器
负责协调多个智能体协作完成复杂任务
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
import logging
import json
from enum import Enum

from .skill_agent import SkillAgent, Task, TaskPriority
from .skill_registry import global_skill_registry, SkillCategory

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """工作流状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskDependencyType(Enum):
    """任务依赖类型枚举"""
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"      # 并行执行
    CONDITIONAL = "conditional"  # 条件执行


@dataclass
class WorkflowTask:
    """工作流任务数据类"""
    id: str
    name: str
    agent_id: str
    skill_id: str
    parameters: Dict[str, Any]
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务ID
    dependency_type: TaskDependencyType = TaskDependencyType.SEQUENTIAL
    condition: Optional[Callable] = None  # 条件函数
    timeout: int = 300  # 超时时间（秒）


@dataclass
class Workflow:
    """工作流数据类"""
    id: str
    name: str
    description: str
    tasks: List[WorkflowTask]
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AgentOrchestrator:
    """智能体编排器"""
    
    def __init__(self):
        """初始化编排器"""
        self.agents: Dict[str, SkillAgent] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.workflow_tasks: Dict[str, Dict[str, str]] = {}  # workflow_id -> {task_id -> external_task_id}
        self.active_workflows = set()
        
        logger.info("Agent Orchestrator initialized")
    
    def register_agent(self, agent: SkillAgent):
        """
        注册智能体
        
        Args:
            agent: 技能代理实例
        """
        self.agents[agent.id] = agent
        logger.info(f"Registered agent: {agent.name} (ID: {agent.id})")
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        注销智能体
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            注销是否成功
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
            return True
        return False
    
    def create_workflow(self, 
                      name: str, 
                      description: str, 
                      tasks: List[WorkflowTask]) -> str:
        """
        创建工作流
        
        Args:
            name: 工作流名称
            description: 工作流描述
            tasks: 任务列表
            
        Returns:
            工作流ID
        """
        workflow_id = str(uuid.uuid4())
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            tasks=tasks
        )
        
        self.workflows[workflow_id] = workflow
        self.workflow_tasks[workflow_id] = {}
        
        logger.info(f"Created workflow: {name} (ID: {workflow_id}) with {len(tasks)} tasks")
        return workflow_id
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        执行工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            执行结果
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        
        if workflow.status != WorkflowStatus.PENDING:
            raise ValueError(f"Workflow {workflow_id} is not in pending state")
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()
        self.active_workflows.add(workflow_id)
        
        logger.info(f"Starting workflow execution: {workflow.name} (ID: {workflow_id})")
        
        try:
            # 构建任务依赖图
            dependency_graph = self._build_dependency_graph(workflow.tasks)
            
            # 按依赖顺序执行任务
            results = await self._execute_tasks_by_dependencies(workflow, dependency_graph)
            
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            workflow.result = results
            
            logger.info(f"Workflow {workflow_id} completed successfully")
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now()
            workflow.error = str(e)
            
            logger.error(f"Workflow {workflow_id} failed: {str(e)}")
            raise e
        finally:
            self.active_workflows.discard(workflow_id)
        
        return {
            'workflow_id': workflow_id,
            'status': workflow.status.value,
            'results': workflow.result,
            'error': workflow.error
        }
    
    def _build_dependency_graph(self, tasks: List[WorkflowTask]) -> Dict[str, List[str]]:
        """
        构建任务依赖图
        
        Args:
            tasks: 任务列表
            
        Returns:
            依赖图（任务ID -> 依赖任务ID列表）
        """
        graph = {}
        task_ids = [task.id for task in tasks]
        
        for task in tasks:
            # 验证依赖任务是否存在
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    raise ValueError(f"Dependency task not found: {dep_id}")
            
            graph[task.id] = task.dependencies
        
        return graph
    
    async def _execute_tasks_by_dependencies(self, 
                                           workflow: Workflow, 
                                           dependency_graph: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        根据依赖关系执行任务
        
        Args:
            workflow: 工作流
            dependency_graph: 依赖图
            
        Returns:
            执行结果
        """
        results = {}
        remaining_tasks = {task.id: task for task in workflow.tasks}
        completed_tasks = set()
        
        while remaining_tasks:
            ready_tasks = []
            
            # 查找没有未完成依赖的任务
            for task_id, task in remaining_tasks.items():
                dependencies_met = all(
                    dep_id in completed_tasks for dep_id in task.dependencies
                )
                
                if dependencies_met:
                    # 检查条件（如果是条件任务）
                    if task.dependency_type == TaskDependencyType.CONDITIONAL:
                        if task.condition and not task.condition(results):
                            # 条件不满足，跳过此任务
                            completed_tasks.add(task_id)
                            del remaining_tasks[task_id]
                            continue
                    
                    ready_tasks.append(task)
            
            if not ready_tasks:
                raise RuntimeError("Circular dependency detected or conditions not met")
            
            # 并行执行就绪任务
            task_coroutines = []
            for task in ready_tasks:
                coro = self._execute_single_workflow_task(workflow.id, task, results)
                task_coroutines.append(coro)
            
            # 等待所有就绪任务完成
            task_results = await asyncio.gather(*task_coroutines, return_exceptions=True)
            
            # 处理结果
            for i, task in enumerate(ready_tasks):
                task_id = task.id
                result = task_results[i]
                
                if isinstance(result, Exception):
                    raise result
                
                results[task_id] = result
                completed_tasks.add(task_id)
                del remaining_tasks[task_id]
        
        return results
    
    async def _execute_single_workflow_task(self, 
                                         workflow_id: str, 
                                         task: WorkflowTask, 
                                         context: Dict[str, Any]) -> Any:
        """
        执行单个工作流任务
        
        Args:
            workflow_id: 工作流ID
            task: 工作流任务
            context: 上下文数据
            
        Returns:
            任务执行结果
        """
        # 解析参数中的上下文引用
        resolved_parameters = self._resolve_context_references(task.parameters, context)
        
        # 获取目标代理
        if task.agent_id not in self.agents:
            raise ValueError(f"Agent not found: {task.agent_id}")
        
        agent = self.agents[task.agent_id]
        
        # 添加任务到代理
        external_task_id = await agent.add_task(
            name=f"{task.name}_{workflow_id}",
            description=f"Workflow task: {task.description}",
            skill_id=task.skill_id,
            parameters=resolved_parameters,
            priority=task.priority
        )
        
        # 记录任务映射
        self.workflow_tasks[workflow_id][task.id] = external_task_id
        
        # 等待任务完成
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < task.timeout:
            result = agent.get_task_result(external_task_id)
            if result and result['status'] in ['completed', 'failed']:
                if result['status'] == 'failed':
                    raise RuntimeError(f"Task failed: {result.get('error', 'Unknown error')}")
                return result['result']
            
            await asyncio.sleep(0.5)
        
        raise TimeoutError(f"Task {task.id} timed out after {task.timeout} seconds")
    
    def _resolve_context_references(self, 
                                  parameters: Dict[str, Any], 
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析参数中的上下文引用
        
        Args:
            parameters: 原始参数
            context: 上下文数据
            
        Returns:
            解析后的参数
        """
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # 解析上下文引用，格式: ${task_id.result_key}
                ref = value[2:-1]  # 移除 ${ 和 }
                
                if '.' in ref:
                    task_id, result_key = ref.split('.', 1)
                    if task_id in context:
                        task_result = context[task_id]
                        if isinstance(task_result, dict) and result_key in task_result:
                            resolved[key] = task_result[result_key]
                        else:
                            resolved[key] = value  # 保留原始值
                    else:
                        resolved[key] = value  # 保留原始值
                else:
                    # 直接引用整个任务结果
                    resolved[key] = context.get(ref, value)
            elif isinstance(value, dict):
                # 递归解析嵌套字典
                resolved[key] = self._resolve_context_references(value, context)
            elif isinstance(value, list):
                # 解析列表中的上下文引用
                resolved_list = []
                for item in value:
                    if isinstance(item, str) and item.startswith("${") and item.endswith("}"):
                        ref = item[2:-1]
                        resolved_list.append(context.get(ref, item))
                    else:
                        resolved_list.append(item)
                resolved[key] = resolved_list
            else:
                resolved[key] = value
        
        return resolved
    
    def get_workflow_result(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流结果
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            工作流结果
        """
        if workflow_id not in self.workflows:
            return None
        
        workflow = self.workflows[workflow_id]
        return {
            'id': workflow.id,
            'name': workflow.name,
            'status': workflow.status.value,
            'result': workflow.result,
            'error': workflow.error,
            'created_at': workflow.created_at.isoformat() if workflow.created_at else None,
            'started_at': workflow.started_at.isoformat() if workflow.started_at else None,
            'completed_at': workflow.completed_at.isoformat() if workflow.completed_at else None
        }
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """
        取消工作流执行
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            取消是否成功
        """
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        
        if workflow.status != WorkflowStatus.RUNNING:
            return False
        
        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.now()
        
        # 从活跃工作流中移除
        self.active_workflows.discard(workflow_id)
        
        logger.info(f"Cancelled workflow: {workflow_id}")
        return True
    
    def get_active_workflows(self) -> List[str]:
        """
        获取活跃工作流列表
        
        Returns:
            活跃工作流ID列表
        """
        return list(self.active_workflows)
    
    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """
        获取编排器统计信息
        
        Returns:
            统计信息
        """
        completed_workflows = sum(
            1 for wf in self.workflows.values() 
            if wf.status == WorkflowStatus.COMPLETED
        )
        failed_workflows = sum(
            1 for wf in self.workflows.values() 
            if wf.status == WorkflowStatus.FAILED
        )
        
        return {
            'total_agents': len(self.agents),
            'total_workflows': len(self.workflows),
            'active_workflows': len(self.active_workflows),
            'completed_workflows': completed_workflows,
            'failed_workflows': failed_workflows,
            'registered_agents': list(self.agents.keys()),
            'workflow_status_distribution': {
                status.value: sum(1 for wf in self.workflows.values() if wf.status == status)
                for status in WorkflowStatus
            }
        }
    
    async def shutdown(self):
        """关闭编排器"""
        logger.info("Shutting down Agent Orchestrator...")
        
        # 取消所有活跃工作流
        for workflow_id in list(self.active_workflows):
            self.cancel_workflow(workflow_id)
        
        # 关闭所有代理
        for agent in list(self.agents.values()):
            await agent.shutdown()
        
        logger.info("Agent Orchestrator shut down successfully")


# 示例使用
async def example_usage():
    """示例用法"""
    print("=== 智能体编排器示例 ===")
    
    # 创建编排器
    orchestrator = AgentOrchestrator()
    
    # 创建一些代理
    agent1 = SkillAgent(
        name="DataProcessor",
        description="数据处理代理",
        skills=[]  # 我们后面会设置
    )
    await agent1.initialize()
    
    agent2 = SkillAgent(
        name="TextAnalyzer", 
        description="文本分析代理",
        skills=[]
    )
    await agent2.initialize()
    
    # 注册代理到编排器
    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)
    
    # 获取可用技能
    all_skills = global_skill_registry.list_skills()
    skill_ids = [skill.metadata.id for skill in all_skills]
    
    # 为代理分配技能
    if len(skill_ids) >= 2:
        agent1.skills = [skill_ids[0]]  # 数据处理技能
        agent2.skills = [skill_ids[1]]  # 文本分析技能
    
    # 创建工作流任务
    task1 = WorkflowTask(
        id="task1",
        name="Clean Data",
        agent_id=agent1.id,
        skill_id=skill_ids[0] if skill_ids else "",
        parameters={
            "data": [
                {"name": "张三", "age": 30, "city": "北京", "score": None},
                {"name": "李四", "age": 25, "city": "上海", "score": 85}
            ],
            "operation": "clean"
        }
    )
    
    task2 = WorkflowTask(
        id="task2",
        name="Analyze Text",
        agent_id=agent2.id,
        skill_id=skill_ids[1] if len(skill_ids) > 1 else "",
        parameters={
            "text": "今天天气很好，心情愉快",
            "analyze_type": "sentiment"
        },
        dependencies=["task1"]  # 依赖task1的结果
    )
    
    # 创建工作流
    workflow_id = orchestrator.create_workflow(
        name="Data Processing and Analysis Workflow",
        description="一个包含数据处理和文本分析的工作流",
        tasks=[task1, task2]
    )
    
    print(f"Created workflow: {workflow_id}")
    
    # 执行工作流
    try:
        result = await orchestrator.execute_workflow(workflow_id)
        print(f"Workflow result: {result}")
    except Exception as e:
        print(f"Workflow execution failed: {str(e)}")
    
    # 获取工作流结果
    workflow_result = orchestrator.get_workflow_result(workflow_id)
    print(f"Final workflow result: {workflow_result}")
    
    # 获取统计信息
    stats = orchestrator.get_orchestrator_stats()
    print(f"Orchestrator stats: {stats}")
    
    # 关闭编排器
    await orchestrator.shutdown()


if __name__ == "__main__":
    asyncio.run(example_usage())