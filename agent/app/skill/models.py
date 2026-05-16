"""Skill data models and manifest schema."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SkillTool:
    """A tool provided by a skill."""
    name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)


@dataclass
class SkillConfig:
    """Skill configuration requirements."""
    requires: list[str] = field(default_factory=list)  # e.g. ["BRAVE_API_KEY"]


@dataclass
class SkillInfo:
    """Complete skill information parsed from SKILL.md manifest."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    tools: list[SkillTool] = field(default_factory=list)
    config: SkillConfig = field(default_factory=SkillConfig)
    documentation: str = ""  # Markdown body after front-matter
    path: str = ""  # Directory path of the skill
    enabled: bool = False

    @property
    def tool_names(self) -> list[str]:
        return [t.name for t in self.tools]
