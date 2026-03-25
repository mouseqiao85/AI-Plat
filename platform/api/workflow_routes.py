"""
工作流API路由
提供工作流定义、执行、管理API
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from auth.models import User
from auth.dependencies import get_current_active_user, require_developer
from workflow import workflow_engine, WorkflowStatus, TriggerType

router = APIRouter(prefix="/workflows", tags=["workflows"])


class CreateWorkflowRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    variables: Optional[Dict[str, Any]] = None


class UpdateWorkflowRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    variables: Optional[Dict[str, Any]] = None


class ExecuteWorkflowRequest(BaseModel):
    variables: Optional[Dict[str, Any]] = None
    trigger_type: Optional[str] = "manual"


class NodeConfig(BaseModel):
    id: str
    name: str
    type: str
    config: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, float]] = None
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    retry_count: Optional[int] = 0
    retry_interval: Optional[int] = 60
    timeout: Optional[int] = 300


class EdgeConfig(BaseModel):
    id: str
    source: str
    target: str
    condition: Optional[str] = None
    label: Optional[str] = None


@router.post("")
async def create_workflow(
    request: CreateWorkflowRequest,
    current_user: User = Depends(require_developer)
):
    """创建工作流"""
    definition = workflow_engine.create_workflow(
        name=request.name,
        description=request.description,
        nodes=request.nodes,
        edges=request.edges,
        variables=request.variables,
        created_by=str(current_user.id)
    )
    return {"success": True, "workflow": definition.to_dict()}


@router.get("")
async def list_workflows(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """列出所有工作流"""
    status_filter = WorkflowStatus(status) if status else None
    workflows = workflow_engine.list_workflows(status=status_filter)
    return {
        "success": True,
        "workflows": [w.to_dict() for w in workflows],
        "count": len(workflows)
    }


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取工作流详情"""
    definition = workflow_engine.get_workflow(workflow_id)
    if not definition:
        raise HTTPException(status_code=404, detail="工作流不存在")
    return {"success": True, "workflow": definition.to_dict()}


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    current_user: User = Depends(require_developer)
):
    """更新工作流"""
    definition = workflow_engine.get_workflow(workflow_id)
    if not definition:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    if request.name is not None:
        definition.name = request.name
    if request.description is not None:
        definition.description = request.description
    if request.variables is not None:
        definition.variables = request.variables
    definition.updated_at = datetime.utcnow()
    
    return {"success": True, "workflow": definition.to_dict()}


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: User = Depends(require_developer)
):
    """删除工作流"""
    success = workflow_engine.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="工作流不存在")
    return {"success": True, "message": "工作流已删除"}


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    request: ExecuteWorkflowRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """执行工作流"""
    definition = workflow_engine.get_workflow(workflow_id)
    if not definition:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    trigger_type = TriggerType(request.trigger_type or "manual")
    
    execution = await workflow_engine.execute(
        workflow_id=workflow_id,
        variables=request.variables,
        trigger_type=trigger_type,
        triggered_by=str(current_user.id)
    )
    
    return {"success": True, "execution": execution.to_dict()}


