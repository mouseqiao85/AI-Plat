"""Python-side tool registry for skill tools and built-in Python tools."""
import logging
from typing import Optional

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for Python-side tools (skill tools + built-in Python tools).

    These tools execute locally in the Python agent process, unlike
    Go gateway tools which require HTTP callbacks.
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        if tool.name in self._tools:
            logger.warning("overwriting tool registration: %s", tool.name)
        self._tools[tool.name] = tool
        logger.info("registered python tool: %s", tool.name)

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def list_tools(self) -> list[BaseTool]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_openai_tools(self) -> list[dict]:
        """Export all tools in OpenAI function-calling format."""
        return [t.to_openai_format() for t in self._tools.values()]

    def clear(self) -> None:
        """Remove all tools."""
        self._tools.clear()


# Global singleton
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
