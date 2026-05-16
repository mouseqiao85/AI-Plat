"""CreatePlanTool: LLM-callable tool that generates a plan with optional worker flag."""
from typing import Any

from app.tools.base import BaseTool


class CreatePlanTool(BaseTool):
    """Tool for LLM to create an execution plan with optional parallel workers."""

    @property
    def name(self) -> str:
        return "create_plan"

    @property
    def description(self) -> str:
        return (
            "Create an execution plan for a complex task. "
            "Set needs_workers=true if subtasks can be executed in parallel."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {"type": "string"},
                            "args": {"type": "object"},
                            "description": {"type": "string"},
                        },
                        "required": ["tool", "description"],
                    },
                    "description": "List of plan steps to execute",
                },
                "needs_workers": {
                    "type": "boolean",
                    "description": "Whether steps can be executed in parallel by workers",
                    "default": False,
                },
            },
            "required": ["steps"],
        }

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Return the plan for the graph to process."""
        steps = arguments.get("steps", [])
        needs_workers = arguments.get("needs_workers", False)
        return {
            "result": {
                "plan": steps,
                "needs_workers": needs_workers,
                "step_count": len(steps),
            },
            "success": True,
        }
