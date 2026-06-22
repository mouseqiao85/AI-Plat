"""WebSearchTool: Brave Search API integration for Python-side tool execution.

This tool allows the responder node to search the internet directly from
the Python agent process, without needing to proxy through the Go gateway.
"""
import json
import logging
from typing import Any

import httpx

from app.tools.base import BaseTool
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Search the internet via Brave Search API."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "搜索互联网获取最新信息。支持中英文关键词搜索。"
            "当你需要查找实时信息、新闻、网页内容时使用此工具。"
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，支持中英文",
                },
                "count": {
                    "type": "integer",
                    "description": "返回结果数量，默认5",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = arguments.get("query", "")
        if not query:
            return {"result": "缺少搜索关键词", "success": False}

        count = int(arguments.get("count", 5))
        if count < 1:
            count = 5
        if count > 20:
            count = 20

        api_key = settings.BRAVE_API_KEY or ""
        if not api_key:
            return {"result": "BRAVE_API_KEY 未配置，无法搜索", "success": False}

        try:
            results = await self._brave_search(api_key, query, count)
            return {"result": json.dumps(results, ensure_ascii=False), "success": True}
        except Exception as e:
            logger.error("web_search failed: %s", e)
            return {"result": f"搜索失败: {str(e)}", "success": False}

    async def _brave_search(self, api_key: str, query: str, count: int) -> list[dict]:
        """Execute Brave Search API call."""
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        }
        params = {"q": query, "count": count}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        web_results = data.get("web", {}).get("results", [])
        results = []
        for r in web_results:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("description", ""),
            })

        return results
