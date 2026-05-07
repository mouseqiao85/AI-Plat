"""Skill manager — discovers skill.md files, tracks enabled state, loads tools."""

from __future__ import annotations

import json
import os
import shutil
import structlog
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Project root (for state file location and relative path resolution)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve_skills_dir() -> Path:
    """Determine the skills sandbox directory.

    Priority:
    1. settings.SKILLS_DIR if non-empty
    2. <project_root>/skills/
    """
    if settings.SKILLS_DIR:
        p = Path(settings.SKILLS_DIR)
    else:
        p = _PROJECT_ROOT / "skills"
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()


SKILLS_DIR = _resolve_skills_dir()


class SkillInfo:
    """Parsed representation of a single skill."""

    def __init__(self, path: Path, manifest: Dict[str, Any]) -> None:
        self.path = path
        self.manifest = manifest

    @property
    def name(self) -> str:
        return self.manifest.get("name", self.path.name)

    @property
    def version(self) -> str:
        return self.manifest.get("version", "0.0.0")

    @property
    def description(self) -> str:
        return self.manifest.get("description", "")

    @property
    def author(self) -> str:
        return self.manifest.get("author", "")

    @property
    def license(self) -> str:
        return self.manifest.get("license", "")

    @property
    def keywords(self) -> List[str]:
        return self.manifest.get("keywords", [])

    @property
    def dependencies(self) -> List[str]:
        return self.manifest.get("dependencies", [])

    @property
    def tools(self) -> List[Dict[str, Any]]:
        return self.manifest.get("tools", [])

    @property
    def requires_config(self) -> List[str]:
        cfg = self.manifest.get("config", {})
        return cfg.get("requires", [])

    @property
    def optional_config(self) -> List[str]:
        cfg = self.manifest.get("config", {})
        return cfg.get("optional", [])

    @property
    def enabled_default(self) -> bool:
        return self.manifest.get("enabled", True)

    @property
    def skill_md_content(self) -> str:
        """Full text of skill.md (front-matter stripped)."""
        for fname in ("skill.md", "SKILL.md"):
            p = self.path / fname
            if p.exists():
                try:
                    text = p.read_text(encoding="utf-8")
                    # Strip YAML front-matter
                    if text.startswith("---"):
                        parts = text.split("---", 2)
                        return parts[2].strip() if len(parts) >= 3 else text
                    return text
                except Exception:
                    return ""
        return ""

    @property
    def scripts_path(self) -> Optional[Path]:
        """Path to scripts/ sub-directory, if it exists."""
        p = self.path / "scripts"
        return p if p.is_dir() else None

    @property
    def references_path(self) -> Optional[Path]:
        """Path to references/ sub-directory, if it exists."""
        p = self.path / "references"
        return p if p.is_dir() else None

    @property
    def references(self) -> List[str]:
        """List of filenames inside references/ sub-directory."""
        p = self.path / "references"
        if not p.is_dir():
            return []
        return sorted(f.name for f in p.iterdir() if f.is_file())

    def to_dict(self, enabled: bool, config_ok: bool) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "keywords": self.keywords,
            "dependencies": self.dependencies,
            "tools": [
                {"name": t.get("name", ""), "description": t.get("description", "")}
                for t in self.tools
            ],
            "requires_config": self.requires_config,
            "optional_config": self.optional_config,
            "enabled": enabled,
            "config_ok": config_ok,
            "path": str(self.path),
            "skill_md_content": self.skill_md_content,
            "scripts_path": str(self.scripts_path) if self.scripts_path else None,
            "references": self.references,
        }


