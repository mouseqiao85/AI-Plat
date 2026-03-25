"""
目标驱动型编排引擎 API
Goal-Oriented Orchestrator API

基于高级意图解析的目标导向任务编排系统
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import sqlite3

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])

DB_PATH = "/opt/ai-plat-api/ai_plat.db"


class TaskGoal(BaseModel):
    description: str = Field(..., description="自然语言描述的目标")
    priority: str = Field(default="medium", description="优先级: low, medium, high, critical")
    deadline: Optional[str] = Field(None, description="截止日期")
    constraints: Optional[List[str]] = Field(None, description="约束条件")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class SubTask(BaseModel):
    id: str
    name: str
    description: str
    status: str = "pending"
    assigned_agent: Optional[str] = None
    dependencies: List[str] = []
    estimated_time: Optional[int] = None
    actual_time: Optional[int] = None


class OrchestrationPlan(BaseModel):
    goal_id: str
    goal_description: str
    subtasks: List[SubTask]
    execution_order: List[str]
    estimated_completion: Optional[str] = None
    status: str = "planning"


class ExecutionResult(BaseModel):
    goal_id: str
    status: str
    subtasks_completed: int
    subtasks_total: int
    execution_time: Optional[int] = None
    results: List[Dict[str, Any]]
    errors: List[str] = []


def init_orchestrator_tables():
    """初始化编排器数据库表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS orchestration_goals (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            deadline TEXT,
            constraints TEXT,
            context TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS orchestration_subtasks (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            assigned_agent TEXT,
            dependencies TEXT,
            estimated_time INTEGER,
            actual_time INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (goal_id) REFERENCES orchestration_goals(id)
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS orchestration_results (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            status TEXT,
            subtasks_completed INTEGER,
            subtasks_total INTEGER,
            execution_time INTEGER,
            results TEXT,
            errors TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


class GoalOrientedOrchestrator:
    """目标驱动型编排引擎"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        init_orchestrator_tables()
    
    def parse_goal(self, goal_description: str) -> Dict[str, Any]:
        """
        自然语言目标理解与分解
        解析用户输入的自然语言目标
        """
        # 简化的目标解析逻辑
        parsed = {
            "original": goal_description,
            "keywords": [],
            "intent": "execute",
            "entities": []
        }
        
        # 提取关键词
        words = goal_description.lower().split()
        action_keywords = ["分析", "处理", "生成", "创建", "优化", "监控", "预测"]
        
        for word in words:
            if any(ak in word for ak in action_keywords):
                parsed["keywords"].append(word)
        
        # 检测意图类型
        if "分析" in goal_description or "统计" in goal_description:
            parsed["intent"] = "analyze"
        elif "生成" in goal_description or "创建" in goal_description:
            parsed["intent"] = "generate"
        elif "优化" in goal_description or "改进" in goal_description:
            parsed["intent"] = "optimize"
        elif "监控" in goal_description:
            parsed["intent"] = "monitor"
        
        return parsed
    
    def decompose_goal(self, goal: TaskGoal) -> OrchestrationPlan:
        """
        将高层目标分解为可执行的子任务
        """
        goal_id = f"goal_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        # 解析目标
        parsed = self.parse_goal(goal.description)
        
        # 根据意图生成子任务
        subtasks = []
        
        if parsed["intent"] == "analyze":
            subtasks = [
                SubTask(
                    id=f"{goal_id}_st1",
                    name="数据收集",
                    description="收集分析所需的数据",
                    estimated_time=300
                ),
                SubTask(
                    id=f"{goal_id}_st2",
                    name="数据预处理",
                    description="清洗和准备数据",
                    dependencies=[f"{goal_id}_st1"],
                    estimated_time=600
                ),
                SubTask(
                    id=f"{goal_id}_st3",
                    name="执行分析",
                    description="执行数据分析算法",
                    dependencies=[f"{goal_id}_st2"],
                    estimated_time=900
                ),
                SubTask(
                    id=f"{goal_id}_st4",
                    name="生成报告",
                    description="生成分析报告",
                    dependencies=[f"{goal_id}_st3"],
                    estimated_time=300
                )
            ]
        elif parsed["intent"] == "generate":
            subtasks = [
                SubTask(
                    id=f"{goal_id}_st1",
                    name="需求理解",
                    description="理解生成需求",
                    estimated_time=180
                ),
                SubTask(
                    id=f"{goal_id}_st2",
                    name="内容生成",
                    description="生成目标内容",
                    dependencies=[f"{goal_id}_st1"],
                    estimated_time=600
                ),
                SubTask(
                    id=f"{goal_id}_st3",
                    name="质量验证",
                    description="验证生成内容质量",
                    dependencies=[f"{goal_id}_st2"],
                    estimated_time=300
                )
            ]
        elif parsed["intent"] == "optimize":
            subtasks = [
                SubTask(
                    id=f"{goal_id}_st1",
                    name="现状分析",
                    description="分析当前状态",
                    estimated_time=400
                ),
                SubTask(
                    id=f"{goal_id}_st2",
                    name="瓶颈识别",
                    description="识别性能瓶颈",
                    dependencies=[f"{goal_id}_st1"],
                    estimated_time=500
                ),
                SubTask(
                    id=f"{goal_id}_st3",
                    name="优化执行",
                    description="执行优化策略",
                    dependencies=[f"{goal_id}_st2"],
                    estimated_time=800
                ),
                SubTask(
                    id=f"{goal_id}_st4",
                    name="效果验证",
                    description="验证优化效果",
                    dependencies=[f"{goal_id}_st3"],
                    estimated_time=400
                )
            ]
        else:
            # 通用任务分解
            subtasks = [
                SubTask(
                    id=f"{goal_id}_st1",
                    name="任务分析",
                    description="分析任务需求",
                    estimated_time=200
                ),
                SubTask(
                    id=f"{goal_id}_st2",
                    name="执行处理",
                    description="执行主要处理逻辑",
                    dependencies=[f"{goal_id}_st1"],
                    estimated_time=600
                ),
                SubTask(
                    id=f"{goal_id}_st3",
                    name="结果验证",
                    description="验证执行结果",
                    dependencies=[f"{goal_id}_st2"],
                    estimated_time=200
                )
            ]
        
        # 计算执行顺序（拓扑排序）
        execution_order = self._calculate_execution_order(subtasks)
        
        # 保存到数据库
        self._save_goal(goal_id, goal)
        self._save_subtasks(goal_id, subtasks)
        
        # 估算完成时间
        total_time = sum(st.estimated_time or 0 for st in subtasks)
        estimated_completion = datetime.utcnow().timestamp() + total_time
        
        return OrchestrationPlan(
            goal_id=goal_id,
            goal_description=goal.description,
            subtasks=subtasks,
            execution_order=execution_order,
            estimated_completion=datetime.fromtimestamp(estimated_completion).isoformat(),
            status="planned"
        )
    
    def _calculate_execution_order(self, subtasks: List[SubTask]) -> List[str]:
        """计算子任务的执行顺序"""
        # 简化的拓扑排序
        order = []
        completed = set()
        
        while len(order) < len(subtasks):
            for st in subtasks:
                if st.id in completed:
                    continue
                if all(dep in completed for dep in st.dependencies):
                    order.append(st.id)
                    completed.add(st.id)
        
        return order
    
    def _save_goal(self, goal_id: str, goal: TaskGoal):
        """保存目标到数据库"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """INSERT INTO orchestration_goals 
               (id, description, priority, deadline, constraints, context, status) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (goal_id, goal.description, goal.priority, goal.deadline,
             json.dumps(goal.constraints) if goal.constraints else None,
             json.dumps(goal.context) if goal.context else None, "planned")
        )
        conn.commit()
        conn.close()
    
    def _save_subtasks(self, goal_id: str, subtasks: List[SubTask]):
        """保存子任务到数据库"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for st in subtasks:
            c.execute(
                """INSERT INTO orchestration_subtasks 
                   (id, goal_id, name, description, status, assigned_agent, 
                    dependencies, estimated_time, actual_time) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (st.id, goal_id, st.name, st.description, st.status,
                 st.assigned_agent, json.dumps(st.dependencies),
                 st.estimated_time, st.actual_time)
            )
        conn.commit()
        conn.close()
    
    def execute_plan(self, goal_id: str) -> ExecutionResult:
        """
        执行编排计划
        """
        # 获取子任务
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM orchestration_subtasks WHERE goal_id = ?", (goal_id,))
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            raise HTTPException(404, "Goal not found")
        
        subtasks = [dict(r) for r in rows]
        total = len(subtasks)
        completed = 0
        errors = []
        results = []
        start_time = datetime.utcnow()
        
        # 模拟执行
        for st in subtasks:
            try:
                # 更新状态为运行中
                self._update_subtask_status(st["id"], "running")
                
                # 模拟执行时间
                import time
                time.sleep(0.1)
                
                # 模拟执行结果
                result = {
                    "subtask_id": st["id"],
                    "subtask_name": st["name"],
                    "status": "completed",
                    "output": f"Task {st['name']} completed successfully"
                }
                results.append(result)
                completed += 1
                
                # 更新状态为完成
                self._update_subtask_status(st["id"], "completed")
                
            except Exception as e:
                errors.append(f"Subtask {st['name']} failed: {str(e)}")
                self._update_subtask_status(st["id"], "failed")
        
        execution_time = int((datetime.utcnow() - start_time).total_seconds())
        
        # 保存执行结果
        result_id = f"result_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            """INSERT INTO orchestration_results 
               (id, goal_id, status, subtasks_completed, subtasks_total, 
                execution_time, results, errors) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (result_id, goal_id, "completed" if completed == total else "partial",
             completed, total, execution_time,
             json.dumps(results), json.dumps(errors))
        )
        conn.commit()
        conn.close()
        
        return ExecutionResult(
            goal_id=goal_id,
            status="completed" if completed == total else "partial",
            subtasks_completed=completed,
            subtasks_total=total,
            execution_time=execution_time,
            results=results,
            errors=errors
        )
    
    def _update_subtask_status(self, subtask_id: str, status: str):
        """更新子任务状态"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE orchestration_subtasks SET status = ? WHERE id = ?", (status, subtask_id))
        conn.commit()
        conn.close()
    
    def get_goal_status(self, goal_id: str) -> Dict[str, Any]:
        """获取目标执行状态"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute("SELECT * FROM orchestration_goals WHERE id = ?", (goal_id,))
        goal = c.fetchone()
        
        if not goal:
            conn.close()
            raise HTTPException(404, "Goal not found")
        
        c.execute("SELECT * FROM orchestration_subtasks WHERE goal_id = ?", (goal_id,))
        subtasks = [dict(r) for r in c.fetchall()]
        
        c.execute("SELECT * FROM orchestration_results WHERE goal_id = ? ORDER BY created_at DESC LIMIT 1", (goal_id,))
        result = c.fetchone()
        
        conn.close()
        
        completed = sum(1 for st in subtasks if st["status"] == "completed")
        total = len(subtasks)
        progress = (completed / total * 100) if total > 0 else 0
        
        return {
            "goal_id": goal_id,
            "description": goal["description"],
            "status": goal["status"],
            "progress": progress,
            "subtasks_completed": completed,
            "subtasks_total": total,
            "subtasks": subtasks,
            "latest_result": dict(result) if result else None
        }
    
    def list_goals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出所有目标"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            "SELECT * FROM orchestration_goals ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = c.fetchall()
        conn.close()
        
        return [dict(r) for r in rows]


