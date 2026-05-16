"""Skill Tab management — industry/domain groupings for expert roles.

Each tab represents a domain (e.g., "software-engineering", "finance") and
contains a set of expert roles imported from either gstack (builtin) or
GitHub repositories.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from . import db

logger = logging.getLogger(__name__)


# ── DB Migrations ───────────────────────────────────────────────────────────

TAB_MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS skill_tabs (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        source_type TEXT NOT NULL DEFAULT 'builtin',
        source_url TEXT DEFAULT '',
        branch TEXT DEFAULT 'main',
        sub_path TEXT DEFAULT '',
        imported_at TEXT,
        updated_at TEXT,
        role_count INTEGER DEFAULT 0,
        icon TEXT DEFAULT '',
        tab_order INTEGER DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tab_roles (
        id TEXT PRIMARY KEY,
        tab_id TEXT NOT NULL REFERENCES skill_tabs(id) ON DELETE CASCADE,
        role_id TEXT NOT NULL,
        display_name TEXT DEFAULT '',
        category TEXT DEFAULT '',
        classification TEXT DEFAULT '',
        description TEXT DEFAULT '',
        capabilities TEXT DEFAULT '[]',
        recommended_tools TEXT DEFAULT '[]',
        skill_md_path TEXT DEFAULT '',
        system_prompt TEXT DEFAULT '',
        created_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tab_scenarios (
        id TEXT PRIMARY KEY,
        tab_id TEXT NOT NULL REFERENCES skill_tabs(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        tools TEXT DEFAULT '[]',
        recommended_roles TEXT DEFAULT '[]',
        generated_by TEXT DEFAULT 'llm',
        created_at TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tab_roles_tab ON tab_roles(tab_id)",
    "CREATE INDEX IF NOT EXISTS idx_tab_scenarios_tab ON tab_scenarios(tab_id)",
]


def init_tables():
    """Apply tab-related migrations. Called from db.init() or manually."""
    with db.cursor() as cur:
        for sql in TAB_MIGRATIONS:
            try:
                cur.execute(sql)
            except Exception as e:
                if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                    raise


# ── Models ──────────────────────────────────────────────────────────────────

@dataclass
class SkillTab:
    id: str
    name: str
    description: str = ""
    source_type: str = "builtin"
    source_url: str = ""
    branch: str = "main"
    sub_path: str = ""
    imported_at: str = ""
    updated_at: str = ""
    role_count: int = 0
    icon: str = ""
    tab_order: int = 0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "branch": self.branch,
            "sub_path": self.sub_path,
            "imported_at": self.imported_at,
            "updated_at": self.updated_at,
            "role_count": self.role_count,
            "icon": self.icon,
            "tab_order": self.tab_order,
        }


@dataclass
class TabRole:
    id: str
    tab_id: str
    role_id: str
    display_name: str = ""
    category: str = ""
    classification: str = ""
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    recommended_tools: List[str] = field(default_factory=list)
    skill_md_path: str = ""
    system_prompt: str = ""
    created_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "tab_id": self.tab_id,
            "role_id": self.role_id,
            "display_name": self.display_name,
            "category": self.category,
            "classification": self.classification,
            "description": self.description,
            "capabilities": self.capabilities,
            "recommended_tools": self.recommended_tools,
            "skill_md_path": self.skill_md_path,
            "created_at": self.created_at,
        }


@dataclass
class TabScenario:
    id: str
    tab_id: str
    name: str
    description: str = ""
    tools: List[str] = field(default_factory=list)
    recommended_roles: List[str] = field(default_factory=list)
    generated_by: str = "llm"
    created_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "tab_id": self.tab_id,
            "name": self.name,
            "description": self.description,
            "tools": self.tools,
            "recommended_roles": self.recommended_roles,
            "generated_by": self.generated_by,
            "created_at": self.created_at,
        }


# ── CRUD: Tabs ──────────────────────────────────────────────────────────────

def create_tab(
    *,
    id: str,
    name: str,
    description: str = "",
    source_type: str = "builtin",
    source_url: str = "",
    branch: str = "main",
    sub_path: str = "",
    icon: str = "",
    tab_order: int = 0,
) -> SkillTab:
    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO skill_tabs (id, name, description, source_type, source_url,
               branch, sub_path, icon, tab_order, imported_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (id, name, description, source_type, source_url,
             branch, sub_path, icon, tab_order, now, now),
        )
    return get_tab(id)


def get_tab(tab_id: str) -> SkillTab:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM skill_tabs WHERE id = ?", (tab_id,))
        row = cur.fetchone()
    if row is None:
        raise KeyError(f"tab not found: {tab_id}")
    return _row_to_tab(row)


def list_tabs() -> List[SkillTab]:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM skill_tabs ORDER BY tab_order ASC, name ASC")
        rows = cur.fetchall()
    return [_row_to_tab(r) for r in rows]


def update_tab(tab_id: str, **kwargs) -> SkillTab:
    current = get_tab(tab_id)
    fields = []
    values = []
    for key in ("name", "description", "icon", "tab_order", "source_url", "branch", "sub_path"):
        if key in kwargs and kwargs[key] is not None:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])
    if not fields:
        return current
    fields.append("updated_at = ?")
    values.append(datetime.utcnow().isoformat(sep=" ", timespec="seconds"))
    values.append(tab_id)
    with db.cursor() as cur:
        cur.execute(f"UPDATE skill_tabs SET {', '.join(fields)} WHERE id = ?", values)
    return get_tab(tab_id)


def delete_tab(tab_id: str) -> None:
    with db.cursor() as cur:
        cur.execute("DELETE FROM tab_scenarios WHERE tab_id = ?", (tab_id,))
        cur.execute("DELETE FROM tab_roles WHERE tab_id = ?", (tab_id,))
        cur.execute("DELETE FROM skill_tabs WHERE id = ?", (tab_id,))


def update_role_count(tab_id: str) -> None:
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM tab_roles WHERE tab_id = ?", (tab_id,))
        count = cur.fetchone()["cnt"]
        cur.execute("UPDATE skill_tabs SET role_count = ? WHERE id = ?", (count, tab_id))


# ── CRUD: Tab Roles ─────────────────────────────────────────────────────────

def add_role(
    *,
    id: str,
    tab_id: str,
    role_id: str,
    display_name: str = "",
    category: str = "",
    classification: str = "",
    description: str = "",
    capabilities: List[str] = None,
    recommended_tools: List[str] = None,
    skill_md_path: str = "",
    system_prompt: str = "",
) -> TabRole:
    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
    with db.cursor() as cur:
        cur.execute(
            """INSERT OR REPLACE INTO tab_roles
               (id, tab_id, role_id, display_name, category, classification,
                description, capabilities, recommended_tools, skill_md_path,
                system_prompt, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (id, tab_id, role_id, display_name, category, classification,
             description, json.dumps(capabilities or [], ensure_ascii=False),
             json.dumps(recommended_tools or [], ensure_ascii=False),
             skill_md_path, system_prompt, now),
        )
    update_role_count(tab_id)
    return get_role(id)


