"""SkillManager: discovers, loads, enables/disables skills from YAML manifests."""
import json
import logging
import os
from pathlib import Path
from typing import Optional

import yaml

from app.skill.models import SkillInfo, SkillTool, SkillConfig

logger = logging.getLogger(__name__)

_STATE_FILE = ".skill_state.json"


class SkillManager:
    """Manages skill lifecycle: discovery, enable/disable, manifest parsing."""

    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)
        self._skills: dict[str, SkillInfo] = {}
        self._state_path = self.skills_dir / _STATE_FILE

    def discover(self) -> list[SkillInfo]:
        """Scan skills directory and parse all SKILL.md manifests."""
        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            return []

        enabled_state = self._load_state()
        discovered = []

        for entry in self.skills_dir.iterdir():
            if not entry.is_dir():
                continue
            manifest_path = entry / "SKILL.md"
            if not manifest_path.exists():
                continue
            try:
                skill = self._parse_manifest(manifest_path)
                skill.path = str(entry)
                skill.enabled = enabled_state.get(skill.name, False)
                self._skills[skill.name] = skill
                discovered.append(skill)
            except Exception as e:
                logger.warning("failed to parse skill at %s: %s", entry, e)

        logger.info("discovered %d skills", len(discovered))
        return discovered

    def get_skill(self, name: str) -> Optional[SkillInfo]:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[SkillInfo]:
        """List all discovered skills."""
        return list(self._skills.values())

    def list_enabled(self) -> list[SkillInfo]:
        """List only enabled skills."""
        return [s for s in self._skills.values() if s.enabled]

    def enable(self, name: str) -> bool:
        """Enable a skill. Returns False if skill not found."""
        skill = self._skills.get(name)
        if not skill:
            return False
        skill.enabled = True
        self._save_state()
        logger.info("enabled skill: %s", name)
        return True

    def disable(self, name: str) -> bool:
        """Disable a skill. Returns False if skill not found."""
        skill = self._skills.get(name)
        if not skill:
            return False
        skill.enabled = False
        self._save_state()
        logger.info("disabled skill: %s", name)
        return True

    def import_skill(self, skill_dir: str) -> Optional[SkillInfo]:
        """Import a skill from an external directory by copying its manifest."""
        src = Path(skill_dir)
        manifest = src / "SKILL.md"
        if not manifest.exists():
            return None

        skill = self._parse_manifest(manifest)
        dest = self.skills_dir / skill.name
        dest.mkdir(parents=True, exist_ok=True)

        # Copy all files
        for item in src.iterdir():
            if item.is_file():
                (dest / item.name).write_text(item.read_text(encoding="utf-8"), encoding="utf-8")

        skill.path = str(dest)
        self._skills[skill.name] = skill
        return skill

    def _parse_manifest(self, path: Path) -> SkillInfo:
        """Parse a SKILL.md file with YAML front-matter + Markdown body."""
        content = path.read_text(encoding="utf-8")
        front_matter, doc_body = self._split_front_matter(content)

        data = yaml.safe_load(front_matter) or {}

        tools = []
        for t in data.get("tools", []):
            if isinstance(t, dict):
                tools.append(SkillTool(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    input_schema=t.get("input_schema", {}),
                ))
            elif isinstance(t, str):
                tools.append(SkillTool(name=t))

        config_data = data.get("config", {})
        config = SkillConfig(
            requires=config_data.get("requires", []) if isinstance(config_data, dict) else [],
        )

        return SkillInfo(
            name=data.get("name", path.parent.name),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            tools=tools,
            config=config,
            documentation=doc_body.strip(),
        )

    @staticmethod
    def _split_front_matter(content: str) -> tuple[str, str]:
        """Split YAML front-matter (between ---) from Markdown body."""
        if not content.startswith("---"):
            return "", content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return content, ""
        return parts[1], parts[2]

    def _load_state(self) -> dict[str, bool]:
        """Load enabled/disabled state from .skill_state.json."""
        if not self._state_path.exists():
            return {}
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_state(self) -> None:
        """Persist enabled/disabled state to .skill_state.json."""
        state = {name: skill.enabled for name, skill in self._skills.items()}
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# Global singleton
_manager: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    """Get or create the global skill manager."""
    global _manager
    if _manager is None:
        from app.core.config import settings
        _manager = SkillManager(settings.SKILLS_DIR)
    return _manager


def init_skill_manager(skills_dir: str) -> SkillManager:
    """Initialize the global skill manager with a specific directory."""
    global _manager
    _manager = SkillManager(skills_dir)
    _manager.discover()
    return _manager
