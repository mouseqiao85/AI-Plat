"""Generic tools for code-execution style skills (scripts/ + references/)."""

import asyncio
import ast
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Set

from app.tools.base import BaseTool

# Modules/functions that must never be executed in skill scripts
_BLOCKED_MODULES: Set[str] = {
    "os", "subprocess", "shutil", "signal", "ctypes",
    "multiprocessing", "socket", "http", "urllib",
    "xmlrpc", "telnetlib", "ftplib", "smtplib",
    "pickle", "shelve", "marshal",
}
_BLOCKED_BUILTINS: Set[str] = {
    "exec", "eval", "compile", "__import__",
    "open", "input", "breakpoint",
    "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr", "type",
}


def _validate_code_safety(code: str) -> List[str]:
    """AST-level blocklist check. Returns list of violations (empty = safe)."""
    violations: List[str] = []
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as e:
        return [f"语法错误: {e}"]

    for node in ast.walk(tree):
        # Block `import os`, `from os import ...`
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_mod = alias.name.split(".")[0]
                if root_mod in _BLOCKED_MODULES:
                    violations.append(f"禁止导入模块: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_mod = node.module.split(".")[0]
                if root_mod in _BLOCKED_MODULES:
                    violations.append(f"禁止从模块导入: {node.module}")
        # Block direct builtin calls like eval(), exec(), open()
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _BLOCKED_BUILTINS:
                violations.append(f"禁止调用: {func.id}()")
            # Block os.system(), subprocess.run() etc.
            if isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name) and func.value.id in _BLOCKED_MODULES:
                    violations.append(f"禁止调用: {func.value.id}.{func.attr}()")
        # Block attribute access to __dunder__ on objects
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                violations.append(f"禁止访问 dunder 属性: {node.attr}")

    return violations


class ReadSkillReferenceTool(BaseTool):
    """Read a file from the skill's references/ directory."""

    def __init__(self, references_path: Path) -> None:
        self._references_path = references_path

    @property
    def name(self) -> str:
        return "read_skill_reference"

    @property
    def description(self) -> str:
        return (
            "读取技能 references/ 目录中的参考文档（Markdown 格式）。"
            "在调用 API 前请先读取对应文档了解参数细节和示例。"
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "references/ 目录中的文件名，例如 create_doc.md",
                }
            },
            "required": ["filename"],
        }

    async def execute(self, *, filename: str, **_) -> Any:
        target = (self._references_path / filename).resolve()
        # Safety: must stay within references_path
        if not str(target).startswith(str(self._references_path.resolve())):
            return {"error": "非法路径"}
        if not target.exists():
            available = [f.name for f in self._references_path.iterdir() if f.is_file()]
            return {"error": f"文件不存在: {filename}", "available": available}
        try:
            return {"filename": filename, "content": target.read_text(encoding="utf-8")}
        except Exception as exc:
            return {"error": str(exc)}


class RunSkillScriptTool(BaseTool):
    """Execute a Python snippet using the skill's scripts/ directory as working directory."""

    def __init__(self, scripts_path: Path) -> None:
        self._scripts_path = scripts_path

    @property
    def name(self) -> str:
        return "run_skill_script"

    @property
    def description(self) -> str:
        return (
            "在技能的 scripts/ 目录下执行 Python 代码片段。"
            "scripts/ 目录及其父目录均已加入 sys.path，支持两种 import 写法："
            "直接 import 模块（如 from ku_api_client import KuApiClient）"
            "或通过包名导入（如 from scripts import KuApiClient）。"
            "输出 stdout/stderr 和返回值。"
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码，支持多行。最后一个表达式的值作为 result 返回。",
                }
            },
            "required": ["code"],
        }

    async def execute(self, *, code: str, **_) -> Any:
        # Layer 1: AST blocklist validation
        violations = _validate_code_safety(code)
        if violations:
            return {"error": "代码安全检查未通过", "violations": violations}

        # Layer 2: Run in subprocess with timeout (not in-process exec/eval)
        timeout_sec = 30
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", dir=str(self._scripts_path),
                prefix="_run_", delete=False, encoding="utf-8",
            ) as tmp:
                tmp.write(code)
                tmp_path = tmp.name

            proc = await asyncio.create_subprocess_exec(
                sys.executable, tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._scripts_path),
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout_sec
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {"error": f"执行超时（{timeout_sec}s）", "stdout": "", "stderr": ""}

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            return {
                "stdout": stdout,
                "stderr": stderr,
                "result": None,
                "error": f"进程退出码 {proc.returncode}" if proc.returncode else None,
            }
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}
        finally:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass
