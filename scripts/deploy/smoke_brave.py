"""Smoke-test the new brave_search module using the live agent venv.

Run directly on the server:
  /home/admin/agent-platform/agent/.venv/bin/python smoke_brave.py
"""
import ast, pathlib, sys, os

NEW = pathlib.Path("/home/admin/agent-platform-new/agent")

for rel in ["app/tools/brave_search.py", "main.py"]:
    p = NEW / rel
    try:
        ast.parse(p.read_text())
        print(f"[syntax OK] {rel}")
    except SyntaxError as e:
        print(f"[syntax FAIL] {rel}: {e}")
        sys.exit(2)

# Import check: make agent dir importable
sys.path.insert(0, str(NEW))
os.chdir(NEW)

try:
    from app.tools.brave_search import BraveSearchTool
    t = BraveSearchTool()
    assert t.name == "brave_search", t.name
    assert t.input_schema["required"] == ["query"]
    assert t.input_schema["properties"]["count"]["maximum"] == 20
    print(f"[import OK] BraveSearchTool.name={t.name}")
    print(f"[schema OK] required={t.input_schema['required']}, count.max={t.input_schema['properties']['count']['maximum']}")
except Exception as e:
    print(f"[import FAIL] {type(e).__name__}: {e}")
    sys.exit(3)

# Smoke-test execute with no API key → should return structured error, not raise
import asyncio
from app.core import config as cfg
cfg.settings.BRAVE_API_KEY = ""
out = asyncio.run(t.execute({"query": "hello"}))
if out.get("success") is False and "BRAVE_API_KEY" in (out.get("error") or ""):
    print(f"[execute-no-key OK] {out['error']}")
else:
    print(f"[execute-no-key FAIL] {out}")
    sys.exit(4)

# Smoke-test empty query
out = asyncio.run(t.execute({"query": "   "}))
if out.get("success") is False and "query is required" in (out.get("error") or ""):
    print(f"[execute-empty-query OK] {out['error']}")
else:
    print(f"[execute-empty-query FAIL] {out}")
    sys.exit(5)

print("\nALL SMOKE CHECKS PASSED")
