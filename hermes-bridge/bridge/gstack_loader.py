"""Scan a local gstack checkout, parse SKILL.md frontmatter, and build the
expert_roles index that the platform exposes via /api/v2/roles.

Skills are loaded by reading SKILL.md files directly — no hermes CLI binary
required. The role index is cached to JSON for fast startup.

The path is overridable via ``GSTACK_HOME`` so a developer can point at a
local checkout without editing code.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

GSTACK_HOME = os.getenv("GSTACK_HOME", "/root/projects/gstack")
HERMES_SKILLS_DIR = Path(os.getenv("HERMES_SKILLS_DIR", "/home/admin/.hermes/skills"))
ROLES_CACHE_PATH = Path(
    os.getenv("EXPERT_ROLES_CACHE", "/root/.agent-platform/expert_roles.json")
)

# Mirror of gstack's AGENTS.md grouping. Anything not listed falls into "other".
CATEGORY_MAP: Dict[str, str] = {
    # plan-mode reviews
    "office-hours": "plan",
    "plan-ceo-review": "plan",
    "plan-eng-review": "plan",
    "plan-design-review": "plan",
    "plan-devex-review": "plan",
    "plan-tune": "plan",
    "autoplan": "plan",
    "design-consultation": "plan",
    # implementation + review
    "review": "implement",
    "codex": "implement",
    "investigate": "implement",
    "design-review": "implement",
    "design-shotgun": "implement",
    "design-html": "implement",
    "devex-review": "implement",
    "qa": "implement",
    "qa-only": "implement",
    "scrape": "implement",
    "skillify": "implement",
    # release + deploy
    "ship": "release",
    "land-and-deploy": "release",
    "canary": "release",
    "landing-report": "release",
    "document-release": "release",
    "setup-deploy": "release",
    "gstack-upgrade": "release",
    # operational
    "context-save": "ops",
    "context-restore": "ops",
    "learn": "ops",
    "retro": "ops",
    "health": "ops",
    "benchmark": "ops",
    "benchmark-models": "ops",
    "cso": "ops",
    "setup-gbrain": "ops",
    "sync-gbrain": "ops",
    # browser / agent
    "browse": "browser",
    "open-gstack-browser": "browser",
    "setup-browser-cookies": "browser",
    "pair-agent": "browser",
    # safety
    "careful": "safety",
    "freeze": "safety",
    "guard": "safety",
    "unfreeze": "safety",
    "make-pdf": "safety",
}


# ── Models ───────────────────────────────────────────────────────────────────

@dataclass
class ExpertRole:
    id: str                       # slug, equals skill name
    name: str
    category: str
    description: str
    version: str
    source: str                   # absolute path to the gstack skill dir
    skill_md_path: str
    allowed_tools: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    hermes_installed: bool = False
    install_error: Optional[str] = None
    loaded_at: float = 0.0


# ── Frontmatter parsing ──────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(skill_md: Path) -> Dict:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {"name": skill_md.parent.name}
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        logger.warning("frontmatter parse failed for %s: %s", skill_md, exc)
        return {"name": skill_md.parent.name}
    if isinstance(data.get("description"), str):
        data["description"] = data["description"].strip()
    return data


# ── Discovery + install ──────────────────────────────────────────────────────


def discover_skills(root: str = GSTACK_HOME) -> List[Path]:
    """Return every gstack subdirectory that contains a SKILL.md."""
    base = Path(root)
    if not base.exists():
        logger.warning("gstack root not found: %s", base)
        return []
    found = []
    for skill_md in sorted(base.glob("*/SKILL.md")):
        if skill_md.name == "SKILL.md.tmpl":
            continue
        found.append(skill_md.parent)
    return found


def install_skill(skill_dir: Path) -> Optional[str]:
    """Install a skill by copying it into the skills directory.
    Returns None on success, error string on failure."""
    target = HERMES_SKILLS_DIR / skill_dir.name
    try:
        HERMES_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_dir, target)
        return None
    except OSError as exc:
        return f"copy failed: {exc}"


def _build_role(skill_dir: Path) -> ExpertRole:
    skill_md = skill_dir / "SKILL.md"
    meta = _parse_frontmatter(skill_md)
    name = str(meta.get("name") or skill_dir.name)
    return ExpertRole(
        id=name,
        name=name,
        category=CATEGORY_MAP.get(name, "other"),
        description=str(meta.get("description") or "").strip(),
        version=str(meta.get("version") or "0.0.0"),
        source=str(skill_dir),
        skill_md_path=str(skill_md),
        allowed_tools=list(meta.get("allowed-tools") or []),
        triggers=list(meta.get("triggers") or []),
    )


# ── Cache ────────────────────────────────────────────────────────────────────

def _save_cache(roles: List[ExpertRole]) -> None:
    try:
        ROLES_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        ROLES_CACHE_PATH.write_text(
            json.dumps([asdict(r) for r in roles], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("failed to persist roles cache: %s", exc)


def load_cache() -> List[ExpertRole]:
    if not ROLES_CACHE_PATH.exists():
        return []
    try:
        raw = json.loads(ROLES_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("roles cache unreadable, ignoring: %s", exc)
        return []
    return [ExpertRole(**item) for item in raw]


# ── Public API ───────────────────────────────────────────────────────────────

def load_all(root: str = GSTACK_HOME, install: bool = True) -> Dict:
    """Scan gstack, install each skill (file copy), persist the role index.

    Returns a summary dict suitable for direct JSON response.
    """
    started = time.time()
    skill_dirs = discover_skills(root)
    roles: List[ExpertRole] = []
    install_failures: List[Dict[str, str]] = []

    for skill_dir in skill_dirs:
        role = _build_role(skill_dir)
        if install:
            err = install_skill(skill_dir)
            if err:
                role.install_error = err
                install_failures.append({"name": role.name, "error": err})
            else:
                role.hermes_installed = True
        else:
            role.hermes_installed = (HERMES_SKILLS_DIR / skill_dir.name).exists()
        role.loaded_at = time.time()
        roles.append(role)

    _save_cache(roles)

    return {
        "root": str(root),
        "scanned": len(skill_dirs),
        "loaded": len(roles),
        "installed": sum(1 for r in roles if r.hermes_installed),
        "install_failures": install_failures,
        "duration_ms": int((time.time() - started) * 1000),
    }


def list_roles() -> List[ExpertRole]:
    """Return cached roles, loading from disk on first call."""
    return load_cache()


def get_role(role_id: str) -> Optional[ExpertRole]:
    for role in list_roles():
        if role.id == role_id:
            return role
    return None
