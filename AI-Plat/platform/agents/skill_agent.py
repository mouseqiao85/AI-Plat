"""
技能代理 (Skill Agent)
具备特定技能的智能体，可以与其他智能体协作完成复杂任务
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import logging
import json
import time
from dataclasses import dataclass, field

from .skill_registry import global_skill_registry, Skill, SkillCategory

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """智能体状态枚举"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """任务数据类"""
    id: str
    name: str
    description: str
    skill_id: str
    parameters: Dict[str, Any]
    priority: TaskPriority = TaskPriority.MEDIUM
    timeout: int = 300  # 5分钟超时
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None


class SkillAgent:
    """技能代理类"""
    
    def __init__(self, 
                 name: str, 
                 description: str,
                 skills: List[str] = None,
                 max_concurrent_tasks: int = 5):
        """
        初始化技能代理
        
        Args:
            name: 代理名称
            description: 代理描述
            skills: 可用技能ID列表
            max_concurrent_tasks: 最大并发任务数
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.skills = skills or []
        self.max_concurrent_tasks = max_concurrent_tasks
        self.status = AgentStatus.IDLE
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        
        # 任务队列
        self.task_queue = asyncio.Queue()
        self.active_tasks = {}
        self.completed_tasks = {}
        self.failed_tasks = {}
        
        # 性能统计
        self.stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_execution_time': 0,
            'avg_execution_time': 0
        }
        
        logger.info(f"Initialized SkillAgent: {name} (ID: {self.id})")
    
    async def initialize(self):
        """初始化代理"""
        # 验证技能可用性
        available_skills = []
        for skill_id in self.skills:
            skill = global_skill_registry.get_skill(skill_id)
            if skill:
                available_skills.append(skill_id)
            else:
                logger.warning(f"Skill not found: {skill_id}")
        
        self.skills = available_skills
        logger.info(f"Agent {self.name} initialized with {len(self.skills)} skills")
    
    def can_execute_skill(self, skill_id: str) -> bool:
        """
        检查是否可以执行指定技能
        
        Args:
            skill_id: 技能ID
            
        Returns:
            是否可以执行
        """
        return skill_id in self.skills
    
    async def add_task(self, 
                      name: str, 
                      description: str, 
                      skill_id: str, 
                      parameters: Dict[str, Any],
                      priority: TaskPriority = TaskPriority.MEDIUM) -> str:
        """
        添加任务到队列
        
        Args:
            name: 任务名称
            description: 任务描述
            skill_id: 技能ID
            parameters: 参数字典
            priority: 任务优先级
            
        Returns:
            任务ID
        """
        if not self.can_execute_skill(skill_id):
            raise ValueError(f"Agent cannot execute skill: {skill_id}")
        
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name,
            description=description,
            skill_id=skill_id,
            parameters=parameters,
            priority=priority
        )
        
        await self.task_queue.put(task)
        logger.info(f"Added task {task_id} to queue for agent {self.name}")
        
        # 如果代理空闲，开始处理任务
        if self.status == AgentStatus.IDLE:
            asyncio.create_task(self.process_tasks())
        
        return task_id
    
    async def process_tasks(self):
        """处理任务队列"""
        if self.status != AgentStatus.IDLE:
            return  # 已经在处理任务
        
        self.status = AgentStatus.BUSY
        logger.info(f"Agent {self.name} started processing tasks")
        
        while not self.task_queue.empty():
            try:
                task = await self.task_queue.get()
                
                # 检查是否有足够的并发槽位
                if len(self.active_tasks) >= self.max_concurrent_tasks:
                    await self.task_queue.put(task)  # 放回队列等待
                    await asyncio.sleep(0.1)
                    continue
                
                # 执行任务
                task_id = task.id
                self.active_tasks[task_id] = task
                task.started_at = datetime.now()
                
                # 创建异步任务
                asyncio.create_task(self._execute_task(task))
                
                self.last_activity = datetime.now()
                
            except Exception as e:
                logger.error(f"Error processing task queue: {str(e)}")
                break
        
        self.status = AgentStatus.IDLE
        logger.info(f"Agent {self.name} finished processing tasks")
    
    async def _execute_task(self, task: Task):
        """执行单个任务"""
        start_time = time.time()
        
        try:
            logger.info(f"Executing task {task.id} with skill {task.skill_id}")
            
            # 获取技能
            skill = global_skill_registry.get_skill(task.skill_id)
            if not skill:
                raise ValueError(f"Skill not found: {task.skill_id}")
            
            # 执行技能
            result = await asyncio.wait_for(
                self._run_skill_with_context(skill, task.parameters),
                timeout=task.timeout
            )
            
            # 记录成功结果
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.now()
            
            # 移动到完成队列
            self.completed_tasks[task.id] = task
            del self.active_tasks[task.id]
            
            # 更新统计
            execution_time = time.time() - start_time
            self.stats['tasks_completed'] += 1
            self.stats['total_execution_time'] += execution_time
            self.stats['avg_execution_time'] = (
                self.stats['total_execution_time'] / self.stats['tasks_completed']
            )
            
            logger.info(f"Task {task.id} completed successfully")
            
        except asyncio.TimeoutError:
            error_msg = f"Task {task.id} timed out after {task.timeout}s"
            self._handle_task_error(task, error_msg)
            
        except Exception as e:
            error_msg = f"Task {task.id} failed: {str(e)}"
            self._handle_task_error(task, error_msg)
    
    async def _run_skill_with_context(self, skill: Skill, parameters: Dict[str, Any]):
        """在上下文中运行技能"""
        # 这里可以添加上下文管理逻辑
        # 例如：添加代理ID、时间戳等上下文信息
        context_params = parameters.copy()
        context_params['_agent_id'] = self.id
        context_params['_execution_time'] = datetime.now().isoformat()
        
        # 执行技能
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, skill.execute, context_params)
        
        return result
    
    def _handle_task_error(self, task: Task, error_msg: str):
        """处理任务错误"""
        task.status = "failed"
        task.error = error_msg
        task.completed_at = datetime.now()
        
        # 移动到失败队列
        self.failed_tasks[task.id] = task
        if task.id in self.active_tasks:
            del self.active_tasks[task.id]
        
        # 更新统计
        self.stats['tasks_failed'] += 1
        
        logger.error(error_msg)
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务结果字典
        """
        task = (self.completed_tasks.get(task_id) or 
                self.failed_tasks.get(task_id) or 
                self.active_tasks.get(task_id))
        
        if not task:
            return None
        
        return {
            'id': task.id,
            'name': task.name,
            'status': task.status,
            'result': task.result,
            'error': task.error,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        }
    
    def get_available_skills(self) -> List[Dict[str, Any]]:
        """
        获取可用技能列表
        
        Returns:
            技能信息列表
        """
        available_skills = []
        for skill_id in self.skills:
            skill = global_skill_registry.get_skill(skill_id)
            if skill:
                available_skills.append({
                    'id': skill.metadata.id,
                    'name': skill.metadata.name,
                    'description': skill.metadata.description,
                    'category': skill.metadata.category.value,
                    'version': skill.metadata.version,
                    'input_schema': skill.metadata.input_schema,
                    'output_schema': skill.metadata.output_schema
                })
        
        return available_skills
    
    def get_status_report(self) -> Dict[str, Any]:
        """
        获取状态报告
        
        Returns:
            状态报告字典
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'queue_size': self.task_queue.qsize(),
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'failed_tasks': len(self.failed_tasks),
            'stats': self.stats,
            'available_skills_count': len(self.get_available_skills())
        }
    
    async def execute_skill_directly(self, 
                                   skill_id: str, 
                                   parameters: Dict[str, Any]) -> Any:
        """
        直接执行技能（不通过任务队列）
        
        Args:
            skill_id: 技能ID
            parameters: 参数
            
        Returns:
            技能执行结果
        """
        if not self.can_execute_skill(skill_id):
            raise ValueError(f"Agent cannot execute skill: {skill_id}")
        
        skill = global_skill_registry.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")
        
        self.status = AgentStatus.BUSY
        self.last_activity = datetime.now()
        
        try:
            result = await self._run_skill_with_context(skill, parameters)
            self.stats['tasks_completed'] += 1
            return result
        except Exception as e:
            self.stats['tasks_failed'] += 1
            raise e
        finally:
            self.status = AgentStatus.IDLE
    
    async def shutdown(self):
        """关闭代理"""
        logger.info(f"Shutting down agent {self.name}")
        
        # 等待所有活跃任务完成
        while self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} tasks to complete...")
            await asyncio.sleep(1)
        
        logger.info(f"Agent {self.name} shut down successfully")


