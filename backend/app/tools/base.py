from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the tool."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema describing the tool's input parameters."""
        ...

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return the tool definition in OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with the given arguments and return the result."""
        ...
