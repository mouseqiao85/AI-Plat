"""Generic tools for code-execution style skills (scripts/ + references/)."""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

from app.tools.base import BaseTool


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
        scripts_dir = str(self._scripts_path.resolve())
        parent_dir = str(self._scripts_path.parent.resolve())

        def _run() -> Dict[str, Any]:
            import io
            import contextlib

            # Inject scripts_path and its parent into sys.path
            injected = []
            for p in (scripts_dir, parent_dir):
                if p not in sys.path:
                    sys.path.insert(0, p)
                    injected.append(p)

            stdout_buf = io.StringIO()
            stderr_buf = io.StringIO()
            local_ns: Dict[str, Any] = {}
            result = None
            error = None

            try:
                with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                    # Split into statements; exec all but eval the last expression
                    import ast
                    tree = ast.parse(code, mode="exec")
                    if tree.body and isinstance(tree.body[-1], ast.Expr):
                        # Separate last expression for eval
                        last_expr = ast.Expression(body=tree.body[-1].value)
                        ast.fix_missing_locations(last_expr)
                        exec_tree = ast.Module(body=tree.body[:-1], type_ignores=[])
                        ast.fix_missing_locations(exec_tree)
                        exec(compile(exec_tree, "<skill>", "exec"), local_ns)
                        result = eval(compile(last_expr, "<skill>", "eval"), local_ns)
                    else:
                        exec(compile(tree, "<skill>", "exec"), local_ns)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            finally:
                for p in injected:
                    if p in sys.path:
                        sys.path.remove(p)

            return {
                "stdout": stdout_buf.getvalue(),
                "stderr": stderr_buf.getvalue(),
                "result": result,
                "error": error,
            }

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run)
