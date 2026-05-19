import asyncio
import json
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from pydantic import BaseModel

from dataclasses import asdict
from typing import List, Optional

from . import flows as flows_mod
from . import gstack_loader, hermes_cli, orchestrator, runs as runs_mod, scenarios as scenarios_mod
from . import skill_tabs, github_importer, llm_classifier
from .types import ChatRequest

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "hermes-bridge", "version": "1.0.0"}


@router.post("/chat")
async def chat(req: ChatRequest):
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, hermes_cli.execute_query, req.message
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """True SSE streaming: proxy to the agent service's streaming endpoint."""
    import httpx

    AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8001")

    async def event_generator():
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(600)) as client:
                async with client.stream(
                    "POST",
                    f"{AGENT_SERVICE_URL}/api/v1/agent/chat/stream",
                    json={
                        "message": req.message,
                        "session_id": req.session_id,
                        "user_id": req.user_id,
                        "conversation_id": req.conversation_id,
                        "skill_name": req.skill_name or "",
                        "model": req.model or "",
                        "provider": req.provider or "",
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line:
                            yield line + "\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Hub routes (filesystem-based, no CLI) ──
@router.get("/skills/hub")
async def search_hub(q: str = ""):
    """Search installed skills by keyword (filesystem scan)."""
    skills = hermes_cli.list_skills_from_fs()
    if q:
        q_lower = q.lower()
        skills = [s for s in skills if q_lower in s["name"].lower() or q_lower in s.get("description", "").lower()]
    return {"skills": skills}


class InstallRequest(BaseModel):
    identifier: str


@router.post("/skills/hub/install")
async def install_hub(req: InstallRequest):
    """Install from identifier is no longer supported (CLI removed). Use Tab import instead."""
    return {"success": False, "output": "Hub install via CLI removed. Use /tabs/{id}/import for GitHub imports.", "identifier": req.identifier}


# ── Skills (filesystem-based) ──
@router.get("/skills")
async def list_skills():
    skills = hermes_cli.list_skills_from_fs()
    return {"skills": skills}


@router.get("/skills/{name}")
async def get_skill(name: str):
    detail = hermes_cli.get_skill_detail_fs(name)
    if "error" in detail:
        raise HTTPException(status_code=404, detail=detail["error"])
    return detail


@router.post("/skills/{name}/execute")
async def execute_skill(name: str, req: ChatRequest):
    """Execute a skill using direct LLM (no CLI)."""
    try:
        loop = asyncio.get_event_loop()
        content, sid = await loop.run_in_executor(
            None, hermes_cli.execute_skill_direct,
            name, req.message, 600, req.session_id, req.model, req.project_dir,
        )
        return {"result": content, "session_id": sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Agents ──
@router.get("/agents")
async def list_agents():
    """List agent workflows (from gstack roles)."""
    roles = [asdict(r) for r in gstack_loader.list_roles()]
    return {"agents": roles}


@router.post("/agents/{name}/run")
async def run_agent(name: str, req: ChatRequest):
    """Run an agent (same as skill execute)."""
    try:
        loop = asyncio.get_event_loop()
        content, sid = await loop.run_in_executor(
            None, hermes_cli.execute_skill_direct,
            name, req.message, 600, req.session_id, req.model, req.project_dir,
        )
        return {"result": content, "session_id": sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace")
async def workspace():
    projects = hermes_cli.list_workspace_fs()
    return {"projects": projects}


# ── gstack expert roles ──────────────────────────────────────────────────────


class GstackLoadRequest(BaseModel):
    root: str | None = None
    install: bool = True


@router.post("/gstack/load")
async def gstack_load(req: GstackLoadRequest | None = None):
    """Scan the configured gstack checkout, install every skill into hermes,
    and refresh the role index. Idempotent — safe to call repeatedly."""
    payload = req or GstackLoadRequest()
    try:
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(
            None,
            gstack_loader.load_all,
            payload.root or gstack_loader.GSTACK_HOME,
            payload.install,
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles")
async def list_roles(category: str | None = None):
    """Expert roles loaded from gstack. Pass ?category=plan|implement|... to filter."""
    roles = [asdict(r) for r in gstack_loader.list_roles()]
    if category:
        roles = [r for r in roles if r["category"] == category]
    return {"roles": roles, "count": len(roles)}


@router.get("/roles/{role_id}")
async def get_role(role_id: str):
    role = gstack_loader.get_role(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail=f"role not found: {role_id}")
    return asdict(role)


# ── Tool scenarios ───────────────────────────────────────────────────────────


@router.get("/scenarios")
async def list_scenarios():
    return {"scenarios": scenarios_mod.list_scenarios()}


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    scenario = scenarios_mod.get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"scenario not found: {scenario_id}")
    return scenario


# ── Dialog flows (recipe CRUD) ──────────────────────────────────────────────


class FlowCreate(BaseModel):
    name: str
    flow_type: str  # 'sequential' | 'parallel'
    role_ids: List[str]
    description: str = ""
    scenario_id: str = ""
    prompt_template: str = ""
    model: str = ""
    owner_id: int = 0


class FlowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    flow_type: Optional[str] = None
    role_ids: Optional[List[str]] = None
    scenario_id: Optional[str] = None
    prompt_template: Optional[str] = None
    model: Optional[str] = None


@router.post("/flows")
async def create_flow(req: FlowCreate):
    try:
        flow = flows_mod.create(
            name=req.name,
            flow_type=req.flow_type,
            role_ids=req.role_ids,
            description=req.description,
            scenario_id=req.scenario_id,
            prompt_template=req.prompt_template,
            model=req.model,
            owner_id=req.owner_id,
        )
        return flow.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/flows")
async def list_flows(owner_id: Optional[int] = None):
    return {"flows": [f.to_dict() for f in flows_mod.list_flows(owner_id)]}


@router.get("/flows/{flow_id}")
async def get_flow(flow_id: int):
    try:
        return flows_mod.get(flow_id).to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/flows/{flow_id}")
async def update_flow(flow_id: int, req: FlowUpdate):
    try:
        flow = flows_mod.update(
            flow_id,
            name=req.name,
            description=req.description,
            flow_type=req.flow_type,
            role_ids=req.role_ids,
            scenario_id=req.scenario_id,
            prompt_template=req.prompt_template,
            model=req.model,
        )
        return flow.to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/flows/{flow_id}")
async def delete_flow(flow_id: int):
    try:
        flows_mod.get(flow_id)  # 404 if missing
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    flows_mod.delete(flow_id)
    return {"deleted": flow_id}


@router.get("/flows/{flow_id}/runs")
async def list_flow_runs(flow_id: int, limit: int = 50):
    try:
        flows_mod.get(flow_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"runs": [r.to_dict() for r in runs_mod.list_for_flow(flow_id, limit)]}


@router.get("/runs/{run_id}")
async def get_run(run_id: int):
    try:
        return runs_mod.get(run_id).to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/runs/{run_id}/artifacts.zip")
async def download_run_artifacts(run_id: int):
    try:
        run = runs_mod.get(run_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if run.status != "succeeded":
        raise HTTPException(status_code=409, detail="run artifacts are only available for succeeded runs")
    try:
        zip_bytes, filename, _, _ = runs_mod.build_artifact_zip(run)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except OverflowError as e:
        raise HTTPException(status_code=413, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/runs/{run_id}")
async def delete_run(run_id: int):
    try:
        run = runs_mod.get(run_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if run.status in {"pending", "running"}:
        raise HTTPException(status_code=409, detail="running tasks cannot be deleted")
    try:
        removed, workdir = runs_mod.remove_project_dir(run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"failed to remove workdir: {e}")
    runs_mod.delete(run_id)
    return {"deleted": run_id, "workdir_removed": removed, "workdir": workdir}


# Phase 3: real SSE-streamed orchestrator run.
@router.post("/flows/{flow_id}/run")
async def run_flow(flow_id: int, req: ChatRequest):
    try:
        flows_mod.get(flow_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    async def event_generator():
        try:
            async for event in orchestrator.run_flow(flow_id, req.message, project_dir=req.project_dir):
                yield event.to_sse()
        except Exception as exc:                             # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
# Skill Tabs API
# ══════════════════════════════════════════════════════════════════════════════


class TabCreate(BaseModel):
    id: str
    name: str
    description: str = ""
    source_type: str = "github"
    source_url: str = ""
    branch: str = "main"
    sub_path: str = ""
    icon: str = ""


class TabUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    tab_order: Optional[int] = None


class TabImportRequest(BaseModel):
    url: str
    branch: str = "main"
    sub_path: str = ""


@router.get("/tabs")
async def list_tabs():
    """List all skill tabs."""
    tabs = skill_tabs.list_tabs()
    return {"tabs": [t.to_dict() for t in tabs]}


@router.post("/tabs")
async def create_tab(req: TabCreate):
    """Create a new skill tab."""
    try:
        tab = skill_tabs.create_tab(
            id=req.id,
            name=req.name,
            description=req.description,
            source_type=req.source_type,
            source_url=req.source_url,
            branch=req.branch,
            sub_path=req.sub_path,
            icon=req.icon,
        )
        return tab.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tabs/{tab_id}")
async def get_tab(tab_id: str):
    try:
        tab = skill_tabs.get_tab(tab_id)
        return tab.to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/tabs/{tab_id}")
async def update_tab(tab_id: str, req: TabUpdate):
    try:
        tab = skill_tabs.update_tab(tab_id, **req.model_dump(exclude_none=True))
        return tab.to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/tabs/{tab_id}")
async def delete_tab(tab_id: str):
    try:
        skill_tabs.get_tab(tab_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    skill_tabs.delete_tab(tab_id)
    github_importer.remove_skill_pack(tab_id)
    return {"deleted": tab_id}


@router.post("/tabs/{tab_id}/import")
async def import_tab(tab_id: str, req: TabImportRequest):
    """Import skills from a GitHub repository into a tab.

    Pipeline: clone → scan → register roles (use repo structure if nested, LLM classify if flat).
    """
    try:
        skill_tabs.get_tab(tab_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    loop = asyncio.get_event_loop()

    # Step 1: Clone and scan
    import_result = await loop.run_in_executor(
        None, github_importer.import_from_github,
        req.url, tab_id, req.branch, req.sub_path,
    )

    if not import_result.success:
        raise HTTPException(status_code=400, detail=import_result.error)

    # Step 2: Determine if repo uses nested structure (role/skills/skill_name)
    has_role_groups = any(s.role_group for s in import_result.skills)

    skill_tabs.delete_roles_for_tab(tab_id)
    registered_roles = []

    if has_role_groups:
        # Use repo's own role→skill structure directly
        from itertools import groupby
        sorted_skills = sorted(import_result.skills, key=lambda s: s.role_group)
        for role_name, group_skills in groupby(sorted_skills, key=lambda s: s.role_group):
            skills_list = list(group_skills)
            capabilities = [s.name for s in skills_list]
            # Register each skill as a role entry (grouped by role_group)
            for skill in skills_list:
                role = skill_tabs.add_role(
                    id=f"{tab_id}:{skill.skill_id}",
                    tab_id=tab_id,
                    role_id=skill.skill_id,
                    display_name=skill.name,
                    category=role_name,
                    classification="implementation",
                    description=skill.description or f"{role_name} - {skill.name}",
                    capabilities=capabilities,
                    recommended_tools=[],
                    skill_md_path=skill.skill_md_path,
                    system_prompt=skill.system_prompt[:500],
                )
                registered_roles.append(role.to_dict())
    else:
        # Flat repo: use LLM classification
        skills_for_classify = [
            {
                "skill_id": s.skill_id,
                "name": s.name,
                "description": s.description,
                "content": s.system_prompt[:2000],
            }
            for s in import_result.skills
        ]

        classifications = await loop.run_in_executor(
            None, llm_classifier.classify_batch, skills_for_classify,
        )

        for skill, cls in zip(import_result.skills, classifications):
            role = skill_tabs.add_role(
                id=f"{tab_id}:{skill.skill_id}",
                tab_id=tab_id,
                role_id=skill.skill_id,
                display_name=cls.display_name,
                category=cls.category,
                classification=cls.classification,
                description=cls.description,
                capabilities=cls.capabilities,
                recommended_tools=cls.recommended_tools,
                skill_md_path=skill.skill_md_path,
                system_prompt=skill.system_prompt[:500],
            )
            registered_roles.append(role.to_dict())

    # Step 3: Generate scenarios if enough roles (only for flat repos needing LLM)
    scenarios = []
    if not has_role_groups and len(import_result.skills) >= 3:
        roles_for_scenario = [
            {
                "role_id": r.get("role_id", ""),
                "display_name": r.get("display_name", ""),
                "classification": r.get("classification", ""),
                "description": r.get("description", ""),
            }
            for r in registered_roles
        ]
        tab = skill_tabs.get_tab(tab_id)
        generated = await loop.run_in_executor(
            None, llm_classifier.generate_scenarios, roles_for_scenario, tab.name,
        )
        for gs in generated:
            sc = skill_tabs.add_scenario(
                id=f"{tab_id}:{gs.id}",
                tab_id=tab_id,
                name=gs.name,
                description=gs.description,
                tools=gs.tools,
                recommended_roles=gs.recommended_roles,
            )
            scenarios.append(sc.to_dict())

    # Update tab metadata
    skill_tabs.update_tab(tab_id, source_url=req.url, branch=req.branch, sub_path=req.sub_path)

    return {
        "success": True,
        "scanned": import_result.scanned,
        "imported": len(registered_roles),
        "scenarios_generated": len(scenarios),
        "roles": registered_roles,
        "scenarios": scenarios,
    }


@router.post("/tabs/{tab_id}/refresh")
async def refresh_tab(tab_id: str):
    """Re-pull from GitHub and re-classify."""
    try:
        tab = skill_tabs.get_tab(tab_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if tab.source_type != "github" or not tab.source_url:
        raise HTTPException(status_code=400, detail="Tab has no GitHub source to refresh")

    req = TabImportRequest(url=tab.source_url, branch=tab.branch, sub_path=tab.sub_path)
    return await import_tab(tab_id, req)


@router.get("/tabs/{tab_id}/roles")
async def list_tab_roles(tab_id: str):
    """List roles for a specific tab."""
    try:
        skill_tabs.get_tab(tab_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    roles = skill_tabs.list_roles_for_tab(tab_id)
    return {"roles": [r.to_dict() for r in roles], "count": len(roles)}


@router.get("/tabs/{tab_id}/scenarios")
async def list_tab_scenarios(tab_id: str):
    """List scenarios for a specific tab."""
    try:
        skill_tabs.get_tab(tab_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    scenarios = skill_tabs.list_scenarios_for_tab(tab_id)
    return {"scenarios": [s.to_dict() for s in scenarios]}
