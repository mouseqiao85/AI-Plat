"""Base tool abstraction for Python-side tools."""
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for all Python-side tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        ...

    @property
    def input_schema(self) -> dict:
        """JSON Schema for the tool's input parameters."""
        return {"type": "object", "properties": {}}

    @abstractmethod
    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool with given arguments.

        Returns:
            dict with at least {"result": ..., "success": bool}
        """
        ...

    def to_openai_format(self) -> dict:
        """Export tool definition in OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }
