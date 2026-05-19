"""SkillManager: discovers, loads, enables/disables skills from YAML manifests."""
import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from app.skill.models import SkillInfo, SkillTool, SkillConfig

logger = logging.getLogger(__name__)

_STATE_FILE = ".skill_state.json"
_GITHUB_URL_RE = re.compile(
    r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+)(?:/(.+))?)?"
)


@dataclass
class GitHubSkillImportResult:
    success: bool = False
    scanned: int = 0
    imported: list[SkillInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    clone_path: str = ""


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
        """Import a skill from an external directory."""
        src = Path(skill_dir)
        manifest = src / "SKILL.md"
        if not manifest.exists():
            return None

        skill = self._parse_manifest(manifest)
        dest = self.skills_dir / skill.name
        self._copy_skill_dir(src, dest)
        skill.path = str(dest)
        self._skills[skill.name] = skill
        return skill

    def import_from_github(self, url: str, branch: str = "main", sub_path: str = "") -> GitHubSkillImportResult:
        """Clone a GitHub repository and import every SKILL.md into this manager."""
        result = GitHubSkillImportResult()
        try:
            _, _, _, url_sub_path = self._parse_github_url(url)
            clone_path = self._clone_github_repo(url, branch)
            result.clone_path = str(clone_path)
            skill_dirs = self._scan_skill_dirs(clone_path, sub_path or url_sub_path)
            result.scanned = len(skill_dirs)
            for skill_dir in skill_dirs:
                try:
                    skill = self.import_skill(str(skill_dir))
                    if skill:
                        result.imported.append(skill)
                    else:
                        result.errors.append(f"No SKILL.md in {skill_dir}")
                except Exception as exc:
                    result.errors.append(f"{skill_dir}: {exc}")
            self.discover()
            result.success = bool(result.imported)
        except Exception as exc:
            result.errors.append(str(exc))
        return result

    def _clone_github_repo(self, url: str, branch: str = "main") -> Path:
        owner, repo, url_branch, _ = self._parse_github_url(url)
        selected_branch = url_branch or branch or "main"
        target_dir = self.skills_dir / ".github_imports" / repo
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        clone_url = f"https://github.com/{owner}/{repo}.git"
        cmd = ["git", "clone", "--depth", "1", "--branch", selected_branch, clone_url, str(target_dir)]
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if completed.returncode != 0:
            if target_dir.exists():
                shutil.rmtree(target_dir)
            fallback = ["git", "clone", "--depth", "1", clone_url, str(target_dir)]
            completed = subprocess.run(fallback, capture_output=True, text=True, timeout=180)
            if completed.returncode != 0:
                raise RuntimeError(f"git clone failed: {completed.stderr.strip()}")
        return target_dir

    @staticmethod
    def _parse_github_url(url: str) -> tuple[str, str, str, str]:
        normalized = url.strip().rstrip("/")
        if normalized.endswith(".git"):
            normalized = normalized[:-4]
        match = _GITHUB_URL_RE.fullmatch(normalized)
        if not match:
            raise ValueError(f"Invalid GitHub URL: {url}")
        return match.group(1), match.group(2), match.group(3) or "", match.group(4) or ""

    @staticmethod
    def _scan_skill_dirs(root_path: Path, sub_path: str = "") -> list[Path]:
        base = root_path / sub_path if sub_path else root_path
        if not base.exists():
            raise FileNotFoundError(f"GitHub import path not found: {base}")
        skill_dirs = []
        for manifest in sorted(base.rglob("SKILL.md")):
            rel_parts = manifest.relative_to(base).parts
            if any(part.startswith(".") or part == "node_modules" for part in rel_parts):
                continue
            skill_dirs.append(manifest.parent)
        return skill_dirs

    @staticmethod
    def _copy_skill_dir(src: Path, dest: Path) -> None:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__", ".DS_Store"))

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
