"""
工作流引擎核心
支持复杂工作流定义、执行、监控
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
from abc import ABC, abstractmethod
import heapq
from collections import defaultdict

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """节点类型"""
    START = "start"
    END = "end"
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"
    SUBWORKFLOW = "subworkflow"
    DELAY = "delay"
    WEBHOOK = "webhook"


class NodeStatus(str, Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


class WorkflowStatus(str, Enum):
    """工作流状态"""
    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerType(str, Enum):
    """触发类型"""
    MANUAL = "manual"
    SCHEDULE = "schedule"
    EVENT = "event"
    WEBHOOK = "webhook"
    API = "api"


@dataclass
class NodeContext:
    """节点执行上下文"""
    workflow_id: str
    execution_id: str
    node_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowNode:
    """工作流节点"""
    id: str
    name: str
    type: NodeType
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, float] = field(default_factory=dict)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    retry_interval: int = 60
    timeout: int = 300
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "config": self.config,
            "position": self.position,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "retry_count": self.retry_count,
            "retry_interval": self.retry_interval,
            "timeout": self.timeout
        }


@dataclass
class WorkflowEdge:
    """工作流边"""
    id: str
    source: str
    target: str
    condition: Optional[str] = None
    label: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "condition": self.condition,
            "label": self.label
        }


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    nodes: List[WorkflowNode] = field(default_factory=list)
    edges: List[WorkflowEdge] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    triggers: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "variables": self.variables,
            "triggers": self.triggers,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by
        }


@dataclass
class NodeExecution:
    """节点执行记录"""
    id: str
    workflow_execution_id: str
    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_execution_id": self.workflow_execution_id,
            "node_id": self.node_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "error": self.error,
            "retry_count": self.retry_count
        }


@dataclass
class WorkflowExecution:
    """工作流执行记录"""
    id: str
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    trigger_type: TriggerType = TriggerType.MANUAL
    triggered_by: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    node_executions: Dict[str, NodeExecution] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "trigger_type": self.trigger_type.value,
            "triggered_by": self.triggered_by,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "variables": self.variables,
            "node_executions": {k: v.to_dict() for k, v in self.node_executions.items()},
            "result": self.result,
            "error": self.error
        }


class NodeHandler(ABC):
    """节点处理器基类"""
    
    @abstractmethod
    async def execute(self, context: NodeContext, config: Dict[str, Any]) -> Dict[str, Any]:
        """执行节点"""
        pass
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """验证配置"""
        pass


class TaskNodeHandler(NodeHandler):
    """任务节点处理器"""
    
    def __init__(self, agent_registry=None, skill_registry=None):
        self.agent_registry = agent_registry
        self.skill_registry = skill_registry
    
    async def execute(self, context: NodeContext, config: Dict[str, Any]) -> Dict[str, Any]:
        agent_id = config.get("agent_id")
        skill_id = config.get("skill_id")
        parameters = config.get("parameters", {})
        
        parameters.update(context.variables)
        parameters.update(context.inputs)
        
        if self.agent_registry and agent_id:
            agent = self.agent_registry.get(agent_id)
            if agent:
                result = await agent.execute_skill(skill_id, parameters)
                return {"result": result, "success": True}
        
        await asyncio.sleep(0.1)
        return {"result": {"status": "completed"}, "success": True}
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "agent_id" not in config:
            return False, "agent_id is required"
        if "skill_id" not in config:
            return False, "skill_id is required"
        return True, None


class ConditionNodeHandler(NodeHandler):
    """条件节点处理器"""
    
    async def execute(self, context: NodeContext, config: Dict[str, Any]) -> Dict[str, Any]:
        conditions = config.get("conditions", [])
        default_branch = config.get("default", "else")
        
        for condition in conditions:
            if await self._evaluate_condition(condition, context):
                return {"branch": condition.get("branch", "true"), "success": True}
        
        return {"branch": default_branch, "success": True}
    
    async def _evaluate_condition(self, condition: Dict[str, Any], context: NodeContext) -> bool:
        expression = condition.get("expression", "")
        
        try:
            variables = {**context.variables, **context.inputs}
            result = eval(expression, {"__builtins__": {}}, variables)
            return bool(result)
        except Exception as e:
            logger.error(f"Condition evaluation error: {e}")
            return False
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None


class ParallelNodeHandler(NodeHandler):
    """并行节点处理器"""
    
    async def execute(self, context: NodeContext, config: Dict[str, Any]) -> Dict[str, Any]:
        branches = config.get("branches", [])
        results = []
        
        tasks = []
        for branch in branches:
            task = self._execute_branch(branch, context)
            tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {"results": results, "success": True}
    
    async def _execute_branch(self, branch: Dict[str, Any], context: NodeContext) -> Dict[str, Any]:
        await asyncio.sleep(0.1)
        return {"branch": branch.get("id"), "status": "completed"}
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None


class DelayNodeHandler(NodeHandler):
    """延迟节点处理器"""
    
    async def execute(self, context: NodeContext, config: Dict[str, Any]) -> Dict[str, Any]:
        delay_seconds = config.get("seconds", 1)
        await asyncio.sleep(delay_seconds)
        return {"waited": delay_seconds, "success": True}
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self):
        self.definitions: Dict[str, WorkflowDefinition] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.handlers: Dict[NodeType, NodeHandler] = {}
        self.running_executions: Set[str] = set()
        
        self._register_default_handlers()
        
        logger.info("Workflow Engine initialized")
    
    def _register_default_handlers(self):
        self.handlers[NodeType.TASK] = TaskNodeHandler()
        self.handlers[NodeType.CONDITION] = ConditionNodeHandler()
        self.handlers[NodeType.PARALLEL] = ParallelNodeHandler()
        self.handlers[NodeType.DELAY] = DelayNodeHandler()
    
    def register_handler(self, node_type: NodeType, handler: NodeHandler):
        self.handlers[node_type] = handler
    
    def create_workflow(
        self,
        name: str,
        description: str = "",
        nodes: List[Dict[str, Any]] = None,
        edges: List[Dict[str, Any]] = None,
        variables: Dict[str, Any] = None,
        created_by: str = None
    ) -> WorkflowDefinition:
        workflow_id = str(uuid.uuid4())
        
        workflow_nodes = []
        for node_data in (nodes or []):
            node = WorkflowNode(
                id=node_data.get("id", str(uuid.uuid4())),
                name=node_data.get("name", ""),
                type=NodeType(node_data.get("type", "task")),
                config=node_data.get("config", {}),
                position=node_data.get("position", {}),
                inputs=node_data.get("inputs", {}),
                outputs=node_data.get("outputs", {}),
                retry_count=node_data.get("retry_count", 0),
                retry_interval=node_data.get("retry_interval", 60),
                timeout=node_data.get("timeout", 300)
            )
            workflow_nodes.append(node)
        
        workflow_edges = []
        for edge_data in (edges or []):
            edge = WorkflowEdge(
                id=edge_data.get("id", str(uuid.uuid4())),
                source=edge_data["source"],
                target=edge_data["target"],
                condition=edge_data.get("condition"),
                label=edge_data.get("label")
            )
            workflow_edges.append(edge)
        
        definition = WorkflowDefinition(
            id=workflow_id,
            name=name,
            description=description,
            nodes=workflow_nodes,
            edges=workflow_edges,
            variables=variables or {},
            created_by=created_by
        )
        
        self.definitions[workflow_id] = definition
        logger.info(f"Created workflow: {name} ({workflow_id})")
        
        return definition
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        return self.definitions.get(workflow_id)
    
    def list_workflows(self, status: WorkflowStatus = None) -> List[WorkflowDefinition]:
        return list(self.definitions.values())
    
    def delete_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self.definitions:
            del self.definitions[workflow_id]
            return True
        return False
    
    async def execute(
        self,
        workflow_id: str,
        variables: Dict[str, Any] = None,
        trigger_type: TriggerType = TriggerType.MANUAL,
        triggered_by: str = None
    ) -> WorkflowExecution:
        definition = self.get_workflow(workflow_id)
        if not definition:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        execution_id = str(uuid.uuid4())
        execution = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow_id,
            workflow_name=definition.name,
            trigger_type=trigger_type,
            triggered_by=triggered_by,
            variables={**definition.variables, **(variables or {})}
        )
        
        for node in definition.nodes:
            node_execution = NodeExecution(
                id=str(uuid.uuid4()),
                workflow_execution_id=execution_id,
                node_id=node.id
            )
            execution.node_executions[node.id] = node_execution
        
        self.executions[execution_id] = execution
        self.running_executions.add(execution_id)
        
        execution.status = WorkflowStatus.RUNNING
        execution.started_at = datetime.utcnow()
        
        try:
            await self._execute_workflow(execution, definition)
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()
            logger.error(f"Workflow execution failed: {e}")
        finally:
            self.running_executions.discard(execution_id)
        
        return execution
    
    async def _execute_workflow(self, execution: WorkflowExecution, definition: WorkflowDefinition):
        graph = self._build_graph(definition)
        
        start_nodes = self._find_start_nodes(definition)
        
        ready_queue = []
        for node_id in start_nodes:
            heapq.heappush(ready_queue, (0, node_id))
        
        completed_nodes: Set[str] = set()
        in_progress: Set[str] = set()
        
        while ready_queue or in_progress:
            if ready_queue:
                _, node_id = heapq.heappop(ready_queue)
                
                if node_id in completed_nodes or node_id in in_progress:
                    continue
                
                node = next((n for n in definition.nodes if n.id == node_id), None)
                if not node:
                    continue
                
                in_progress.add(node_id)
                
                node_execution = execution.node_executions.get(node_id)
                if node_execution:
                    node_execution.status = NodeStatus.RUNNING
                    node_execution.started_at = datetime.utcnow()
                    node_execution.inputs = execution.variables.copy()
                
                try:
                    result = await self._execute_node(node, execution)
                    
                    if node_execution:
                        node_execution.status = NodeStatus.SUCCESS
                        node_execution.outputs = result
                        node_execution.completed_at = datetime.utcnow()
                    
                    execution.variables.update(result)
                    
                    completed_nodes.add(node_id)
                    in_progress.discard(node_id)
                    
                    next_nodes = self._get_next_nodes(node_id, definition, result)
                    for next_node_id in next_nodes:
                        if next_node_id not in completed_nodes:
                            heapq.heappush(ready_queue, (len(completed_nodes), next_node_id))
                
                except Exception as e:
                    if node_execution:
                        node_execution.status = NodeStatus.FAILED
                        node_execution.error = str(e)
                        node_execution.completed_at = datetime.utcnow()
                    
                    in_progress.discard(node_id)
                    raise
            
            if in_progress and not ready_queue:
                await asyncio.sleep(0.1)
    
    async def _execute_node(self, node: WorkflowNode, execution: WorkflowExecution) -> Dict[str, Any]:
        handler = self.handlers.get(node.type)
        if not handler:
            return {"error": f"No handler for node type: {node.type}"}
        
        context = NodeContext(
            workflow_id=execution.workflow_id,
            execution_id=execution.id,
            node_id=node.id,
            variables=execution.variables,
            inputs=node.inputs
        )
        
        result = await handler.execute(context, node.config)
        return result
    
    def _build_graph(self, definition: WorkflowDefinition) -> Dict[str, List[str]]:
        graph = defaultdict(list)
        for edge in definition.edges:
            graph[edge.source].append(edge.target)
        return dict(graph)
    
    def _find_start_nodes(self, definition: WorkflowDefinition) -> List[str]:
        target_nodes = {e.target for e in definition.edges}
        start_nodes = []
        
        for node in definition.nodes:
            if node.type == NodeType.START:
                start_nodes.append(node.id)
            elif node.id not in target_nodes:
                start_nodes.append(node.id)
        
        return start_nodes if start_nodes else [n.id for n in definition.nodes[:1]]
    
    def _get_next_nodes(
        self,
        node_id: str,
        definition: WorkflowDefinition,
        result: Dict[str, Any]
    ) -> List[str]:
        next_nodes = []
        
        for edge in definition.edges:
            if edge.source == node_id:
                if edge.condition:
                    branch = result.get("branch")
                    if branch and edge.label == branch:
                        next_nodes.append(edge.target)
                else:
                    next_nodes.append(edge.target)
        
        return next_nodes
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        return self.executions.get(execution_id)
    
    def list_executions(
        self,
        workflow_id: str = None,
        status: WorkflowStatus = None
    ) -> List[WorkflowExecution]:
        executions = list(self.executions.values())
        
        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        
        if status:
            executions = [e for e in executions if e.status == status]
        
        return sorted(executions, key=lambda e: e.started_at or datetime.min, reverse=True)
    
    async def cancel_execution(self, execution_id: str) -> bool:
        if execution_id in self.running_executions:
            execution = self.executions.get(execution_id)
            if execution:
                execution.status = WorkflowStatus.CANCELLED
                execution.completed_at = datetime.utcnow()
                self.running_executions.discard(execution_id)
                return True
        return False
    
    async def pause_execution(self, execution_id: str) -> bool:
        execution = self.executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.RUNNING:
            execution.status = WorkflowStatus.PAUSED
            return True
        return False
    
    async def resume_execution(self, execution_id: str) -> bool:
        execution = self.executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.PAUSED:
            execution.status = WorkflowStatus.RUNNING
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        total = len(self.executions)
        by_status = defaultdict(int)
        
        for execution in self.executions.values():
            by_status[execution.status.value] += 1
        
        return {
            "total_workflows": len(self.definitions),
            "total_executions": total,
            "running_executions": len(self.running_executions),
            "by_status": dict(by_status)
        }


workflow_engine = WorkflowEngine()
