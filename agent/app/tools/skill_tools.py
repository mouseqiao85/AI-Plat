"""Skill-specific tools: RunSkillScriptTool and ReadSkillReferenceTool."""
import ast
import asyncio
import logging
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Dangerous modules and builtins that are blocked in skill scripts
BLOCKED_MODULES = {"os", "subprocess", "shutil", "sys", "importlib", "ctypes", "socket"}
BLOCKED_BUILTINS = {"exec", "eval", "compile", "__import__", "open", "input"}


def _check_script_safety(code: str) -> tuple[bool, str]:
    """AST-level safety check for skill scripts.

    Returns (is_safe, reason).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"syntax error: {e}"

    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in BLOCKED_MODULES:
                    return False, f"blocked module import: {mod}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.split(".")[0]
                if mod in BLOCKED_MODULES:
                    return False, f"blocked module import: {mod}"
        # Check dangerous builtins
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in BLOCKED_BUILTINS:
                return False, f"blocked builtin call: {func.id}"
            elif isinstance(func, ast.Attribute) and func.attr in BLOCKED_BUILTINS:
                return False, f"blocked builtin call: {func.attr}"

    return True, ""


class RunSkillScriptTool(BaseTool):
    """Execute a skill's Python script in a sandboxed environment."""

    def __init__(self, skill_name: str, script_path: str, description: str = ""):
        self._name = f"skill_{skill_name}_run"
        self._description = description or f"Run {skill_name} skill script"
        self._script_path = script_path
        self._skill_name = skill_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input data for the skill script",
                },
                "params": {
                    "type": "object",
                    "description": "Additional parameters",
                },
            },
        }

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute the skill script with safety checks."""
        script_path = Path(self._script_path)
        if not script_path.exists():
            return {"result": f"Script not found: {self._script_path}", "success": False}

        code = script_path.read_text(encoding="utf-8")

        # Safety check
        is_safe, reason = _check_script_safety(code)
        if not is_safe:
            return {"result": f"Script blocked: {reason}", "success": False}

        # Execute in restricted namespace
        timeout = getattr(settings, "SKILL_SCRIPT_TIMEOUT", 30)
        namespace = {
            "__builtins__": {
                k: v for k, v in __builtins__.items()
                if k not in BLOCKED_BUILTINS
            } if isinstance(__builtins__, dict) else {
                k: getattr(__builtins__, k)
                for k in dir(__builtins__)
                if k not in BLOCKED_BUILTINS and not k.startswith("_")
            },
            "input_data": arguments.get("input", ""),
            "params": arguments.get("params", {}),
            "result": None,
        }

        try:
            # Run in thread with timeout
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, exec, code, namespace),
                timeout=timeout,
            )
            result = namespace.get("result", "Script completed without setting result")
            return {"result": result, "success": True}
        except asyncio.TimeoutError:
            return {"result": f"Script timed out after {timeout}s", "success": False}
        except Exception as e:
            return {"result": f"Script error: {str(e)}", "success": False}


class ReadSkillReferenceTool(BaseTool):
    """Read a skill's reference documentation."""

    def __init__(self, skill_name: str, doc_content: str):
        self._name = f"skill_{skill_name}_ref"
        self._description = f"Read {skill_name} skill reference documentation"
        self._doc_content = doc_content

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": "Optional section to read (default: full doc)",
                },
            },
        }

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Return the skill documentation."""
        section = arguments.get("section", "")
        if section and section in self._doc_content:
            # Try to extract the section
            lines = self._doc_content.split("\n")
            in_section = False
            section_lines = []
            for line in lines:
                if section.lower() in line.lower() and line.startswith("#"):
                    in_section = True
                    section_lines.append(line)
                elif in_section and line.startswith("#") and section.lower() not in line.lower():
                    break
                elif in_section:
                    section_lines.append(line)
            if section_lines:
                return {"result": "\n".join(section_lines), "success": True}

        return {"result": self._doc_content, "success": True}
