"""范围子系统

Enforces capability boundaries, permission tiers and rate limits:
- Tier-based tool access (free / basic / pro / enterprise)
- Data access control (public / user-authorized / forbidden)
- In-memory rate limiting (window counter, resets per period)
- ScopeException for unauthorised actions
- Audit logging for every permission decision
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)

# ── Permissions file path ────────────────────────────────────────────────────
_PERMISSIONS_FILE = Path(__file__).parent / "permissions.json"


# ── Tier ordering ─────────────────────────────────────────────────────────────

_TIER_RANK: Dict[str, int] = {
    "free": 0,
    "basic": 1,
    "pro": 2,
    "enterprise": 3,
}


def _tier_gte(user_tier: str, required: str) -> bool:
    return _TIER_RANK.get(user_tier, -1) >= _TIER_RANK.get(required, 0)


# ── Permission table loading ──────────────────────────────────────────────────
#
# Permissions are loaded from permissions.json (same directory).
# If the file is missing or malformed, a minimal built-in fallback is used.
#
# Schema per section:
#   tools.<name>:    {allowed: bool, min_tier: str, rate_limit: int (0=unlimited)}
#   features.<name>: {min_tier: str}
#   data.<name>:     {read: bool, write: bool, min_tier: str, requires_consent: bool}

_FALLBACK_PERMISSIONS: Dict[str, Any] = {
    "tools": {},
    "features": {},
    "data": {},
}


def _load_permissions() -> Dict[str, Any]:
    """Load permissions from JSON file, falling back to empty defaults."""
    if not _PERMISSIONS_FILE.exists():
        logger.warning("permissions_file_not_found", path=str(_PERMISSIONS_FILE))
        return _FALLBACK_PERMISSIONS
    try:
        with open(_PERMISSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Basic structure validation
        if not isinstance(data, dict):
            raise ValueError("permissions.json root must be an object")
        for key in ("tools", "features", "data"):
            if key in data and not isinstance(data[key], dict):
                raise ValueError(f"permissions.json['{key}'] must be an object")
        logger.info("permissions_loaded", path=str(_PERMISSIONS_FILE))
        return data
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        logger.error("permissions_load_failed", error=str(exc), path=str(_PERMISSIONS_FILE))
        return _FALLBACK_PERMISSIONS


# ── Rate-limit window ─────────────────────────────────────────────────────────

@dataclass
class _RateWindow:
    count: int = 0
    window_start: float = field(default_factory=time.time)


# ── Exception ─────────────────────────────────────────────────────────────────

class ScopeException(Exception):
    """Raised when an action falls outside the permitted scope."""

    def __init__(self, action: str, required: str, current: str, reason: str = ""):
        self.action = action
        self.required = required
        self.current = current
        msg = f"权限不足：{action} 需要 {required}，当前为 {current}"
        if reason:
            msg += f"（{reason}）"
        super().__init__(msg)


# ── ScopeManager ─────────────────────────────────────────────────────────────

class ScopeManager:
    """Enforces capability boundaries at runtime.

    Example::

        scope = ScopeManager()
        ok, reason = scope.check_tool("get_financial_data", user_tier="free")
        # ok=False, reason="需要 basic 或以上等级"
    """

    def __init__(
        self, permissions: Optional[Dict[str, Any]] = None
    ) -> None:
        self._perms = permissions or _load_permissions()
        # (user_id, tool) → _RateWindow
        self._rate_windows: Dict[Tuple[Any, str], _RateWindow] = {}

    # ── Tool checks ───────────────────────────────────────────────────────────

    def check_tool(
        self, tool: str, user_tier: str = "free"
    ) -> Tuple[bool, str]:
        """Return (allowed, reason).

        Checks: globally allowed → tier requirement.
        Does NOT check rate limits (call check_rate_limit separately).
        """
        cfg = self._perms.get("tools", {}).get(tool)
        if cfg is None:
            # Unknown tool — allow by default (log for visibility)
            self._audit("tool", tool, user_tier, True, "未知工具，默认放行")
            return True, ""

        if not cfg.get("allowed", False):
            reason = f"工具 {tool} 在此系统中已禁用"
            self._audit("tool", tool, user_tier, False, reason)
            return False, reason

        min_tier = cfg.get("min_tier", "free")
        if not _tier_gte(user_tier, min_tier):
            reason = f"需要 {min_tier} 或以上等级（当前：{user_tier}）"
            self._audit("tool", tool, user_tier, False, reason)
            return False, reason

        self._audit("tool", tool, user_tier, True, "")
        return True, ""

    def assert_tool(self, tool: str, user_tier: str = "free") -> None:
        """Like check_tool but raises ScopeException on failure."""
        ok, reason = self.check_tool(tool, user_tier)
        if not ok:
            cfg = self._perms.get("tools", {}).get(tool, {})
            raise ScopeException(
                action=f"使用工具 {tool}",
                required=cfg.get("min_tier", "?"),
                current=user_tier,
                reason=reason,
            )

    # ── Rate limiting ─────────────────────────────────────────────────────────

    def check_rate_limit(
        self, tool: str, user_id: Any, user_tier: str = "free"
    ) -> Tuple[bool, str]:
        """Return (within_limit, reason).  Increments counter if within limit."""
        cfg = self._perms.get("tools", {}).get(tool, {})
        limit = cfg.get("rate_limit", 0)
        if limit == 0:
            return True, ""

        key = (user_id, tool)
        now = time.time()
        window = self._rate_windows.get(key)

        if window is None or (now - window.window_start) >= 3600:
            self._rate_windows[key] = _RateWindow(count=1, window_start=now)
            return True, ""

        if window.count >= limit:
            reason = f"工具 {tool} 调用超限（{limit} 次/小时）"
            return False, reason

        window.count += 1
        return True, ""

    # ── Feature checks ────────────────────────────────────────────────────────

    def check_feature(
        self, feature: str, user_tier: str = "free"
    ) -> Tuple[bool, str]:
        cfg = self._perms.get("features", {}).get(feature)
        if cfg is None:
            return True, ""   # unknown feature — pass through
        min_tier = cfg.get("min_tier", "free")
        if not _tier_gte(user_tier, min_tier):
            reason = f"功能 {feature} 需要 {min_tier} 或以上等级"
            self._audit("feature", feature, user_tier, False, reason)
            return False, reason
        self._audit("feature", feature, user_tier, True, "")
        return True, ""

    # ── Data access checks ────────────────────────────────────────────────────

    def check_data_access(
        self,
        data_type: str,
        operation: str = "read",   # "read" | "write"
        user_tier: str = "free",
    ) -> Tuple[bool, str]:
        cfg = self._perms.get("data", {}).get(data_type)
        if cfg is None:
            return False, f"未知数据类型 {data_type}"

        if not cfg.get(operation, False):
            reason = f"数据 {data_type} 不允许 {operation} 操作"
            self._audit("data", data_type, user_tier, False, reason)
            return False, reason

        min_tier = cfg.get("min_tier", "free")
        if not _tier_gte(user_tier, min_tier):
            reason = f"访问 {data_type} 需要 {min_tier} 或以上等级"
            self._audit("data", data_type, user_tier, False, reason)
            return False, reason

        self._audit("data", data_type, user_tier, True, "")
        return True, ""

    # ── Batch plan filter ─────────────────────────────────────────────────────

    def filter_plan(
        self, plan: List[Dict[str, Any]], user_tier: str = "free"
    ) -> List[Dict[str, Any]]:
        """Mark each plan step as blocked or allowed based on tool permissions."""
        for step in plan:
            tool = step.get("tool") or step.get("action", "")
            ok, reason = self.check_tool(tool, user_tier)
            step["blocked"] = not ok
            if not ok:
                step["block_reason"] = reason
        return plan

    # ── Allowed tools list ────────────────────────────────────────────────────

    def allowed_tools(self, user_tier: str = "free") -> List[str]:
        """Return names of all tools accessible to the given tier."""
        return [
            name
            for name, cfg in self._perms.get("tools", {}).items()
            if cfg.get("allowed", False)
            and _tier_gte(user_tier, cfg.get("min_tier", "free"))
        ]

    # ── Hot reload ─────────────────────────────────────────────────────────────

    def reload_permissions(self) -> bool:
        """Reload permissions from JSON file. Returns True on success."""
        new_perms = _load_permissions()
        if new_perms is _FALLBACK_PERMISSIONS:
            return False
        self._perms = new_perms
        logger.info("permissions_reloaded")
        return True

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _audit(
        category: str, name: str, tier: str, allowed: bool, reason: str
    ) -> None:
        log = logger.debug if allowed else logger.info
        log(
            "scope_check",
            category=category,
            name=name,
            tier=tier,
            allowed=allowed,
            reason=reason or "ok",
        )


# ── Module-level singleton ────────────────────────────────────────────────────
_scope_manager: Optional[ScopeManager] = None


def get_scope_manager() -> ScopeManager:
    global _scope_manager
    if _scope_manager is None:
        _scope_manager = ScopeManager()
    return _scope_manager