# 示例使用
async def main():
    """示例主函数"""
    print("=== 技能代理示例 ===")
    
    # 创建代理
    agent = SkillAgent(
        name="DataProcessingAgent",
        description="专门处理数据的技能代理",
        skills=[],  # 我们稍后会添加技能
        max_concurrent_tasks=3
    )
    
    # 初始化代理
    await agent.initialize()
    
    # 获取全局注册中心中的技能ID
    all_skills = global_skill_registry.list_skills()
    skill_ids = [skill.metadata.id for skill in all_skills]
    
    # 将技能分配给代理
    agent.skills = skill_ids[:2]  # 分配前两个技能
    
    print(f"Agent initialized with skills: {[global_skill_registry.get_skill(sid).metadata.name for sid in agent.skills]}")
    
    # 添加任务
    task1_id = await agent.add_task(
        name="Process User Data",
        description="Clean and process user data",
        skill_id=agent.skills[0] if agent.skills else "",
        parameters={
            "data": [{"name": "张三", "age": 30, "city": "北京"}, 
                     {"name": "李四", "age": None, "city": "上海"}],
            "operation": "clean"
        },
        priority=TaskPriority.HIGH
    )
    
    print(f"Added task: {task1_id}")
    
    # 等待任务完成
    await asyncio.sleep(2)
    
    # 获取结果
    result = agent.get_task_result(task1_id)
    print(f"Task result: {result}")
    
    # 获取状态报告
    status = agent.get_status_report()
    print(f"Agent status: {status}")
    
    # 关闭代理
    await agent.shutdown()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())