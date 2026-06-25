"""Skill management — discover, load, enable/disable skill modules."""

from app.skill.manager import SkillManager, get_skill_manager

__all__ = ["SkillManager", "get_skill_manager"]
