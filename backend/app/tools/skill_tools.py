"""Generic tools for code-execution style skills (scripts/ + references/)."""

import asyncio
import ast
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Set

from app.tools.base import BaseTool


def _smart_decode(raw: bytes) -> str:
    """Decode subprocess output: try UTF-8 first, fallback to GBK (Windows CN)."""
    if not raw:
        return ""
    # Try UTF-8 strict
    try:
        text = raw.decode("utf-8")
        # If it decoded without error and has no replacement chars, it's valid UTF-8
        if "\ufffd" not in text:
            return text
    except UnicodeDecodeError:
        pass
    # Fallback: try GBK (common on Chinese Windows)
    try:
        return raw.decode("gbk")
    except (UnicodeDecodeError, LookupError):
        pass
    # Last resort: UTF-8 with replacement
    return raw.decode("utf-8", errors="replace")

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
    """Execute a skill script or Python snippet in the skill's scripts/ directory.

    Two modes:
    1. script_name (+ optional args): Run a trusted script file from scripts/ directly.
       No AST safety check — the script is part of the skill and trusted.
       Supports .py (Python) and .sh (Bash) scripts.
    2. code: Run a free-form Python snippet (AST safety check applied).
    """

    # Supported script extensions and their interpreters
    _SCRIPT_EXTENSIONS = {".py", ".sh"}

    def __init__(self, scripts_path: Path) -> None:
        self._scripts_path = scripts_path
        # Discover available scripts for the description
        self._available_scripts: List[str] = []
        if scripts_path.is_dir():
            self._available_scripts = sorted(
                f.name for f in scripts_path.iterdir()
                if f.is_file() and f.suffix in self._SCRIPT_EXTENSIONS and not f.name.startswith("_")
            )

    @staticmethod
    def _find_bash() -> str | None:
        """Locate bash interpreter (Git Bash on Windows, /bin/bash on Unix)."""
        import shutil
        # Unix-like
        bash = shutil.which("bash")
        if bash:
            return bash
        # Windows: Git Bash common locations
        for candidate in [
            "C:/Program Files/Git/bin/bash.exe",
            "C:/Program Files (x86)/Git/bin/bash.exe",
            "C:/Git/bin/bash.exe",
        ]:
            if Path(candidate).exists():
                return candidate
        return None

    @property
    def name(self) -> str:
        return "run_skill_script"

    @property
    def description(self) -> str:
        base = (
            "在技能的 scripts/ 目录下执行脚本或代码片段。\n"
            "模式一（推荐）：传入 script_name 直接运行 scripts/ 中的脚本文件，"
            "可选 args 传入命令行参数列表。\n"
            "模式二：传入 code 执行自定义 Python 代码片段。\n"
            "二者只需传一个，优先 script_name。"
        )
        if self._available_scripts:
            scripts_list = ", ".join(self._available_scripts)
            base += f"\n\n可用脚本文件：{scripts_list}"
        return base

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "script_name": {
                    "type": "string",
                    "description": "scripts/ 目录中的脚本文件名，如 check_ugate_token.py",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "传给脚本的命令行参数列表（可选）",
                },
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码片段（当不使用 script_name 时）",
                },
            },
        }

    async def execute(self, *, script_name: str = "", args: List[str] = None, code: str = "", **_) -> Any:
        import subprocess
        import os
        timeout_sec = 60  # longer timeout for scripts that wait for user interaction

        # Mode 1: Run a trusted script file directly (no AST check)
        if script_name:
            target = (self._scripts_path / script_name).resolve()
            # Safety: must stay within scripts_path
            if not str(target).startswith(str(self._scripts_path.resolve())):
                return {"error": "非法路径：脚本必须在 scripts/ 目录内"}
            if not target.exists():
                available = [
                    f.name for f in self._scripts_path.iterdir()
                    if f.is_file() and f.suffix in self._SCRIPT_EXTENSIONS
                ]
                return {"error": f"脚本不存在: {script_name}", "available": available}

            # Determine interpreter based on extension
            suffix = target.suffix.lower()
            if suffix == ".sh":
                # Use bash (Git Bash on Windows, /bin/bash on Unix)
                bash_path = self._find_bash()
                if not bash_path:
                    return {"error": "找不到 bash 解释器，无法执行 .sh 脚本"}
                cmd = [bash_path, str(target)] + (args or [])
            else:
                # Default: Python
                cmd = [sys.executable, str(target)] + (args or [])

            env = {**os.environ, "PYTHONPATH": str(self._scripts_path), "PYTHONIOENCODING": "utf-8"}

            def _run():
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    cwd=str(self._scripts_path),
                    env=env,
                    timeout=timeout_sec,
                )

            loop = asyncio.get_event_loop()
            try:
                proc_result = await asyncio.wait_for(
                    loop.run_in_executor(None, _run),
                    timeout=timeout_sec + 5,
                )
            except asyncio.TimeoutError:
                return {"error": f"执行超时（{timeout_sec}s）", "stdout": "", "stderr": ""}
            except subprocess.TimeoutExpired:
                return {"error": f"执行超时（{timeout_sec}s）", "stdout": "", "stderr": ""}

            stdout = _smart_decode(proc_result.stdout)
            stderr = _smart_decode(proc_result.stderr)
            return {
                "stdout": stdout,
                "stderr": stderr,
                "result": None,
                "error": f"进程退出码 {proc_result.returncode}" if proc_result.returncode else None,
            }

        # Mode 2: Run free-form code snippet (AST safety check)
        if not code:
            return {"error": "必须提供 script_name 或 code 参数"}

        violations = _validate_code_safety(code)
        if violations:
            return {"error": "代码安全检查未通过", "violations": violations}

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", dir=str(self._scripts_path),
                prefix="_run_", delete=False, encoding="utf-8",
            ) as tmp:
                tmp.write(code)
                tmp_path = tmp.name

            env = {**os.environ, "PYTHONPATH": str(self._scripts_path), "PYTHONIOENCODING": "utf-8"}

            def _run_snippet():
                return subprocess.run(
                    [sys.executable, tmp_path],
                    capture_output=True,
                    cwd=str(self._scripts_path),
                    env=env,
                    timeout=30,
                )

            loop = asyncio.get_event_loop()
            try:
                proc_result = await asyncio.wait_for(
                    loop.run_in_executor(None, _run_snippet),
                    timeout=35,
                )
            except asyncio.TimeoutError:
                return {"error": "执行超时（30s）", "stdout": "", "stderr": ""}

            stdout = _smart_decode(proc_result.stdout)
            stderr = _smart_decode(proc_result.stderr)
            return {
                "stdout": stdout,
                "stderr": stderr,
                "result": None,
                "error": f"进程退出码 {proc_result.returncode}" if proc_result.returncode else None,
            }
        except subprocess.TimeoutExpired:
            return {"error": "执行超时（30s）", "stdout": "", "stderr": ""}
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass


