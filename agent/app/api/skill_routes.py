"""Skill REST API routes: list, enable, disable, import, get, remove, upload."""
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.skill.manager import get_skill_manager
from app.tools.registry import get_tool_registry
from app.tools.skill_tools import RunSkillScriptTool, ReadSkillReferenceTool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


class SkillToolResponse(BaseModel):
    name: str
    description: str = ""


class SkillResponse(BaseModel):
    name: str
    version: str = ""
    description: str = ""
    author: str = ""
    license: str = ""
    keywords: list[str] = []
    dependencies: list[str] = []
    tools: list[SkillToolResponse] = []
    requires_config: list[str] = []
    optional_config: list[str] = []
    enabled: bool = False
    config_ok: bool = True
    path: str = ""

    model_config = {"extra": "ignore"}

    @classmethod
    def from_skill(cls, s) -> "SkillResponse":
        """Convert a SkillInfo to SkillResponse with version coercion."""
        version = s.version
        if version is not None:
            version = str(version)
        return cls(
            name=s.name,
            version=version or "",
            description=s.description or "",
            author=s.author or "",
            tools=[SkillToolResponse(name=t.name, description=t.description) for t in (s.tools or [])],
            enabled=s.enabled,
            path=s.path or "",
        )


class SkillListResponse(BaseModel):
    skills: list[SkillResponse]


class SkillActionRequest(BaseModel):
    name: str


class SkillAddRequest(BaseModel):
    path: str = ""
    name: str = ""
    description: str = ""
    version: str = ""


class SkillUpdateRequest(BaseModel):
    description: str = ""
    version: str = ""
    category: str = ""


class SkillRemoveResponse(BaseModel):
    name: str
    removed: bool


class SkillEnableResponse(BaseModel):
    name: str
    enabled: bool


class SkillGitHubImportRequest(BaseModel):
    url: str
    branch: str = "main"
    sub_path: str = ""
    enable: bool = True


class SkillGitHubImportResponse(BaseModel):
    success: bool
    scanned: int
    imported: int
    skills: list[SkillResponse]
    errors: list[str] = []


def _to_response(skill) -> SkillResponse:
    return SkillResponse.from_skill(skill)


@router.get("")
async def list_skills():
    """List all discovered skills."""
    manager = get_skill_manager()
    skills = manager.list_skills()
    return SkillListResponse(skills=[_to_response(s) for s in skills])


@router.get("/{name}")
async def get_skill(name: str):
    """Get a single skill by name."""
    manager = get_skill_manager()
    skill = manager.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
    return _to_response(skill)


@router.post("")
async def add_skill(request: SkillAddRequest):
    """Import/add a skill. Accepts either {path} for directory import or {name,...} for creation."""
    manager = get_skill_manager()
    manager.discover()  # Sync with filesystem before checking existence

    # If path is provided, import from external directory
    if request.path:
        skill = manager.import_skill(request.path)
        if not skill:
            raise HTTPException(status_code=400, detail="Failed to import skill. Check path and SKILL.md.")
        return _to_response(skill)

    # Otherwise, create a new skill from metadata
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Skill name is required")
    if manager.get_skill(name):
        raise HTTPException(status_code=409, detail=f"Skill already exists: {name}")

    from app.core.config import settings
    skill_dir = Path(settings.SKILLS_DIR) / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    manifest = f"""---
name: {name}
version: "{request.version or '1.0.0'}"
description: '{request.description or ''}'
author: ''
tools: []
---
# {name}
{request.description or ''}
"""
    manifest_path = skill_dir / "SKILL.md"
    manifest_path.write_text(manifest.lstrip(), encoding="utf-8")

    # Rediscover to load the new skill
    manager.discover()
    skill = manager.get_skill(name)
    if not skill:
        raise HTTPException(status_code=500, detail="Failed to create skill")

    return _to_response(skill)


@router.post("/import/github")
async def import_github_skills(request: SkillGitHubImportRequest):
    manager = get_skill_manager()
    result = manager.import_from_github(request.url, request.branch, request.sub_path)
    imported = []

    for imported_skill in result.imported:
        skill = manager.get_skill(imported_skill.name)
        if not skill:
            result.errors.append(f"Skill not found after import: {imported_skill.name}")
            continue
        if request.enable:
            manager.enable(skill.name)
            skill = manager.get_skill(skill.name) or skill
            _register_skill_tools(skill)
        imported.append(_to_response(skill))

    if not imported:
        raise HTTPException(status_code=400, detail="; ".join(result.errors) or "No SKILL.md files imported")

    return SkillGitHubImportResponse(
        success=result.success,
        scanned=result.scanned,
        imported=len(imported),
        skills=imported,
        errors=result.errors,
    )


