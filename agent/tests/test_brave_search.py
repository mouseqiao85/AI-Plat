"""Unit tests for BraveSearchTool — network is fully mocked via httpx.MockTransport."""
from __future__ import annotations

import json

import httpx
import pytest

from app.tools.brave_search import BraveSearchTool


@pytest.fixture
def tool():
    return BraveSearchTool()


def _install_transport(monkeypatch, handler):
    """Patch httpx.AsyncClient so every request routes through `handler`."""
    original = httpx.AsyncClient

    class _PatchedClient(original):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _PatchedClient)


def test_metadata_contract(tool):
    assert tool.name == "brave_search"
    assert "web" in tool.description.lower()
    schema = tool.input_schema
    assert schema["required"] == ["query"]
    assert "count" in schema["properties"]
    assert schema["properties"]["count"]["maximum"] == 20


@pytest.mark.asyncio
async def test_empty_query_returns_error(tool):
    out = await tool.execute({"query": "   "})
    assert out["success"] is False
    assert "query is required" in out["error"]


@pytest.mark.asyncio
async def test_missing_api_key_returns_structured_error(tool, monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "BRAVE_API_KEY", "", raising=False)
    out = await tool.execute({"query": "hello"})
    assert out["success"] is False
    assert "BRAVE_API_KEY" in out["error"]


@pytest.mark.asyncio
async def test_happy_path_parses_results(tool, monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "BRAVE_API_KEY", "test-key", raising=False)

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        captured["headers"] = dict(request.headers)
        body = {
            "web": {
                "results": [
                    {
                        "title": "Example Result",
                        "url": "https://example.com/a",
                        "description": "Snippet A",
                        "age": "2 days ago",
                    },
                    {
                        "title": "Second",
                        "url": "https://example.com/b",
                        "description": "Snippet B",
                    },
                ]
            }
        }
        return httpx.Response(200, content=json.dumps(body), headers={"content-type": "application/json"})

    _install_transport(monkeypatch, handler)

    out = await tool.execute({"query": "claude code", "count": 5, "country": "us"})
    assert out["success"] is True
    assert out["result"]["count"] == 2
    assert out["result"]["results"][0]["title"] == "Example Result"
    assert out["result"]["results"][0]["snippet"] == "Snippet A"
    assert out["result"]["results"][1]["age"] == ""
    # verify the caller actually sent the correct auth header and params
    assert captured["headers"].get("x-subscription-token") == "test-key"
    assert captured["params"]["q"] == "claude code"
    assert captured["params"]["count"] == "5"
    assert captured["params"]["country"] == "US"


@pytest.mark.asyncio
async def test_401_surfaces_invalid_key(tool, monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "BRAVE_API_KEY", "bad-key", raising=False)

    _install_transport(monkeypatch, lambda req: httpx.Response(401, text="unauthorized"))
    out = await tool.execute({"query": "x"})
    assert out["success"] is False
    assert "invalid or revoked" in out["error"]


@pytest.mark.asyncio
async def test_429_surfaces_rate_limit(tool, monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "BRAVE_API_KEY", "test-key", raising=False)

    _install_transport(monkeypatch, lambda req: httpx.Response(429, text="too many"))
    out = await tool.execute({"query": "x"})
    assert out["success"] is False
    assert "rate-limit" in out["error"]


@pytest.mark.asyncio
async def test_count_clamped_to_max(tool, monkeypatch):
    from app.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "BRAVE_API_KEY", "test-key", raising=False)

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["count"] = request.url.params.get("count")
        return httpx.Response(200, content=json.dumps({"web": {"results": []}}))

    _install_transport(monkeypatch, handler)

    out = await tool.execute({"query": "x", "count": 999})
    assert out["success"] is True
    assert captured["count"] == "20"
