"""BraveSearchTool: LLM-callable web search via Brave Search API.

Requires BRAVE_API_KEY env var (see app/core/config.py). If unset, the tool
returns a structured error rather than raising — the LLM can decide whether
to apologise to the user or fall back to another source.

Brave free tier rate-limits at 1 req/s, so concurrent worker dispatch will
hit 429. We serialize requests with a process-wide semaphore + min-interval
clock and retry transient 429s with exponential backoff.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
_DEFAULT_TIMEOUT = 10.0
_MAX_COUNT = 20

_RATE_LIMIT_SEM = asyncio.Semaphore(1)
_RATE_LIMIT_LOCK = asyncio.Lock()
_MIN_INTERVAL_S = 1.1
_LAST_CALL_TS = 0.0
_MAX_RETRIES = 3
_BACKOFF_BASE_S = 1.5


async def _gated_get(client: httpx.AsyncClient, params: dict, headers: dict) -> httpx.Response:
    """Send one Brave request behind the global 1 req/s gate."""
    global _LAST_CALL_TS
    async with _RATE_LIMIT_SEM:
        async with _RATE_LIMIT_LOCK:
            now = asyncio.get_event_loop().time()
            wait = _LAST_CALL_TS + _MIN_INTERVAL_S - now
            if wait > 0:
                await asyncio.sleep(wait)
            _LAST_CALL_TS = asyncio.get_event_loop().time()
        return await client.get(_ENDPOINT, params=params, headers=headers)


class BraveSearchTool(BaseTool):
    """Web search tool backed by Brave Search API."""

    @property
    def name(self) -> str:
        return "brave_search"

    @property
    def description(self) -> str:
        return (
            "Search the web via Brave Search. Returns a list of results with "
            "title, url, and snippet. Use for current-events, factual lookups, "
            "or when the user explicitly asks to search the web. Prefer a "
            "specific query over a generic one."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific.",
                },
                "count": {
                    "type": "integer",
                    "description": f"Number of results to return (1-{_MAX_COUNT}).",
                    "default": 10,
                    "minimum": 1,
                    "maximum": _MAX_COUNT,
                },
                "country": {
                    "type": "string",
                    "description": "2-letter country code for result localization (e.g. 'CN', 'US'). Default 'CN'.",
                    "default": "CN",
                },
                "safesearch": {
                    "type": "string",
                    "enum": ["strict", "moderate", "off"],
                    "description": "Safe-search filter level.",
                    "default": "moderate",
                },
            },
            "required": ["query"],
        }

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = (arguments.get("query") or "").strip()
        if not query:
            return {"success": False, "result": None, "error": "query is required and must be non-empty"}

        if not settings.BRAVE_API_KEY:
            return {
                "success": False,
                "result": None,
                "error": "BRAVE_API_KEY not configured on the server. Ask the operator to set it in .env.",
            }

        count = max(1, min(int(arguments.get("count", 10)), _MAX_COUNT))
        country = (arguments.get("country") or "CN").upper()
        safesearch = arguments.get("safesearch") or "moderate"

        params = {
            "q": query,
            "count": count,
            "country": country,
            "safesearch": safesearch,
        }
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": settings.BRAVE_API_KEY,
        }

        try:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
                resp: httpx.Response | None = None
                last_429_body = ""
                for attempt in range(_MAX_RETRIES):
                    resp = await _gated_get(client, params, headers)
                    if resp.status_code != 429:
                        break
                    last_429_body = (resp.text or "")[:120]
                    backoff = _BACKOFF_BASE_S * (2 ** attempt)
                    logger.warning(
                        "brave_search 429 attempt=%d backoff=%.1fs q=%r",
                        attempt + 1, backoff, query,
                    )
                    await asyncio.sleep(backoff)
        except httpx.TimeoutException:
            logger.warning("brave_search timeout: q=%r", query)
            return {"success": False, "result": None, "error": f"brave search timed out after {_DEFAULT_TIMEOUT}s"}
        except httpx.HTTPError as exc:
            logger.warning("brave_search http error: %s", exc)
            return {"success": False, "result": None, "error": f"brave search network error: {exc}"}

        if resp.status_code == 401:
            return {"success": False, "result": None, "error": "BRAVE_API_KEY is invalid or revoked"}
        if resp.status_code == 429:
            return {
                "success": False,
                "result": None,
                "error": f"brave search rate-limit exceeded after {_MAX_RETRIES} retries: {last_429_body}",
            }
        if resp.status_code >= 400:
            body = (resp.text or "")[:200]
            return {
                "success": False,
                "result": None,
                "error": f"brave search HTTP {resp.status_code}: {body}",
            }

        try:
            data = resp.json()
        except ValueError:
            return {"success": False, "result": None, "error": "brave search returned non-JSON response"}

        web_results = (data.get("web") or {}).get("results") or []
        simplified = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                "age": item.get("age", ""),
            }
            for item in web_results[:count]
        ]

        return {
            "success": True,
            "result": {
                "query": query,
                "count": len(simplified),
                "results": simplified,
            },
        }