class SkillManager:
    """Discover and manage skills.

    A *skill* is a directory under the project root that contains a ``skill.md``
    (or ``SKILL.md``) with YAML front-matter describing its metadata and tools.

    The manager:
    1. Scans for ``skill.md`` / ``SKILL.md`` on startup.
    2. Persists enable/disable state in a JSON file next to the project root.
    3. Provides methods to list, enable, disable, and check skills.
    4. Loads tool classes from skill manifests for registration with ToolRegistry.
    """

    _STATE_FILE = _PROJECT_ROOT / ".skill_state.json"

    def __init__(self) -> None:
        self._skills: Dict[str, SkillInfo] = {}  # name -> SkillInfo
        self._enabled: Dict[str, bool] = {}       # name -> enabled
        self._loaded = False
        self._file_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> None:
        """Scan SKILLS_DIR for skill.md files and populate the skill registry.

        Only scans the unified sandbox directory (SKILLS_DIR). Skills must be
        imported via add_skill() to be recognized.
        """
        seen_paths: set = set()

        if SKILLS_DIR.is_dir():
            for child in sorted(SKILLS_DIR.iterdir()):
                if not child.is_dir():
                    continue
                if child.name.startswith((".", "_", "node_modules", "venv", "__pycache__")):
                    continue
                for fname in ("skill.md", "SKILL.md"):
                    manifest_path = child / fname
                    if manifest_path.exists():
                        real = str(manifest_path.resolve())
                        if real in seen_paths:
                            continue
                        seen_paths.add(real)
                        info = self._parse_manifest(manifest_path)
                        if info:
                            self._skills[info.name] = info
                        break  # don't parse both skill.md and SKILL.md

        # Load persisted enable/disable state
        self._load_state()

        # For skills without persisted state, use manifest default
        for name, info in self._skills.items():
            if name not in self._enabled:
                self._enabled[name] = info.enabled_default

        # Clean stale entries: remove enabled state for skills no longer on disk
        stale = [n for n in self._enabled if n not in self._skills]
        for n in stale:
            del self._enabled[n]
        if stale:
            self._save_state()
            logger.info("skills_stale_cleaned", removed=stale)

        self._loaded = True
        logger.info(
            "skills_discovered",
            count=len(self._skills),
            names=list(self._skills.keys()),
            skills_dir=str(SKILLS_DIR),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_skills(self) -> List[Dict[str, Any]]:
        """Return metadata for all discovered skills."""
        if not self._loaded:
            self.discover()
        result = []
        for name, info in sorted(self._skills.items()):
            enabled = self._enabled.get(name, False)
            config_ok = self._check_config(info)
            result.append(info.to_dict(enabled=enabled, config_ok=config_ok))
        return result

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Return metadata for a single skill, or None."""
        if not self._loaded:
            self.discover()
        info = self._skills.get(name)
        if not info:
            return None
        enabled = self._enabled.get(name, False)
        config_ok = self._check_config(info)
        return info.to_dict(enabled=enabled, config_ok=config_ok)

    def enable_skill(self, name: str) -> bool:
        """Enable a skill. Returns True if successful."""
        if name not in self._skills:
            return False
        self._enabled[name] = True
        self._save_state()
        logger.info("skill_enabled", name=name)
        return True

    def disable_skill(self, name: str) -> bool:
        """Disable a skill. Returns True if successful."""
        if name not in self._skills:
            return False
        self._enabled[name] = False
        self._save_state()
        logger.info("skill_disabled", name=name)
        return True

    def add_skill(self, path: str) -> Optional[Dict[str, Any]]:
        """Import a skill from any directory into the sandbox.

        The skill directory is **moved** into SKILLS_DIR (copied then source
        removed) so that it becomes self-contained. No restriction on source
        location — accepts any absolute path or relative path (resolved against
        the project root).

        Returns the skill metadata dict on success, or None on failure.
        """
        target = Path(path)
        if not target.is_absolute():
            target = _PROJECT_ROOT / target
        target = target.resolve()

        if not target.is_dir():
            logger.warning("skill_add_not_dir", path=str(target))
            return None

        # Look for skill.md / SKILL.md
        manifest_path = None
        for fname in ("skill.md", "SKILL.md"):
            candidate = target / fname
            if candidate.exists():
                manifest_path = candidate
                break

        if manifest_path is None:
            logger.warning("skill_add_no_manifest", path=str(target))
            return None

        # Validate & auto-fix before parsing
        validation = self.validate_and_fix_manifest(manifest_path)
        if validation["errors"]:
            logger.warning("skill_manifest_errors", path=str(manifest_path), errors=validation["errors"])
            return None

        # Parse to get the skill name
        info = self._parse_manifest(manifest_path)
        if info is None:
            return None

        # Copy into SKILLS_DIR (use skill name as directory name for consistency)
        dest = SKILLS_DIR / info.name
        if dest.exists() and dest.resolve() != target:
            # Remove old version before re-importing
            shutil.rmtree(dest, ignore_errors=True)

        # If source is already inside SKILLS_DIR, skip move
        if target.resolve() != dest.resolve():
            try:
                shutil.copytree(target, dest, dirs_exist_ok=True)
                # Remove source after successful copy (move semantics)
                shutil.rmtree(target, ignore_errors=True)
                logger.info("skill_moved_to_sandbox", name=info.name, src=str(target), dest=str(dest))
            except Exception as exc:
                logger.error("skill_move_failed", name=info.name, error=str(exc))
                return None

            # Re-parse from new location
            new_manifest = dest / manifest_path.name
            info = self._parse_manifest(new_manifest)
            if info is None:
                return None

        self._skills[info.name] = info
        if info.name not in self._enabled:
            self._enabled[info.name] = info.enabled_default
        self._save_state()

        enabled = self._enabled[info.name]
        config_ok = self._check_config(info)
        logger.info("skill_added", name=info.name, path=str(dest))
        result = info.to_dict(enabled=enabled, config_ok=config_ok)
        result["validation"] = validation
        return result

    def remove_skill(self, name: str) -> bool:
        """Remove a skill by name. Deletes from sandbox and state. Returns True if successful."""
        info = self._skills.get(name)
        if info is None:
            return False

        # Always remove the skill directory from sandbox
        sandbox_path = SKILLS_DIR / name
        for candidate in (sandbox_path, info.path.resolve()):
            if candidate.is_dir():
                try:
                    shutil.rmtree(candidate)
                    logger.info("skill_dir_removed", name=name, path=str(candidate))
                except Exception as exc:
                    logger.warning("skill_dir_remove_failed", name=name, error=str(exc))

        del self._skills[name]
        self._enabled.pop(name, None)
        # Also clean runtime_info
        state = self._load_full_state()
        state.get("runtime_info", {}).pop(name, None)
        state["enabled"] = self._enabled
        self._save_full_state(state)
        logger.info("skill_removed", name=name)
        return True

    def is_enabled(self, name: str) -> bool:
        """Check if a skill is currently enabled."""
        return self._enabled.get(name, False)

    def get_enabled_tools(self) -> List[Dict[str, Any]]:
        """Return tool descriptors for all enabled skills.

        Each descriptor has: name, module, class — ready for dynamic import.
        """
        if not self._loaded:
            self.discover()
        tools = []
        for name, info in self._skills.items():
            if not self._enabled.get(name, False):
                continue
            if not self._check_config(info):
                # Config missing — skip silently at runtime (already warned at import)
                continue
            for tool_desc in info.tools:
                tools.append(tool_desc)
        return tools

    def get_enabled_skill_names(self) -> List[str]:
        """Return names of all enabled skills."""
        return [n for n, e in self._enabled.items() if e]

    def get_enabled_skills_catalog(self) -> List[Dict[str, Any]]:
        """Return a lightweight catalog of enabled skills for system prompt injection.

        Each entry contains: name, description, tools (name + description only),
        keywords, and config_ok status.
        """
        if not self._loaded:
            self.discover()
        catalog = []
        for name, info in sorted(self._skills.items()):
            if not self._enabled.get(name, False):
                continue
            config_ok = self._check_config(info)
            if not config_ok:
                continue
            catalog.append({
                "name": info.name,
                "description": info.description,
                "keywords": info.keywords,
                "tools": [
                    {"name": t.get("name", ""), "description": t.get("description", "")}
                    for t in info.tools
                ],
            })
        return catalog

    def update_skill_runtime_info(
        self,
        name: str,
        tools_called: List[str],
        missing_deps: Optional[List[str]] = None,
    ) -> None:
        """Record runtime tool usage and missing deps back into state file.

        Stored under key ``runtime_info`` in the state JSON, keyed by skill name.
        This info is displayed in the frontend skill card and persists across restarts.
        """
        if name not in self._skills:
            return
        state = self._load_full_state()
        if "runtime_info" not in state:
            state["runtime_info"] = {}
        prev = state["runtime_info"].get(name, {})
        # Merge with previous recorded calls (dedup)
        all_called = sorted(set(prev.get("tools_called", []) + tools_called))
        entry: Dict[str, Any] = {
            "last_used": datetime.now(timezone.utc).isoformat(),
            "tools_called": all_called,
        }
        if missing_deps:
            entry["missing_deps"] = sorted(set(prev.get("missing_deps", []) + missing_deps))
        state["runtime_info"][name] = entry
        self._save_full_state(state)
        logger.info("skill_runtime_info_updated", name=name, tools_called=all_called)

    def get_skill_runtime_info(self, name: str) -> Dict[str, Any]:
        """Return persisted runtime info for a skill (empty dict if none)."""
        state = self._load_full_state()
        return state.get("runtime_info", {}).get(name, {})

    # ------------------------------------------------------------------
    # Manifest validation & auto-fix
    # ------------------------------------------------------------------

    @staticmethod
    def validate_and_fix_manifest(path: Path) -> Dict[str, Any]:
        """Validate a skill.md file, auto-fix minor issues, and return a report.

        Returns a dict with keys:
          - fixed (bool): whether the file was rewritten
          - issues (List[str]): problems found
          - fixes (List[str]): auto-fixes applied
          - errors (List[str]): fatal problems that could not be fixed
        """
        report: Dict[str, Any] = {"fixed": False, "issues": [], "fixes": [], "errors": []}

        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            report["errors"].append(f"无法读取文件: {exc}")
            return report

        dir_name = path.parent.name

        # ── 1. Ensure YAML front-matter exists ────────────────────────
        if not text.startswith("---"):
            report["issues"].append("缺少 YAML front-matter（--- 分隔符）")
            # Wrap entire file as body; create minimal front-matter
            first_line = next((l.strip() for l in text.splitlines() if l.strip()), "")
            body_desc = first_line[:100] if first_line else dir_name
            text = f"---\nname: {dir_name}\nversion: \"0.1.0\"\ndescription: \"{body_desc}\"\n---\n\n{text}"
            report["fixes"].append("已自动添加 front-matter，name/version/description 从文件内容推断")

        parts = text.split("---", 2)
        if len(parts) < 3:
            report["errors"].append("front-matter 格式错误：缺少结束 --- 分隔符，无法自动修复")
            return report

        raw_fm, body = parts[1], parts[2]

        # ── 2. Parse YAML ─────────────────────────────────────────────
        try:
            manifest = yaml.safe_load(raw_fm) or {}
        except yaml.YAMLError as exc:
            report["errors"].append(f"YAML 解析失败（需手动修复）: {exc}")
            return report

        if not isinstance(manifest, dict):
            report["errors"].append("front-matter 解析结果不是字典，无法自动修复")
            return report

        changed = False

        # ── 3. Required field: name ───────────────────────────────────
        if not manifest.get("name"):
            report["issues"].append("缺少必填字段 `name`")
            manifest["name"] = dir_name
            report["fixes"].append(f"已将 name 设为目录名: \"{dir_name}\"")
            changed = True

        # ── 4. Required field: version ────────────────────────────────
        if not manifest.get("version"):
            report["issues"].append("缺少字段 `version`")
            manifest["version"] = "0.1.0"
            report["fixes"].append("已将 version 设为默认值: \"0.1.0\"")
            changed = True
        else:
            import re as _re
            if not _re.match(r"^\d+\.\d+\.\d+", str(manifest["version"])):
                report["issues"].append(f"version 格式不符合 semver: {manifest['version']}")
                manifest["version"] = "0.1.0"
                report["fixes"].append("已将 version 修正为: \"0.1.0\"")
                changed = True

        # ── 5. Required field: description ───────────────────────────
        if not manifest.get("description"):
            report["issues"].append("缺少字段 `description`")
            # Extract from first non-empty body line (strip markdown heading #)
            first_body = next(
                (l.lstrip("#").strip() for l in body.splitlines() if l.strip()),
                dir_name,
            )
            manifest["description"] = first_body[:120]
            report["fixes"].append(f"已从正文首行推断 description: \"{manifest['description'][:40]}...\"")
            changed = True

        # ── 6. Optional: tools list validation ───────────────────────
        tools = manifest.get("tools", [])
        if tools and isinstance(tools, list):
            bad_tools = []
            for i, t in enumerate(tools):
                if not isinstance(t, dict):
                    bad_tools.append(f"tools[{i}] 不是字典")
                    continue
                if not t.get("name"):
                    bad_tools.append(f"tools[{i}] 缺少 name 字段")
                if not t.get("description"):
                    bad_tools.append(f"tools[{i}] ({t.get('name','?')}) 缺少 description 字段")
            if bad_tools:
                report["issues"].extend(bad_tools)
                # Remove invalid tool entries
                manifest["tools"] = [
                    t for t in tools
                    if isinstance(t, dict) and t.get("name") and t.get("description")
                ]
                report["fixes"].append(f"已移除 {len(tools) - len(manifest['tools'])} 个不合规的 tools 条目")
                changed = True

        # ── 7. Rewrite file if anything changed ──────────────────────
        if changed:
            new_fm = yaml.dump(manifest, allow_unicode=True, sort_keys=False, default_flow_style=False)
            new_text = f"---\n{new_fm}---\n{body}"
            try:
                path.write_text(new_text, encoding="utf-8")
                report["fixed"] = True
                logger.info("skill_manifest_fixed", path=str(path), fixes=report["fixes"])
            except Exception as exc:
                report["errors"].append(f"写入修复后文件失败: {exc}")

        if not report["issues"] and not report["errors"]:
            report["issues"] = []  # clean

        return report



    @staticmethod
    def _parse_manifest(path: Path) -> Optional[SkillInfo]:
        """Parse a skill.md file with YAML front matter."""
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("skill_read_failed", path=str(path), error=str(exc))
            return None

        # Extract YAML front matter between --- delimiters
        if not text.startswith("---"):
            logger.warning("skill_no_frontmatter", path=str(path))
            return None

        parts = text.split("---", 2)
        if len(parts) < 3:
            logger.warning("skill_malformed_frontmatter", path=str(path))
            return None

        try:
            manifest = yaml.safe_load(parts[1])
        except yaml.YAMLError as exc:
            logger.warning("skill_yaml_error", path=str(path), error=str(exc))
            return None

        if not isinstance(manifest, dict) or "name" not in manifest:
            logger.warning("skill_missing_name", path=str(path))
            return None

        return SkillInfo(path=path.parent, manifest=manifest)

    # ------------------------------------------------------------------
    # Config validation
    # ------------------------------------------------------------------

    @staticmethod
    def _check_config(info: SkillInfo) -> bool:
        """Check that all required config keys are set in settings."""
        for key in info.requires_config:
            if not getattr(settings, key, ""):
                return False
        return True

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> None:
        """Load enable/disable state from JSON file."""
        with self._file_lock:
            if not self._STATE_FILE.exists():
                return
            try:
                data = json.loads(self._STATE_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    # Support both legacy format {name: bool} and new format {enabled:{}, runtime_info:{}}
                    if "enabled" in data and isinstance(data["enabled"], dict):
                        self._enabled = {k: bool(v) for k, v in data["enabled"].items()}
                    else:
                        # Legacy: top-level keys are skill names mapped to bools
                        self._enabled = {k: bool(v) for k, v in data.items() if k != "runtime_info"}
            except Exception as exc:
                logger.warning("skill_state_load_failed", error=str(exc))

    def _save_state(self) -> None:
        """Persist enable/disable state to JSON file (preserves runtime_info)."""
        with self._file_lock:
            state = self._load_full_state_locked()
            state["enabled"] = self._enabled
            try:
                self._STATE_FILE.write_text(
                    json.dumps(state, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception as exc:
                logger.warning("skill_state_save_failed", error=str(exc))

    def _load_full_state(self) -> Dict[str, Any]:
        """Load the full state dict (enabled + runtime_info). Thread-safe."""
        with self._file_lock:
            return self._load_full_state_locked()

    def _load_full_state_locked(self) -> Dict[str, Any]:
        """Load the full state dict. Caller must hold _file_lock."""
        if not self._STATE_FILE.exists():
            return {}
        try:
            data = json.loads(self._STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                # Migrate legacy format {name: bool} → {enabled: {name: bool}}
                if "enabled" not in data:
                    enabled = {k: bool(v) for k, v in data.items() if k != "runtime_info"}
                    return {"enabled": enabled, "runtime_info": data.get("runtime_info", {})}
                return data
        except Exception:
            pass
        return {}

    def _save_full_state(self, state: Dict[str, Any]) -> None:
        """Save the full state dict to disk."""
        with self._file_lock:
            try:
                self._STATE_FILE.write_text(
                    json.dumps(state, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception as exc:
                logger.warning("skill_state_save_failed", error=str(exc))


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_instance: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    """Return the global SkillManager singleton."""
    global _instance
    if _instance is None:
        _instance = SkillManager()
        _instance.discover()
    return _instance
