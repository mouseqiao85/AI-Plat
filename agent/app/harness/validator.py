"""Validator subsystem for agent-platform."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    STRICT = "strict"
    NORMAL = "normal"
    LENIENT = "lenient"


@dataclass
class ValidationResult:
    passed: bool
    issues: List[str] = field(default_factory=list)
    level: ValidationLevel = ValidationLevel.NORMAL
    rewritten: Optional[str] = None

    def __bool__(self) -> bool:
        return self.passed


class InputGuard:
    MAX_CHARS = 0

    _INJECTION_PATTERNS: List[str] = [
        r"ignore\s+previous\s+instructions?",
        r"you\s+are\s+now",
        r"system\s+prompt",
        r"disregard\s+all",
        r"forget\s+your\s+instructions?",
        r"新的?指令",
        r"忽略(之前|前面|上面)的?指令",
    ]

    def validate(self, text: str, level: ValidationLevel = ValidationLevel.NORMAL) -> ValidationResult:
        issues: List[str] = []
        if self.MAX_CHARS > 0 and len(text) > self.MAX_CHARS:
            issues.append(f"输入超过长度限制（最大 {self.MAX_CHARS} 字符，当前 {len(text)} 字符）")
        for pattern in self._INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append("检测到 Prompt 注入尝试")
                break
        if level == ValidationLevel.STRICT:
            passed = len(issues) == 0
        elif level == ValidationLevel.LENIENT:
            passed = not any("注入" in i for i in issues)
        else:
            fatal = [i for i in issues if "注入" in i or "长度" in i]
            passed = len(fatal) == 0
        return ValidationResult(passed=passed, issues=issues, level=level)


class ToolValidator:
    _REQUIRED_PARAMS: Dict[str, List[str]] = {"brave_search": ["query"], "web_search": ["query"]}

    def validate(self, tool_name: str, params: Dict[str, Any], user_tier: str = "free") -> ValidationResult:
        issues: List[str] = []
        required = self._REQUIRED_PARAMS.get(tool_name, [])
        missing = [p for p in required if not params.get(p)]
        if missing:
            issues.append(f"工具 {tool_name} 缺少必要参数：{', '.join(missing)}")
        return ValidationResult(passed=len(issues) == 0, issues=issues)


class OutputGuard:
    _HARMFUL_PHRASES: List[Tuple[str, str]] = []

    def validate(self, text: str, level: ValidationLevel = ValidationLevel.NORMAL, auto_rewrite: bool = True) -> ValidationResult:
        issues: List[str] = []
        rewritten = text
        for pattern, hint in self._HARMFUL_PHRASES:
            if re.search(pattern, text):
                issues.append(f"包含不当内容（匹配：{pattern}）")
                if auto_rewrite and hint:
                    rewritten = re.sub(pattern, hint, rewritten)
        passed = len(issues) == 0 if level == ValidationLevel.STRICT else True
        return ValidationResult(passed=passed, issues=issues, level=level,
                               rewritten=rewritten if rewritten != text else None)


class ResultValidator:
    def validate(self, result: Any) -> ValidationResult:
        if result is None:
            return ValidationResult(passed=False, issues=["工具返回值为 None"])
        if isinstance(result, dict) and "error" in result:
            return ValidationResult(passed=False, issues=[f"工具执行错误：{result['error']}"])
        if isinstance(result, str) and result.strip() == "":
            return ValidationResult(passed=False, issues=["工具返回空字符串"])
        return ValidationResult(passed=True)


class Validator:
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL) -> None:
        self.level = level
        self.input_guard = InputGuard()
        self.tool_validator = ToolValidator()
        self.output_guard = OutputGuard()
        self.result_validator = ResultValidator()

    def validate_input(self, text: str, level: Optional[ValidationLevel] = None) -> ValidationResult:
        return self.input_guard.validate(text, level=level or self.level)

    def validate_tool(self, tool_name: str, params: Dict[str, Any], user_tier: str = "free") -> ValidationResult:
        return self.tool_validator.validate(tool_name, params, user_tier)

    def validate_output(self, text: str, level: Optional[ValidationLevel] = None, auto_rewrite: bool = True) -> ValidationResult:
        return self.output_guard.validate(text, level=level or self.level, auto_rewrite=auto_rewrite)

    def validate_tool_result(self, result: Any) -> ValidationResult:
        return self.result_validator.validate(result)


_validator: Optional[Validator] = None


def get_validator(level: ValidationLevel = ValidationLevel.NORMAL) -> Validator:
    global _validator
    if _validator is None:
        _validator = Validator(level=level)
    return _validator