@router.post("/upload")
async def upload_skill_zip(file: UploadFile = File(...)):
    """Upload a zip file containing a skill, extract it, and register."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")

    manager = get_skill_manager()
    manager.discover()

    from app.core.config import settings
    skills_dir = Path(settings.SKILLS_DIR)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / file.filename
        content = await file.read()
        tmp_path.write_bytes(content)

        try:
            with zipfile.ZipFile(tmp_path, "r") as zf:
                zf.extractall(tmp_dir)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid zip file")

        extracted = Path(tmp_dir)
        skill_root = None
        if (extracted / "SKILL.md").exists():
            skill_root = extracted
        else:
            subdirs = [d for d in extracted.iterdir() if d.is_dir() and not d.name.startswith(".")]
            for d in subdirs:
                if (d / "SKILL.md").exists():
                    skill_root = d
                    break

        if not skill_root:
            raise HTTPException(status_code=400, detail="Zip must contain a SKILL.md at root or in a single subdirectory")

        skill_info = manager._parse_manifest(skill_root / "SKILL.md")
        skill_name = skill_info.name

        if manager.get_skill(skill_name):
            dest = Path(manager.get_skill(skill_name).path)
            shutil.rmtree(dest)
        else:
            dest = skills_dir / skill_name

        dest.mkdir(parents=True, exist_ok=True)

        for item in skill_root.rglob("*"):
            if item.is_file():
                rel = item.relative_to(skill_root)
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)

    manager.discover()
    skill = manager.get_skill(skill_name)
    if not skill:
        raise HTTPException(status_code=500, detail="Failed to register skill from zip")

    return _to_response(skill)


@router.put("/{name}")
async def update_skill(name: str, request: SkillUpdateRequest):
    """Update a skill's metadata (description, version, category)."""
    manager = get_skill_manager()
    manager.discover()
    skill = manager.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")

    # Read existing SKILL.md, update frontmatter, write back
    skill_path = Path(skill.path) / "SKILL.md"
    if not skill_path.exists():
        raise HTTPException(status_code=400, detail=f"SKILL.md not found for skill: {name}")

    content = skill_path.read_text(encoding="utf-8")
    front_matter, body = manager._split_front_matter(content)

    # Parse and update YAML frontmatter, preserving structure
    lines = front_matter.splitlines()
    updated = []
    changed_keys = {}
    import yaml
    try:
        data = yaml.safe_load(front_matter) or {}
    except Exception:
        data = {}
    if request.description:
        data["description"] = request.description
    if request.version:
        data["version"] = request.version
    if request.category:
        data["category"] = request.category

    # Reconstruct frontmatter
    out = "---\n"
    for k, v in data.items():
        if isinstance(v, bool):
            out += f"{k}: {'true' if v else 'false'}\n"
        elif isinstance(v, str):
            out += f"{k}: \"{v}\"\n"
        else:
            out += f"{k}: {v}\n"
    out += "---"
    if body:
        out += "\n" + body

    skill_path.write_text(out, encoding="utf-8")

    # Rediscover
    manager.discover()
    updated_skill = manager.get_skill(name)
    if not updated_skill:
        raise HTTPException(status_code=500, detail="Failed to update skill")
    return _to_response(updated_skill)


@router.delete("/{name}")
async def remove_skill(name: str):
    """Remove/disable a skill."""
    manager = get_skill_manager()
    manager.discover()
    skill = manager.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
    if skill.enabled:
        manager.disable(name)
    # Unregister skill tools
    registry = get_tool_registry()
    registry.unregister(f"skill_{skill.name}_run")
    registry.unregister(f"skill_{skill.name}_ref")
    # Delete skill files from disk
    skill_dir = Path(skill.path)
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    # Remove from memory
    manager._skills.pop(name, None)
    return SkillRemoveResponse(name=name, removed=True)


@router.post("/{name}/enable")
async def enable_skill(name: str):
    """Enable a skill and register its tools."""
    manager = get_skill_manager()
    if not manager.enable(name):
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")

    # Register skill tools into the Python tool registry
    skill = manager.get_skill(name)
    if skill:
        _register_skill_tools(skill)

    return SkillEnableResponse(name=name, enabled=True)


@router.post("/{name}/disable")
async def disable_skill(name: str):
    """Disable a skill and unregister its tools."""
    manager = get_skill_manager()
    if not manager.disable(name):
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")

    # Unregister skill tools
    skill = manager.get_skill(name)
    if skill:
        registry = get_tool_registry()
        registry.unregister(f"skill_{skill.name}_run")
        registry.unregister(f"skill_{skill.name}_ref")

    return SkillEnableResponse(name=name, enabled=False)


def _register_skill_tools(skill) -> None:
    """Register a skill's tools into the Python tool registry."""
    from pathlib import Path

    registry = get_tool_registry()
    skill_path = Path(skill.path)

    # Register script runner if script exists
    script_file = skill_path / "main.py"
    if script_file.exists():
        runner = RunSkillScriptTool(
            skill_name=skill.name,
            script_path=str(script_file),
            description=skill.description,
        )
        registry.register(runner)

    # Register reference reader if documentation exists
    if skill.documentation:
        reader = ReadSkillReferenceTool(
            skill_name=skill.name,
            doc_content=skill.documentation,
        )
        registry.register(reader)

    logger.info("registered tools for skill: %s", skill.name)


def register_enabled_skills() -> None:
    """Register tools for all enabled skills (called at startup)."""
    manager = get_skill_manager()
    for skill in manager.list_enabled():
        _register_skill_tools(skill)
    logger.info("registered tools for %d enabled skills", len(manager.list_enabled()))


# Admin: reload skills from filesystem
@router.post("/admin/reload")
async def reload_skills():
    """Re-scan the skills directory and rediscover all skills. Used after SkillHub install."""
    manager = get_skill_manager()
    manager.discover()
    # Re-register tools for enabled skills
    for skill in manager.list_enabled():
        _register_skill_tools(skill)
    return {"status": "ok", "skills_count": len(manager.list_skills())}
