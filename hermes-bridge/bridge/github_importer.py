"""GitHub repository importer for skill packs.

Clones a GitHub repository, scans for SKILL.md files, and parses them
into structured role definitions ready for registration in a Skill Tab.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from . import gstack_loader

logger = logging.getLogger(__name__)

SKILL_PACKS_DIR = Path(os.getenv("SKILL_PACKS_DIR", "/root/.agent-platform/skill-packs"))

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class ParsedSkill:
    """A skill parsed from a SKILL.md file."""
    skill_id: str
    name: str
    description: str = ""
    version: str = "0.0.0"
    allowed_tools: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    system_prompt: str = ""
    skill_md_path: str = ""
    source_dir: str = ""
    role_group: str = ""  # parent role name for nested structures (e.g. "earnings-reviewer")


@dataclass
class ImportResult:
    """Result of a GitHub import operation."""
    success: bool
    tab_id: str
    repo_url: str
    clone_path: str = ""
    skills: List[ParsedSkill] = field(default_factory=list)
    error: str = ""
    scanned: int = 0
    parsed: int = 0


def parse_github_url(url: str) -> Tuple[str, str, str, str]:
    """Parse a GitHub URL into (owner, repo, branch, sub_path).

    Supports:
      - https://github.com/owner/repo
      - https://github.com/owner/repo/tree/branch
      - https://github.com/owner/repo/tree/branch/path/to/dir
    """
    url = url.strip().rstrip("/")
    # Remove .git suffix
    if url.endswith(".git"):
        url = url[:-4]

    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+)(?:/(.+))?)?",
        url,
    )
    if not m:
        raise ValueError(f"Invalid GitHub URL: {url}")

    owner = m.group(1)
    repo = m.group(2)
    branch = m.group(3) or "main"
    sub_path = m.group(4) or ""
    return owner, repo, branch, sub_path


def clone_repo(
    url: str,
    tab_id: str,
    branch: str = "main",
    timeout: int = 120,
) -> str:
    """Clone a GitHub repository. Returns the local path.

    Uses --depth 1 for efficiency. Stores under
    SKILL_PACKS_DIR/{tab_id}/{repo_name}/
    """
    owner, repo, _, _ = parse_github_url(url)

    target_dir = SKILL_PACKS_DIR / tab_id / repo

    # Clean existing clone
    if target_dir.exists():
        shutil.rmtree(target_dir)

    target_dir.parent.mkdir(parents=True, exist_ok=True)

    clone_url = f"https://github.com/{owner}/{repo}.git"

    cmd = [
        "git", "clone",
        "--depth", "1",
        "--branch", branch,
        clone_url,
        str(target_dir),
    ]

    logger.info("Cloning %s (branch=%s) to %s", clone_url, branch, target_dir)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            # Try without --branch (for repos where main != branch name)
            cmd_retry = [
                "git", "clone", "--depth", "1",
                clone_url, str(target_dir),
            ]
            if target_dir.exists():
                shutil.rmtree(target_dir)
            result = subprocess.run(
                cmd_retry, capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode != 0:
                raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"git clone timed out after {timeout}s")

    return str(target_dir)


def scan_skills(root_path: str, sub_path: str = "") -> List[Tuple[Path, str]]:
    """Scan a directory for SKILL.md files.

    Returns list of (skill_directory, role_group) tuples.
    Detects two structures:
      - Flat: root/{skill}/SKILL.md → role_group=""
      - Nested: root/{role}/skills/{skill}/SKILL.md → role_group="{role}"
    """
    base = Path(root_path)
    if sub_path:
        base = base / sub_path

    if not base.exists():
        logger.warning("Scan path does not exist: %s", base)
        return []

    found = []
    for skill_md in sorted(base.rglob("SKILL.md")):
        # Skip .git, .claude-plugin, node_modules etc. (only check relative path)
        rel = skill_md.relative_to(base)
        rel_parts = rel.parts
        if any(p.startswith(".") or p == "node_modules" for p in rel_parts):
            continue

        # Detect nested pattern: .../role_name/skills/skill_name/SKILL.md
        role_group = ""
        if len(rel_parts) >= 4 and rel_parts[-3] == "skills":
            role_group = rel_parts[-4]  # parent role directory

        found.append((skill_md.parent, role_group))

    return found


def parse_skill_md(skill_dir: Path, role_group: str = "") -> ParsedSkill:
    """Parse a SKILL.md file into a ParsedSkill object."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"No SKILL.md in {skill_dir}")

    content = skill_md.read_text(encoding="utf-8", errors="replace")

    # Parse frontmatter
    meta = {}
    body = content
    match = _FRONTMATTER_RE.match(content)
    if match:
        try:
            meta = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            pass
        body = content[match.end():]

    # Clean body for use as system prompt
    body = re.sub(r"## Preamble.*?```bash\n.*?```\n?", "", body, flags=re.DOTALL)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    body = body.strip()

    raw_name = str(meta.get("name") or skill_dir.name)
    # Namespace skill_id with role_group to avoid collisions
    skill_id = f"{role_group}/{raw_name}" if role_group else raw_name

    return ParsedSkill(
        skill_id=skill_id,
        name=raw_name,
        description=str(meta.get("description") or "").strip(),
        version=str(meta.get("version") or "0.0.0"),
        allowed_tools=list(meta.get("allowed-tools") or meta.get("allowed_tools") or []),
        triggers=list(meta.get("triggers") or []),
        system_prompt=body,
        skill_md_path=str(skill_md),
        source_dir=str(skill_dir),
        role_group=role_group,
    )