# ── Multi-skill versions (for general chat without a specific skill selected) ──


class MultiSkillScriptTool(BaseTool):
    """Run scripts from ANY enabled skill's scripts/ directory.

    Used in multi_skill mode when no specific skill is selected.
    Requires a skill_name parameter to route to the correct skill.
    """

    def __init__(self, skill_scripts_map: Dict[str, Path]) -> None:
        """skill_scripts_map: {skill_name: scripts_path}"""
        self._map = skill_scripts_map
        # Build available scripts per skill
        self._available: Dict[str, List[str]] = {}
        for sname, spath in skill_scripts_map.items():
            if spath.is_dir():
                scripts = sorted(
                    f.name for f in spath.iterdir()
                    if f.is_file() and f.suffix in RunSkillScriptTool._SCRIPT_EXTENSIONS and not f.name.startswith("_")
                )
                if scripts:
                    self._available[sname] = scripts

    @property
    def name(self) -> str:
        return "run_skill_script"

    @property
    def description(self) -> str:
        base = (
            "在指定技能的 scripts/ 目录下执行脚本。\n"
            "必须指定 skill_name 确定执行哪个技能的脚本，"
            "然后传入 script_name（推荐）或 code。\n\n"
        )
        if self._available:
            base += "各技能可用脚本：\n"
            for sname, scripts in self._available.items():
                base += f"  - {sname}: {', '.join(scripts)}\n"
        return base

    @property
    def input_schema(self) -> Dict[str, Any]:
        skill_names = list(self._map.keys())
        return {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "技能名称",
                    "enum": skill_names,
                },
                "script_name": {
                    "type": "string",
                    "description": "scripts/ 目录中的脚本文件名",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "传给脚本的命令行参数列表（可选）",
                },
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码片段（当不使用 script_name 时）",
                },
            },
            "required": ["skill_name"],
        }

    async def execute(self, *, skill_name: str = "", script_name: str = "", args: List[str] = None, code: str = "", **_) -> Any:
        if not skill_name:
            return {"error": "必须指定 skill_name 参数", "available_skills": list(self._map.keys())}
        scripts_path = self._map.get(skill_name)
        if scripts_path is None:
            return {"error": f"技能 '{skill_name}' 不存在或未启用", "available_skills": list(self._map.keys())}

        # Delegate to a RunSkillScriptTool instance
        runner = RunSkillScriptTool(scripts_path)
        return await runner.execute(script_name=script_name, args=args or [], code=code)


class MultiSkillReferenceTool(BaseTool):
    """Read reference docs from ANY enabled skill's references/ directory.

    Used in multi_skill mode when no specific skill is selected.
    """

    def __init__(self, skill_refs_map: Dict[str, Path]) -> None:
        """skill_refs_map: {skill_name: references_path}"""
        self._map = skill_refs_map
        # Build available references per skill
        self._available: Dict[str, List[str]] = {}
        for sname, rpath in skill_refs_map.items():
            if rpath.is_dir():
                refs = sorted(f.name for f in rpath.iterdir() if f.is_file())
                if refs:
                    self._available[sname] = refs

    @property
    def name(self) -> str:
        return "read_skill_reference"

    @property
    def description(self) -> str:
        base = (
            "读取指定技能的 references/ 目录中的参考文档。\n"
            "必须指定 skill_name 确定读取哪个技能的文档。\n\n"
        )
        if self._available:
            base += "各技能可用参考文档：\n"
            for sname, refs in self._available.items():
                base += f"  - {sname}: {', '.join(refs)}\n"
        return base

    @property
    def input_schema(self) -> Dict[str, Any]:
        skill_names = list(self._map.keys())
        return {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "技能名称",
                    "enum": skill_names,
                },
                "filename": {
                    "type": "string",
                    "description": "references/ 目录中的文件名",
                },
            },
            "required": ["skill_name", "filename"],
        }

    async def execute(self, *, skill_name: str = "", filename: str = "", **_) -> Any:
        if not skill_name:
            return {"error": "必须指定 skill_name 参数", "available_skills": list(self._map.keys())}
        refs_path = self._map.get(skill_name)
        if refs_path is None:
            return {"error": f"技能 '{skill_name}' 不存在或未启用", "available_skills": list(self._map.keys())}

        # Delegate to a ReadSkillReferenceTool instance
        reader = ReadSkillReferenceTool(refs_path)
        return await reader.execute(filename=filename)
