"""Scope subsystem for agent-platform."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_TIER_RANK: Dict[str, int] = {"free": 0, "basic": 1, "pro": 2, "enterprise": 3}


def _tier_gte(user_tier: str, required: str) -> bool:
    return _TIER_RANK.get(user_tier, -1) >= _TIER_RANK.get(required, 0)


_DEFAULT_PERMISSIONS: Dict[str, Any] = {
    "tools": {
        "brave_search": {"allowed": True, "min_tier": "free", "rate_limit": 200},
        "web_search": {"allowed": True, "min_tier": "free", "rate_limit": 200},
        "calculator": {"allowed": True, "min_tier": "free", "rate_limit": 0},
        "read_skill_reference": {"allowed": True, "min_tier": "free", "rate_limit": 0},
        "run_skill_script": {"allowed": True, "min_tier": "basic", "rate_limit": 50},
        "advanced_analysis": {"allowed": True, "min_tier": "pro", "rate_limit": 50},
        "api_access": {"allowed": True, "min_tier": "enterprise", "rate_limit": 1000},
    },
    "features": {
        "basic_query": {"min_tier": "free"},
        "skill_execution": {"min_tier": "basic"},
        "advanced_analysis": {"min_tier": "pro"},
        "api_access": {"min_tier": "enterprise"},
    },
    "data": {
        "public_data": {"read": True, "write": False, "min_tier": "free", "requires_consent": False},
        "user_data": {"read": True, "write": True, "min_tier": "free", "requires_consent": True},
        "internal_reports": {"read": False, "write": False, "min_tier": "enterprise", "requires_consent": False},
    },
}


@dataclass
class _RateWindow:
    count: int = 0
    window_start: float = field(default_factory=time.time)


class ScopeException(Exception):
    def __init__(self, action: str, required: str, current: str, reason: str = ""):
        self.action = action
        super().__init__(f"权限不足：{action} 需要 {required}，当前为 {current} ({reason})")


class ScopeManager:
    def __init__(self, permissions: Optional[Dict[str, Any]] = None) -> None:
        self._perms = permissions or _DEFAULT_PERMISSIONS
        self._rate_windows: Dict[Tuple[Any, str], _RateWindow] = {}
        self._lock = asyncio.Lock()

    def check_tool(self, tool: str, user_tier: str = "free") -> Tuple[bool, str]:
        cfg = self._perms.get("tools", {}).get(tool)
        if cfg is None:
            return True, ""
        if not cfg.get("allowed", False):
            return False, f"工具 {tool} 在此系统中已禁用"
        min_tier = cfg.get("min_tier", "free")
        if not _tier_gte(user_tier, min_tier):
            return False, f"需要 {min_tier} 或以上等级（当前：{user_tier}）"
        return True, ""

    async def check_rate_limit(self, tool: str, user_id: Any, user_tier: str = "free") -> Tuple[bool, str]:
        cfg = self._perms.get("tools", {}).get(tool, {})
        limit = cfg.get("rate_limit", 0)
        if limit == 0:
            return True, ""
        key = (user_id, tool)
        now = time.time()
        async with self._lock:
            window = self._rate_windows.get(key)
            if window is None or (now - window.window_start) >= 3600:
                self._rate_windows[key] = _RateWindow(count=1, window_start=now)
                return True, ""
            if window.count >= limit:
                return False, f"工具 {tool} 调用超限（{limit} 次/小时）"
            window.count += 1
            return True, ""

    def check_feature(self, feature: str, user_tier: str = "free") -> Tuple[bool, str]:
        cfg = self._perms.get("features", {}).get(feature)
        if cfg is None:
            return True, ""
        min_tier = cfg.get("min_tier", "free")
        if not _tier_gte(user_tier, min_tier):
            return False, f"功能 {feature} 需要 {min_tier} 或以上等级"
        return True, ""

    def check_data_access(self, data_type: str, operation: str = "read", user_tier: str = "free") -> Tuple[bool, str]:
        cfg = self._perms.get("data", {}).get(data_type)
        if cfg is None:
            return False, f"未知数据类型 {data_type}"
        if not cfg.get(operation, False):
            return False, f"数据 {data_type} 不允许 {operation} 操作"
        min_tier = cfg.get("min_tier", "free")
        if not _tier_gte(user_tier, min_tier):
            return False, f"访问 {data_type} 需要 {min_tier} 或以上等级"
        return True, ""

    def allowed_tools(self, user_tier: str = "free") -> List[str]:
        return [
            name for name, cfg in self._perms.get("tools", {}).items()
            if cfg.get("allowed", False) and _tier_gte(user_tier, cfg.get("min_tier", "free"))
        ]


_scope_manager: Optional[ScopeManager] = None


def get_scope_manager() -> ScopeManager:
    global _scope_manager
    if _scope_manager is None:
        _scope_manager = ScopeManager()
    return _scope_manager
