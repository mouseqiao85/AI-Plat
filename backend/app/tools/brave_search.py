"""Brave Web Search tool — real-time web search via the Brave Search API."""

import asyncio
import gzip
import http.client
import json
import socket
import ssl
import urllib.parse
from typing import Any, Dict, List

import httpx

from app.core.config import settings
from app.tools.base import BaseTool


class _IPv4SNIHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, resolved_ip: str, timeout: float) -> None:
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self._resolved_ip = resolved_ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self._resolved_ip, self.port), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


class BraveSearchTool(BaseTool):
    """Search the web using Brave Search API for real-time information."""

    _API_HOST = "api.search.brave.com"
    _API_PATH = "/res/v1/web/search"
    _API_BASE = f"https://{_API_HOST}{_API_PATH}"

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "使用Brave搜索引擎搜索互联网信息。适用于获取实时新闻、最新事件、"
            "产品信息、技术文档、公司动态等各类网络内容。"
            "当用户询问需要最新信息的问题时优先使用此工具。"
            "输入搜索关键词，返回相关网页标题、摘要和链接。"
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，如 'Python异步编程'、'2024年诺贝尔奖'、'最新AI模型发布'",
                },
                "count": {
                    "type": "integer",
                    "description": "返回结果数量，默认5条，最多10条",
                    "default": 5,
                },
                "search_lang": {
                    "type": "string",
                    "description": "搜索语言，默认 'zh-hans'（简体中文）",
                    "default": "zh-hans",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> Any:
        query = kwargs.get("query", "").strip()
        count = min(max(kwargs.get("count", 5), 1), 10)
        search_lang = kwargs.get("search_lang", "zh-hans")

        if not query:
            return {"error": "搜索关键词不能为空"}

        api_key = settings.BRAVE_API_KEY
        if not api_key:
            return {"error": "BRAVE_API_KEY 未配置，无法执行网页搜索"}

        try:
            results = await self._search(query, count, search_lang)
            return results
        except Exception as exc:
            message = str(exc) or repr(exc)
            return {"error": f"网页搜索失败: {message}", "query": query}

    async def _search(self, query: str, count: int, search_lang: str) -> Dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Connection": "close",
            "Host": self._API_HOST,
            "X-Subscription-Token": settings.BRAVE_API_KEY,
        }
        params = {
            "q": query,
            "count": count,
            "search_lang": search_lang,
            "text_decorations": False,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(self._API_BASE, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.ConnectError, httpx.ConnectTimeout):
            data = await asyncio.to_thread(self._search_over_ipv4, headers, params)

        return self._format_results(query, data)

    def _search_over_ipv4(self, headers: Dict[str, str], params: Dict[str, Any]) -> Dict[str, Any]:
        query_string = urllib.parse.urlencode(params)
        path = f"{self._API_PATH}?{query_string}"
        last_error: Exception | None = None

        for ip in self._resolve_ipv4_candidates():
            conn: _IPv4SNIHTTPSConnection | None = None
            try:
                conn = _IPv4SNIHTTPSConnection(self._API_HOST, ip, timeout=15.0)
                conn.request("GET", path, headers=headers)
                resp = conn.getresponse()
                raw = resp.read()
                if resp.getheader("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                body = raw.decode("utf-8")
                if resp.status >= 400:
                    raise RuntimeError(f"HTTP {resp.status}: {body[:300]}")
                return json.loads(body)
            except Exception as exc:
                last_error = exc
            finally:
                if conn is not None:
                    conn.close()

        raise RuntimeError(f"IPv4 fallback failed: {last_error!r}")

    def _resolve_ipv4_candidates(self) -> List[str]:
        configured_ips = [ip.strip() for ip in settings.BRAVE_API_IPS.split(",") if ip.strip()]
        if configured_ips:
            return configured_ips
        return socket.gethostbyname_ex(self._API_HOST)[2]

    def _format_results(self, query: str, data: Dict[str, Any]) -> Dict[str, Any]:
        web_results = data.get("web", {}).get("results", [])
        items: List[Dict[str, Any]] = []
        for r in web_results:
            item: Dict[str, Any] = {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "description": r.get("description", ""),
            }
            if age := r.get("age"):
                item["age"] = age
            items.append(item)

        return {
            "query": query,
            "total": len(items),
            "results": items,
        }