def import_from_github(
    url: str,
    tab_id: str,
    branch: str = "main",
    sub_path: str = "",
) -> ImportResult:
    """Full import pipeline: clone -> scan -> parse.

    Returns ImportResult with all parsed skills ready for LLM classification
    and registration.
    """
    result = ImportResult(
        success=False,
        tab_id=tab_id,
        repo_url=url,
    )

    try:
        # Clone
        clone_path = clone_repo(url, tab_id, branch=branch)
        result.clone_path = clone_path

        # Scan (returns list of (skill_dir, role_group) tuples)
        scan_results = scan_skills(clone_path, sub_path)
        result.scanned = len(scan_results)

        if not scan_results:
            result.error = "No SKILL.md files found in repository"
            return result

        # Parse each and install to unified skills directory
        parsed_skills = []
        for skill_dir, role_group in scan_results:
            try:
                skill = parse_skill_md(skill_dir, role_group=role_group)
                # Install using namespaced directory name to avoid collisions
                install_name = f"{role_group}--{skill_dir.name}" if role_group else skill_dir.name
                target = gstack_loader.HERMES_SKILLS_DIR / install_name
                gstack_loader.HERMES_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(skill_dir, target)
                skill.skill_md_path = str(target / "SKILL.md")
                parsed_skills.append(skill)
            except Exception as e:
                logger.warning("Failed to parse %s: %s", skill_dir, e)

        result.skills = parsed_skills
        result.parsed = len(parsed_skills)
        result.success = True

    except Exception as e:
        result.error = str(e)
        logger.error("GitHub import failed for %s: %s", url, e)

    return result


def remove_skill_pack(tab_id: str) -> bool:
    """Remove the cloned repository for a tab and its installed skills."""
    target = SKILL_PACKS_DIR / tab_id
    if target.exists():
        # Also remove installed copies from unified skills dir
        for skill_dir, role_group in scan_skills(str(target)):
            install_name = f"{role_group}--{skill_dir.name}" if role_group else skill_dir.name
            installed = gstack_loader.HERMES_SKILLS_DIR / install_name
            if installed.exists():
                shutil.rmtree(installed)
        shutil.rmtree(target)
        return True
    return False


def refresh_skill_pack(tab_id: str, url: str, branch: str = "main", sub_path: str = "") -> ImportResult:
    """Re-clone and re-parse a skill pack (for updates)."""
    remove_skill_pack(tab_id)
    return import_from_github(url, tab_id, branch=branch, sub_path=sub_path)