def get_role(role_id: str) -> TabRole:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tab_roles WHERE id = ?", (role_id,))
        row = cur.fetchone()
    if row is None:
        raise KeyError(f"tab role not found: {role_id}")
    return _row_to_tab_role(row)


def list_roles_for_tab(tab_id: str) -> List[TabRole]:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tab_roles WHERE tab_id = ? ORDER BY category, role_id", (tab_id,))
        rows = cur.fetchall()
    return [_row_to_tab_role(r) for r in rows]


def delete_roles_for_tab(tab_id: str) -> None:
    with db.cursor() as cur:
        cur.execute("DELETE FROM tab_roles WHERE tab_id = ?", (tab_id,))
    update_role_count(tab_id)


# ── CRUD: Tab Scenarios ─────────────────────────────────────────────────────

def add_scenario(
    *,
    id: str,
    tab_id: str,
    name: str,
    description: str = "",
    tools: List[str] = None,
    recommended_roles: List[str] = None,
    generated_by: str = "llm",
) -> TabScenario:
    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
    with db.cursor() as cur:
        cur.execute(
            """INSERT OR REPLACE INTO tab_scenarios
               (id, tab_id, name, description, tools, recommended_roles, generated_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (id, tab_id, name, description,
             json.dumps(tools or [], ensure_ascii=False),
             json.dumps(recommended_roles or [], ensure_ascii=False),
             generated_by, now),
        )
    return get_scenario(id)


def get_scenario(scenario_id: str) -> TabScenario:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tab_scenarios WHERE id = ?", (scenario_id,))
        row = cur.fetchone()
    if row is None:
        raise KeyError(f"tab scenario not found: {scenario_id}")
    return _row_to_tab_scenario(row)


def list_scenarios_for_tab(tab_id: str) -> List[TabScenario]:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tab_scenarios WHERE tab_id = ? ORDER BY name", (tab_id,))
        rows = cur.fetchall()
    return [_row_to_tab_scenario(r) for r in rows]


# ── Row mappers ─────────────────────────────────────────────────────────────

def _row_to_tab(row) -> SkillTab:
    return SkillTab(
        id=row["id"],
        name=row["name"] or "",
        description=row["description"] or "",
        source_type=row["source_type"] or "builtin",
        source_url=row["source_url"] or "",
        branch=row["branch"] or "main",
        sub_path=row["sub_path"] or "",
        imported_at=row["imported_at"] or "",
        updated_at=row["updated_at"] or "",
        role_count=row["role_count"] or 0,
        icon=row["icon"] or "",
        tab_order=row["tab_order"] or 0,
    )


def _row_to_tab_role(row) -> TabRole:
    return TabRole(
        id=row["id"],
        tab_id=row["tab_id"],
        role_id=row["role_id"],
        display_name=row["display_name"] or "",
        category=row["category"] or "",
        classification=row["classification"] or "",
        description=row["description"] or "",
        capabilities=json.loads(row["capabilities"] or "[]"),
        recommended_tools=json.loads(row["recommended_tools"] or "[]"),
        skill_md_path=row["skill_md_path"] or "",
        system_prompt=row["system_prompt"] or "",
        created_at=row["created_at"] or "",
    )


def _row_to_tab_scenario(row) -> TabScenario:
    return TabScenario(
        id=row["id"],
        tab_id=row["tab_id"],
        name=row["name"] or "",
        description=row["description"] or "",
        tools=json.loads(row["tools"] or "[]"),
        recommended_roles=json.loads(row["recommended_roles"] or "[]"),
        generated_by=row["generated_by"] or "llm",
        created_at=row["created_at"] or "",
    )


# ── Bootstrap: seed the builtin "software-engineering" tab from gstack ──────

def ensure_builtin_tab() -> SkillTab:
    """Create or return the default software-engineering tab."""
    try:
        return get_tab("software-engineering")
    except KeyError:
        return create_tab(
            id="software-engineering",
            name="软件工程",
            description="基于 gstack 的软件工程专家角色集合",
            source_type="builtin",
            icon="code",
            tab_order=0,
        )
