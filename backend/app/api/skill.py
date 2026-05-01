"""REST endpoints for skill management — list, get, add, remove, enable, disable."""

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.skill import get_skill_manager

router = APIRouter(tags=["skill"])


class AddSkillRequest(BaseModel):
    path: str


@router.get("/")
async def list_skills():
    """List all discovered skills with their status."""
    mgr = get_skill_manager()
    return {"skills": mgr.list_skills()}


@router.get("/{name}")
async def get_skill(name: str):
    """Get details of a single skill."""
    mgr = get_skill_manager()
    info = mgr.get_skill(name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return info


@router.post("/")
async def add_skill(body: AddSkillRequest):
    """Add a skill by providing its directory path (containing skill.md).

    The skill.md is validated and auto-fixed before registration.
    Returns the skill metadata plus a `validation` report with any
    issues found and fixes applied.
    """
    mgr = get_skill_manager()
    result = mgr.add_skill(body.path)
    if not result:
        # Try to give a more specific error by running validation standalone
        from pathlib import Path
        target = Path(body.path)
        if not target.is_absolute():
            from app.skill.manager import _PROJECT_ROOT
            target = _PROJECT_ROOT / target
        target = target.resolve()
        for fname in ("skill.md", "SKILL.md"):
            mf = target / fname
            if mf.exists():
                report = mgr.validate_and_fix_manifest(mf)
                if report["errors"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"skill.md 校验失败: {'; '.join(report['errors'])}",
                    )
        raise HTTPException(
            status_code=400,
            detail=f"无法从路径 '{body.path}' 添加技能，请确认目录存在且包含有效的 skill.md 文件",
        )
    return result


@router.delete("/{name}")
async def remove_skill(name: str):
    """Remove a skill by name."""
    mgr = get_skill_manager()
    if not mgr.remove_skill(name):
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return {"name": name, "removed": True}


@router.post("/{name}/enable")
async def enable_skill(name: str):
    """Enable a skill so its tools are registered with the agent."""
    mgr = get_skill_manager()
    if not mgr.enable_skill(name):
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return {"name": name, "enabled": True}


@router.post("/{name}/disable")
async def disable_skill(name: str):
    """Disable a skill so its tools are removed from the agent."""
    mgr = get_skill_manager()
    if not mgr.disable_skill(name):
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return {"name": name, "enabled": False}
