"""指令子系统

Manages all Agent prompts and instructions:
- Five instruction types: System / Task / Tool / Context / Safety
- Jinja2 template rendering with variable injection
- Version management with rollback support
- General-purpose defaults (role definition, safety rules, output formats)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from string import Template as _StrTemplate
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


# ── Instruction types ─────────────────────────────────────────────────────────

class InstructionType(str, Enum):
    SYSTEM  = "system"    # Agent role definition & behaviour constraints
    TASK    = "task"      # Specific task description
    TOOL    = "tool"      # Tool-call guidance
    CONTEXT = "context"   # Dynamic context injection
    SAFETY  = "safety"    # Constraint & boundary rules


# ── Built-in general-purpose templates ──────────────────────────────────────

_DEFAULT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    InstructionType.SYSTEM: {
        "version": "1.0.0",
        "template": (
            "你是${role}。\n\n"
            "行为规则：\n${rules}\n\n"
            "当前时间：${timestamp}\n"
            "用户等级：${user_tier}"
        ),
        "defaults": {
            "role": "通用智能助手",
            "rules": "- 回答准确简洁\n- 不确定时明确说明\n- 需要实时信息时调用工具",
            "timestamp": "",   # filled at render time
            "user_tier": "free",
        },
    },
    InstructionType.TASK: {
        "version": "1.0.0",
        "template": (
            "任务：${task}\n"
            "上下文：${context}\n"
            "可用工具：${tools}\n\n"
            "请分析用户意图，制定执行计划。"
        ),
        "defaults": {
            "task": "",
            "context": "无",
            "tools": "web_search",
        },
    },
    InstructionType.TOOL: {
        "version": "1.0.0",
        "template": (
            "工具：${tool_name}\n"
            "说明：${tool_description}\n"
            "参数：${tool_params}\n\n"
            "调用时请严格遵守参数格式。"
        ),
        "defaults": {
            "tool_name": "",
            "tool_description": "",
            "tool_params": "{}",
        },
    },
    InstructionType.CONTEXT: {
        "version": "1.0.0",
        "template": (
            "历史摘要：${history_summary}"
        ),
        "defaults": {
            "history_summary": "无",
        },
    },
    InstructionType.SAFETY: {
        "version": "1.0.0",
        "template": (
            "安全约束（必须遵守）：\n${safety_rules}\n\n"
            "违规处理：${violation_action}"
        ),
        "defaults": {
            "safety_rules": (
                "1. 不得协助违法活动\n"
                "2. 不得生成有害、歧视性内容\n"
                "3. 数据引用必须注明来源\n"
                "4. 不确定时明确说明"
            ),
            "violation_action": "礼貌拒绝并说明原因",
        },
    },
}


# ── Version entry ─────────────────────────────────────────────────────────────

@dataclass
class PromptVersion:
    template: str
    version: str
    defaults: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    description: str = ""


# ── Instruction builder ───────────────────────────────────────────────────────

class InstructionBuilder:
    """Build and manage Agent prompts with versioning support.

    Usage::

        builder = InstructionBuilder()
        prompt = builder.build(InstructionType.SYSTEM, user_tier="pro")
    """

    def __init__(self) -> None:
        # name → list[PromptVersion], latest last
        self._registry: Dict[str, List[PromptVersion]] = {}
        self._load_defaults()

    # ── Public API ────────────────────────────────────────────────────────────

    def build(
        self,
        instruction_type: InstructionType,
        version: Optional[str] = None,
        **variables: Any,
    ) -> str:
        """Render a prompt template with the supplied variables.

        Missing variables fall back to the template's defaults.
        """
        name = instruction_type.value
        pv = self._get_version(name, version)
        if pv is None:
            logger.warning("instruction_not_found", name=name)
            return ""

        ctx: Dict[str, Any] = {**pv.defaults}
        # Inject timestamp if present in defaults
        if "timestamp" in ctx:
            from datetime import datetime
            ctx["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ctx.update({k: v for k, v in variables.items() if v is not None})

        try:
            rendered = _StrTemplate(pv.template).safe_substitute(ctx)
        except Exception as exc:
            logger.error("instruction_render_failed", name=name, error=str(exc))
            rendered = pv.template

        logger.debug("instruction_built", name=name, version=pv.version)
        return rendered

    def build_system_prompt(self, **variables: Any) -> str:
        return self.build(InstructionType.SYSTEM, **variables)

    def build_task_prompt(self, task: str, **variables: Any) -> str:
        return self.build(InstructionType.TASK, task=task, **variables)

    def build_safety_prompt(self, **variables: Any) -> str:
        return self.build(InstructionType.SAFETY, **variables)

    def build_context_prompt(self, **variables: Any) -> str:
        return self.build(InstructionType.CONTEXT, **variables)

    def build_full_system(
        self,
        user_tier: str = "free",
        skill_description: str = "",
        user_profile_str: str = "",
        **extras: Any,
    ) -> str:
        """Assemble system + context + safety into one combined prompt."""
        parts: List[str] = []

        system = self.build_system_prompt(user_tier=user_tier, **extras)
        if system:
            parts.append(system)

        if skill_description:
            parts.append(f"\n当前技能：\n{skill_description}")

        # Inject user profile between skill description and context
        if user_profile_str:
            parts.append(user_profile_str)

        ctx = self.build_context_prompt()
        if ctx:
            parts.append(ctx)

        safety = self.build_safety_prompt()
        if safety:
            parts.append(safety)

        # Plan instruction — guide the agent to use create_plan for complex tasks
        plan_instruction = (
            "当你判断用户请求需要多个步骤或工具调用时，请先调用 create_plan 工具创建执行计划，"
            "然后按计划逐步执行。简单问题直接回答，无需创建计划。\n"
            "如果多个子任务互相独立且可以并行，设置 needs_workers=true。\n"
            "当有多个技能工具可用时，请优先选择与用户请求最匹配的技能工具，"
            "参考技能说明和关键词选择合适的工具，不要随意混用不同技能的工具。"
        )
        parts.append(plan_instruction)

        return "\n\n".join(parts)

    def register(
        self,
        name: str,
        template: str,
        version: str,
        defaults: Optional[Dict[str, Any]] = None,
        description: str = "",
    ) -> None:
        """Register a new (or updated) prompt template version."""
        pv = PromptVersion(
            template=template,
            version=version,
            defaults=defaults or {},
            description=description,
        )
        if name not in self._registry:
            self._registry[name] = []
        self._registry[name].append(pv)
        logger.info("instruction_registered", name=name, version=version)

    def list_versions(self, name: str) -> List[Dict[str, Any]]:
        """Return metadata for all registered versions of a prompt."""
        return [
            {
                "version": pv.version,
                "description": pv.description,
                "created_at": pv.created_at,
            }
            for pv in self._registry.get(name, [])
        ]

    def rollback(self, name: str) -> bool:
        """Remove the latest version, reverting to the previous one."""
        versions = self._registry.get(name, [])
        if len(versions) <= 1:
            return False
        versions.pop()
        logger.info("instruction_rolled_back", name=name, reverted_to=versions[-1].version)
        return True

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_defaults(self) -> None:
        for itype, spec in _DEFAULT_TEMPLATES.items():
            name = itype if isinstance(itype, str) else itype.value
            pv = PromptVersion(
                template=spec["template"],
                version=spec["version"],
                defaults=spec.get("defaults", {}),
                description=f"Built-in {name} template",
            )
            self._registry[name] = [pv]

    def _get_version(
        self, name: str, version: Optional[str]
    ) -> Optional[PromptVersion]:
        versions = self._registry.get(name, [])
        if not versions:
            return None
        if version is None:
            return versions[-1]  # latest
        for pv in reversed(versions):
            if pv.version == version:
                return pv
        return None


# ── Module-level singleton ────────────────────────────────────────────────────
_builder: Optional[InstructionBuilder] = None


def get_instruction_builder() -> InstructionBuilder:
    global _builder
    if _builder is None:
        _builder = InstructionBuilder()
    return _builder
