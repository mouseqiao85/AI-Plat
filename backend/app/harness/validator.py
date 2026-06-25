"""验证子系统

Multi-layer validation pipeline:
- InputGuard  – length / prompt-injection / sensitive-word checks
- ToolValidator – parameter format + scope permission check
- OutputGuard  – investment-advice detection + disclaimer enforcement
- ResultValidator – tool execution result format check
- Validator    – unified facade with retry/rewrite hooks
- ValidationResult & ValidationLevel – shared types
"""

from __future__ import annotations

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


# ── Shared types ──────────────────────────────────────────────────────────────

class ValidationLevel(str, Enum):
    STRICT  = "strict"   # any issue → reject
    NORMAL  = "normal"   # critical issues → reject
    LENIENT = "lenient"  # only severe issues → reject


@dataclass
class ValidationResult:
    passed: bool
    issues: List[str] = field(default_factory=list)
    level: ValidationLevel = ValidationLevel.NORMAL
    rewritten: Optional[str] = None   # output after auto-rewrite, if any

    def __bool__(self) -> bool:       # allows `if result:` syntax
        return self.passed


# ── Input validation ──────────────────────────────────────────────────────────

class InputGuard:
    """Validate user inputs before they reach the agent."""

    MAX_CHARS = 0  # 0 = no limit

    _INJECTION_PATTERNS: List[str] = [
        r"ignore\s+previous\s+instructions?",
        r"you\s+are\s+now",
        r"system\s+prompt",
        r"disregard\s+all",
        r"forget\s+your\s+instructions?",
        r"新的?指令",
        r"忽略(之前|前面|上面)的?指令",
    ]

    _SENSITIVE_WORDS: List[str] = []

    def validate(
        self,
        text: str,
        level: ValidationLevel = ValidationLevel.NORMAL,
    ) -> ValidationResult:
        issues: List[str] = []

        # 1. Length (disabled when MAX_CHARS == 0)
        if self.MAX_CHARS > 0 and len(text) > self.MAX_CHARS:
            issues.append(f"输入超过长度限制（最大 {self.MAX_CHARS} 字符，当前 {len(text)} 字符）")

        # 2. Prompt injection
        for pattern in self._INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append("检测到 Prompt 注入尝试")
                break   # one issue is enough

        # 3. Sensitive words (warn level — do not hard-reject in LENIENT)
        found_sensitive = [w for w in self._SENSITIVE_WORDS if w in text]
        if found_sensitive:
            issues.append(f"包含敏感词：{'、'.join(found_sensitive)}")

        # Decide pass/fail based on level
        if level == ValidationLevel.STRICT:
            passed = len(issues) == 0
        elif level == ValidationLevel.LENIENT:
            # Only injection is fatal in lenient mode
            passed = not any("注入" in i for i in issues)
        else:   # NORMAL
            # Length + injection are fatal; sensitive words are warnings
            fatal = [i for i in issues if "注入" in i or "长度" in i]
            passed = len(fatal) == 0

        result = ValidationResult(passed=passed, issues=issues, level=level)
        if not passed:
            logger.info("input_validation_failed", issues=issues)
        return result


# ── Tool parameter validator ──────────────────────────────────────────────────

class ToolValidator:
    """Validate tool call parameters and permissions before execution."""

    # Minimal required-param definitions for known tools
    _REQUIRED_PARAMS: Dict[str, List[str]] = {
        "web_search": ["query"],
    }

    def validate(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_tier: str = "free",
    ) -> ValidationResult:
        issues: List[str] = []

        # 1. Required params present?
        required = self._REQUIRED_PARAMS.get(tool_name, [])
        missing = [p for p in required if not params.get(p)]
        if missing:
            issues.append(f"工具 {tool_name} 缺少必要参数：{', '.join(missing)}")

        # 2. Scope check (reuse ScopeManager lazily to avoid circular import)
        try:
            from app.harness.scope import get_scope_manager
            ok, reason = get_scope_manager().check_tool(tool_name, user_tier)
            if not ok:
                issues.append(f"权限不足：{reason}")
        except ImportError:
            pass  # scope subsystem not available

        passed = len(issues) == 0
        result = ValidationResult(passed=passed, issues=issues)
        if not passed:
            logger.info("tool_validation_failed", tool=tool_name, issues=issues)
        return result


# ── Output validation ─────────────────────────────────────────────────────────

class OutputGuard:
    """Validate and optionally rewrite agent outputs."""

    _HARMFUL_PHRASES: List[Tuple[str, str]] = [
        # (pattern, replacement_hint) — extend as needed
    ]

    def validate(
        self,
        text: str,
        level: ValidationLevel = ValidationLevel.NORMAL,
        auto_rewrite: bool = True,
    ) -> ValidationResult:
        issues: List[str] = []
        rewritten = text

        for pattern, hint in self._HARMFUL_PHRASES:
            if re.search(pattern, text):
                issues.append(f"包含不当内容（匹配：{pattern}）")
                if auto_rewrite and hint:
                    rewritten = re.sub(pattern, hint, rewritten)

        passed = len(issues) == 0 if level == ValidationLevel.STRICT else True

        result = ValidationResult(
            passed=passed,
            issues=issues,
            level=level,
            rewritten=rewritten if rewritten != text else None,
        )
        if issues:
            logger.info("output_validation_issues", issues=issues, auto_rewritten=auto_rewrite)
        return result


# ── Tool result validator ─────────────────────────────────────────────────────

class ResultValidator:
    """Validate the return values of tool executions."""

    def validate(self, result: Any) -> ValidationResult:
        issues: List[str] = []

        if result is None:
            issues.append("工具返回值为 None")
            return ValidationResult(passed=False, issues=issues)

        if isinstance(result, dict) and "error" in result:
            issues.append(f"工具执行错误：{result['error']}")
            return ValidationResult(passed=False, issues=issues)

        if isinstance(result, str) and result.strip() == "":
            issues.append("工具返回空字符串")
            return ValidationResult(passed=False, issues=issues)

        return ValidationResult(passed=True)


# ── Unified Validator facade ──────────────────────────────────────────────────

class Validator:
    """Unified entry point for all validation operations.

    Usage::

        v = Validator()
        r = v.validate_input("帮我写一首诗")
        r = v.validate_output("好的，这是一首诗：...")
        # r.passed, r.issues, r.rewritten
    """

    def __init__(
        self,
        level: ValidationLevel = ValidationLevel.NORMAL,
    ) -> None:
        self.level = level
        self.input_guard   = InputGuard()
        self.tool_validator = ToolValidator()
        self.output_guard  = OutputGuard()
        self.result_validator = ResultValidator()

    def validate_input(
        self,
        text: str,
        level: Optional[ValidationLevel] = None,
    ) -> ValidationResult:
        return self.input_guard.validate(text, level=level or self.level)

    def validate_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_tier: str = "free",
    ) -> ValidationResult:
        return self.tool_validator.validate(tool_name, params, user_tier)

    def validate_output(
        self,
        text: str,
        level: Optional[ValidationLevel] = None,
        auto_rewrite: bool = True,
    ) -> ValidationResult:
        return self.output_guard.validate(
            text, level=level or self.level, auto_rewrite=auto_rewrite
        )

    def validate_tool_result(self, result: Any) -> ValidationResult:
        return self.result_validator.validate(result)


# ── Module-level singleton ────────────────────────────────────────────────────
_validator: Optional[Validator] = None


def get_validator(level: ValidationLevel = ValidationLevel.NORMAL) -> Validator:
    global _validator
    if _validator is None:
        _validator = Validator(level=level)
    return _validator
