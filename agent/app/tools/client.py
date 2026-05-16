import httpx
from typing import Any, Optional
from app.core.config import settings


class ToolClient:
    """HTTP client to call Go gateway for tool execution."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.GO_CALLBACK_URL
        self.timeout = settings.TOOL_TIMEOUT

    async def execute_tool(
        self, tool_name: str, arguments: dict, session_id: str
    ) -> dict:
        """Execute a tool via the Go gateway."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/api/v1/tools/execute",
                    json={
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "session_id": session_id,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "success": data.get("success", False),
                        "result": data.get("result"),
                        "error": data.get("error"),
                    }
                return {
                    "success": False,
                    "error": f"tool execution returned {resp.status_code}: {resp.text}",
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def list_tools(self) -> list:
        """List available tools from Go gateway."""
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(f"{self.base_url}/api/v1/tools")
                if resp.status_code == 200:
                    return resp.json().get("tools", [])
                return []
            except Exception:
                return []


tool_client = ToolClient()