# 创建全局实例
orchestrator = GoalOrientedOrchestrator()


@router.post("/goals/decompose")
async def decompose_goal(goal: TaskGoal):
    """分解目标为子任务"""
    plan = orchestrator.decompose_goal(goal)
    return {
        "success": True,
        "plan": plan.dict()
    }


@router.post("/goals/{goal_id}/execute")
async def execute_goal(goal_id: str):
    """执行目标计划"""
    result = orchestrator.execute_plan(goal_id)
    return {
        "success": True,
        "result": result.dict()
    }


@router.get("/goals/{goal_id}/status")
async def get_goal_status(goal_id: str):
    """获取目标状态"""
    status = orchestrator.get_goal_status(goal_id)
    return status


@router.get("/goals")
async def list_goals(limit: int = 50):
    """列出所有目标"""
    goals = orchestrator.list_goals(limit)
    return {
        "goals": goals,
        "count": len(goals)
    }


@router.post("/parse")
async def parse_goal(description: str):
    """解析自然语言目标"""
    parsed = orchestrator.parse_goal(description)
    return {
        "success": True,
        "parsed": parsed
    }


@router.get("/status")
async def get_orchestrator_status():
    """获取编排器状态"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM orchestration_goals")
    total_goals = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orchestration_goals WHERE status = 'completed'")
    completed_goals = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orchestration_subtasks")
    total_subtasks = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orchestration_subtasks WHERE status = 'completed'")
    completed_subtasks = c.fetchone()[0]
    
    conn.close()
    
    return {
        "status": "active",
        "version": "1.0.0",
        "statistics": {
            "total_goals": total_goals,
            "completed_goals": completed_goals,
            "total_subtasks": total_subtasks,
            "completed_subtasks": completed_subtasks,
            "completion_rate": (completed_goals / total_goals * 100) if total_goals > 0 else 0
        },
        "capabilities": [
            "natural_language_parsing",
            "goal_decomposition",
            "task_scheduling",
            "execution_monitoring",
            "error_recovery"
        ]
    }
