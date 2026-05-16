"""Static catalogue of tool scenarios.

A scenario tells the orchestrator which tool surfaces are relevant to the
input — e.g. running a DX review only makes sense with the browser available.
For now this is a hard-coded list; storing them in SQLite buys us nothing
until users start authoring custom scenarios. Move to a table when we get
that requirement.
"""
from __future__ import annotations

from typing import Dict, List

# Each scenario references tool surfaces by id. The orchestrator (Phase 3)
# decides how to wire them — usually by exporting env vars or by selecting
# which gstack roles fit the surface.
SCENARIOS: List[Dict] = [
    {
        "id": "code-review",
        "name": "代码评审",
        "description": "对 PR 或本地改动做多角色评审，捕获 CI 通过但生产会炸的问题。",
        "tools": ["read", "grep", "git", "bash"],
        "recommended_roles": [
            "review", "codex", "investigate", "plan-eng-review", "cso",
        ],
    },
    {
        "id": "product-plan",
        "name": "产品规划",
        "description": "从 idea 到可执行计划，CEO/Design/Eng/DX 四视角联评。",
        "tools": ["read", "write", "ask", "websearch"],
        "recommended_roles": [
            "office-hours", "plan-ceo-review", "plan-design-review",
            "plan-eng-review", "plan-devex-review", "autoplan",
        ],
    },
    {
        "id": "design-system",
        "name": "设计系统",
        "description": "构建/审查设计系统:tokens、组件、可达性、视觉打磨。",
        "tools": ["read", "write", "browser", "figma"],
        "recommended_roles": [
            "design-consultation", "design-review", "design-shotgun",
            "design-html", "plan-design-review",
        ],
    },
    {
        "id": "qa-loop",
        "name": "QA 自动化",
        "description": "打开真实浏览器,跑 QA 流程,捕获并修 bug。",
        "tools": ["browser", "bash", "read", "write"],
        "recommended_roles": ["qa", "qa-only", "investigate", "review"],
    },
    {
        "id": "release-train",
        "name": "发布闭环",
        "description": "测试 → 评审 → push → PR → 部署 → 金丝雀监控。",
        "tools": ["bash", "git", "browser"],
        "recommended_roles": [
            "ship", "review", "land-and-deploy", "canary",
            "landing-report", "document-release",
        ],
    },
    {
        "id": "security-audit",
        "name": "安全审计",
        "description": "OWASP Top 10 + STRIDE,扫漏洞、不当鉴权、注入面。",
        "tools": ["read", "grep", "bash"],
        "recommended_roles": ["cso", "review", "investigate"],
    },
    {
        "id": "browser-research",
        "name": "浏览器调研",
        "description": "用真实浏览器抓数据、登录态测试、调研竞品。",
        "tools": ["browser"],
        "recommended_roles": [
            "browse", "scrape", "skillify", "open-gstack-browser",
            "setup-browser-cookies", "pair-agent",
        ],
    },
    {
        "id": "ops-health",
        "name": "运维健康",
        "description": "代码质量看板、性能基准、跨模型评测。",
        "tools": ["read", "bash"],
        "recommended_roles": ["health", "benchmark", "benchmark-models", "retro"],
    },
    {
        "id": "freeform",
        "name": "自由编排",
        "description": "不限定场景,任意挑选角色组合。",
        "tools": [],
        "recommended_roles": [],
    },
]


def list_scenarios() -> List[Dict]:
    return SCENARIOS


def get_scenario(scenario_id: str) -> Dict | None:
    return next((s for s in SCENARIOS if s["id"] == scenario_id), None)
