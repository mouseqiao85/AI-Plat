import asyncio

from typing import Any, Dict, List, Optional

from app.tools.base import BaseTool

# Default timeout for tool execution (seconds)
TOOL_EXECUTE_TIMEOUT = 120


class ToolRegistry:
    """Registry that manages all available tools for the agent engine."""

    def __init__(self, tool_timeout: int = TOOL_EXECUTE_TIMEOUT) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self._tool_timeout = tool_timeout

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance in the registry."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return tool definitions in the format required by the Claude API."""
        return [tool.get_tool_definition() for tool in self._tools.values()]

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by name, or None if not found."""
        return self._tools.get(name)

    async def execute_tool(self, name: str, **kwargs) -> Any:
        """Execute a tool by name with the given keyword arguments.

        Wraps execution with a timeout to prevent hanging tools from
        blocking the entire SSE stream indefinitely.

        Raises:
            KeyError: If the tool is not registered.
            asyncio.TimeoutError: If execution exceeds the configured timeout.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' is not registered.")
        return await asyncio.wait_for(tool.execute(**kwargs), timeout=self._tool_timeout)

    def list_tools(self) -> List[str]:
        """Return a list of all registered tool names."""
        return list(self._tools.keys())
