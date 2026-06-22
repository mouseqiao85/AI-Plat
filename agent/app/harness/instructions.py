"""Instruction subsystem for agent-platform."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from string import Template as _StrTemplate
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class InstructionType(str, Enum):
    SYSTEM = "system"
    TASK = "task"
    TOOL = "tool"
    CONTEXT = "context"
    SAFETY = "safety"


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
            "timestamp": "",
            "user_tier": "free",
        },
    },
    InstructionType.TASK: {
        "version": "1.0.0",
        "template": "任务：${task}\n上下文：${context}\n可用工具：${tools}\n\n请分析用户意图，制定执行计划。",
        "defaults": {"task": "", "context": "无", "tools": "brave_search"},
    },
    InstructionType.TOOL: {
        "version": "1.0.0",
        "template": "工具：${tool_name}\n说明：${tool_description}\n参数：${tool_params}\n\n调用时请严格遵守参数格式。",
        "defaults": {"tool_name": "", "tool_description": "", "tool_params": "{}"},
    },
    InstructionType.CONTEXT: {
        "version": "1.0.0",
        "template": "历史摘要：${history_summary}",
        "defaults": {"history_summary": "无"},
    },
    InstructionType.SAFETY: {
        "version": "1.0.0",
        "template": "安全约束（必须遵守）：\n${safety_rules}\n\n违规处理：${violation_action}",
        "defaults": {
            "safety_rules": "1. 不得协助违法活动\n2. 不得生成有害、歧视性内容\n3. 数据引用必须注明来源\n4. 不确定时明确说明",
            "violation_action": "礼貌拒绝并说明原因",
        },
    },
}


@dataclass
class PromptVersion:
    template: str
    version: str
    defaults: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    description: str = ""


class InstructionBuilder:
    def __init__(self) -> None:
        self._registry: Dict[str, List[PromptVersion]] = {}
        self._load_defaults()

    def build(self, instruction_type: InstructionType, version: Optional[str] = None, **variables: Any) -> str:
        name = instruction_type.value
        pv = self._get_version(name, version)
        if pv is None:
            return ""
        ctx: Dict[str, Any] = {**pv.defaults}
        if "timestamp" in ctx:
            from datetime import datetime
            ctx["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ctx.update({k: v for k, v in variables.items() if v is not None})
        try:
            return _StrTemplate(pv.template).safe_substitute(ctx)
        except Exception:
            return pv.template

    def build_system_prompt(self, **variables: Any) -> str:
        return self.build(InstructionType.SYSTEM, **variables)

    def build_task_prompt(self, task: str, **variables: Any) -> str:
        return self.build(InstructionType.TASK, task=task, **variables)

    def build_safety_prompt(self, **variables: Any) -> str:
        return self.build(InstructionType.SAFETY, **variables)

    def build_context_prompt(self, **variables: Any) -> str:
        return self.build(InstructionType.CONTEXT, **variables)

    def build_full_system(
        self, user_tier: str = "free", skill_description: str = "", user_profile_str: str = "", **extras: Any,
    ) -> str:
        parts: List[str] = []
        system = self.build_system_prompt(user_tier=user_tier, **extras)
        if system:
            parts.append(system)
        if skill_description:
            parts.append(f"\n当前技能：\n{skill_description}")
        if user_profile_str:
            parts.append(user_profile_str)
        ctx = self.build_context_prompt()
        if ctx:
            parts.append(ctx)
        safety = self.build_safety_prompt()
        if safety:
            parts.append(safety)
        parts.append("当你判断用户请求需要多个步骤或工具调用时，请先创建执行计划，然后按计划逐步执行。简单问题直接回答。")
        return "\n\n".join(parts)

    def register(self, name: str, template: str, version: str, defaults: Optional[Dict[str, Any]] = None, description: str = "") -> None:
        pv = PromptVersion(template=template, version=version, defaults=defaults or {}, description=description)
        if name not in self._registry:
            self._registry[name] = []
        self._registry[name].append(pv)

    def _load_defaults(self) -> None:
        for itype, spec in _DEFAULT_TEMPLATES.items():
            name = itype.value if isinstance(itype, InstructionType) else itype
            self._registry[name] = [PromptVersion(
                template=spec["template"], version=spec["version"],
                defaults=spec.get("defaults", {}), description=f"Built-in {name} template",
            )]

    def _get_version(self, name: str, version: Optional[str]) -> Optional[PromptVersion]:
        versions = self._registry.get(name, [])
        if not versions:
            return None
        if version is None:
            return versions[-1]
        for pv in reversed(versions):
            if pv.version == version:
                return pv
        return None


_builder: Optional[InstructionBuilder] = None


def get_instruction_builder() -> InstructionBuilder:
    global _builder
    if _builder is None:
        _builder = InstructionBuilder()
    return _builder