@router.get("/{workflow_id}/executions")
async def list_workflow_executions(
    workflow_id: str,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """列出工作流执行记录"""
    status_filter = WorkflowStatus(status) if status else None
    executions = workflow_engine.list_executions(
        workflow_id=workflow_id,
        status=status_filter
    )
    return {
        "success": True,
        "executions": [e.to_dict() for e in executions],
        "count": len(executions)
    }


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取执行详情"""
    execution = workflow_engine.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return {"success": True, "execution": execution.to_dict()}


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    current_user: User = Depends(require_developer)
):
    """取消执行"""
    success = await workflow_engine.cancel_execution(execution_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法取消执行")
    return {"success": True, "message": "执行已取消"}


@router.post("/executions/{execution_id}/pause")
async def pause_execution(
    execution_id: str,
    current_user: User = Depends(require_developer)
):
    """暂停执行"""
    success = await workflow_engine.pause_execution(execution_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法暂停执行")
    return {"success": True, "message": "执行已暂停"}


@router.post("/executions/{execution_id}/resume")
async def resume_execution(
    execution_id: str,
    current_user: User = Depends(require_developer)
):
    """恢复执行"""
    success = await workflow_engine.resume_execution(execution_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法恢复执行")
    return {"success": True, "message": "执行已恢复"}


@router.get("/executions")
async def list_all_executions(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """列出所有执行记录"""
    status_filter = WorkflowStatus(status) if status else None
    executions = workflow_engine.list_executions(status=status_filter)
    return {
        "success": True,
        "executions": [e.to_dict() for e in executions],
        "count": len(executions)
    }


@router.get("/statistics")
async def get_statistics(
    current_user: User = Depends(get_current_active_user)
):
    """获取工作流统计"""
    stats = workflow_engine.get_statistics()
    return {"success": True, "statistics": stats}


@router.post("/{workflow_id}/nodes")
async def add_node(
    workflow_id: str,
    node: NodeConfig,
    current_user: User = Depends(require_developer)
):
    """添加节点"""
    from workflow import WorkflowNode, NodeType
    
    definition = workflow_engine.get_workflow(workflow_id)
    if not definition:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    new_node = WorkflowNode(
        id=node.id,
        name=node.name,
        type=NodeType(node.type),
        config=node.config or {},
        position=node.position or {},
        inputs=node.inputs or {},
        outputs=node.outputs or {},
        retry_count=node.retry_count or 0,
        retry_interval=node.retry_interval or 60,
        timeout=node.timeout or 300
    )
    
    definition.nodes.append(new_node)
    definition.updated_at = datetime.utcnow()
    
    return {"success": True, "node": new_node.to_dict()}


@router.delete("/{workflow_id}/nodes/{node_id}")
async def remove_node(
    workflow_id: str,
    node_id: str,
    current_user: User = Depends(require_developer)
):
    """删除节点"""
    definition = workflow_engine.get_workflow(workflow_id)
    if not definition:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    definition.nodes = [n for n in definition.nodes if n.id != node_id]
    definition.edges = [e for e in definition.edges 
                       if e.source != node_id and e.target != node_id]
    definition.updated_at = datetime.utcnow()
    
    return {"success": True, "message": "节点已删除"}


@router.post("/{workflow_id}/edges")
async def add_edge(
    workflow_id: str,
    edge: EdgeConfig,
    current_user: User = Depends(require_developer)
):
    """添加边"""
    from workflow import WorkflowEdge
    
    definition = workflow_engine.get_workflow(workflow_id)
    if not definition:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    new_edge = WorkflowEdge(
        id=edge.id,
        source=edge.source,
        target=edge.target,
        condition=edge.condition,
        label=edge.label
    )
    
    definition.edges.append(new_edge)
    definition.updated_at = datetime.utcnow()
    
    return {"success": True, "edge": new_edge.to_dict()}


@router.delete("/{workflow_id}/edges/{edge_id}")
async def remove_edge(
    workflow_id: str,
    edge_id: str,
    current_user: User = Depends(require_developer)
):
    """删除边"""
    definition = workflow_engine.get_workflow(workflow_id)
    if not definition:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    definition.edges = [e for e in definition.edges if e.id != edge_id]
    definition.updated_at = datetime.utcnow()
    
    return {"success": True, "message": "边已删除"}


@router.post("/{workflow_id}/validate")
async def validate_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """验证工作流"""
    definition = workflow_engine.get_workflow(workflow_id)
    if not definition:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    errors = []
    
    if not definition.nodes:
        errors.append("工作流没有节点")
    
    node_ids = {n.id for n in definition.nodes}
    for edge in definition.edges:
        if edge.source not in node_ids:
            errors.append(f"边的源节点不存在: {edge.source}")
        if edge.target not in node_ids:
            errors.append(f"边的目标节点不存在: {edge.target}")
    
    has_start = any(n.type.value == "start" for n in definition.nodes)
    has_end = any(n.type.value == "end" for n in definition.nodes)
    
    return {
        "success": len(errors) == 0,
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": [] if has_start and has_end else ["建议添加开始和结束节点"]
    }
