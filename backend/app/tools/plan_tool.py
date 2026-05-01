from typing import Any, Dict

from app.tools.base import BaseTool


class CreatePlanTool(BaseTool):
    """Tool for creating a structured execution plan for complex tasks.

    When the agent determines a user request requires multiple steps,
    it calls this tool to create a plan. The engine intercepts the
    result to emit PLAN_CREATED SSE events and track step progress.
    """

    @property
    def name(self) -> str:
        return "create_plan"

    @property
    def description(self) -> str:
        return "为复杂任务创建执行计划。当用户请求需要多个步骤或工具调用时使用。"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "description": "步骤标识（通常为工具名或动作名）",
                            },
                            "description": {
                                "type": "string",
                                "description": "步骤的具体描述",
                            },
                        },
                        "required": ["action", "description"],
                    },
                    "description": "执行步骤列表",
                },
                "needs_workers": {
                    "type": "boolean",
                    "description": "是否需要子任务并行执行",
                    "default": False,
                },
            },
            "required": ["steps"],
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        steps = kwargs.get("steps", [])
        needs_workers = kwargs.get("needs_workers", False)
        return {
            "plan_created": True,
            "step_count": len(steps),
            "needs_workers": needs_workers,
            "steps": steps,
        }
