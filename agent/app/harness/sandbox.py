"""Session filesystem sandbox for agent-platform."""
from __future__ import annotations

import os
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SANDBOX_ENV_VAR = "JOEYAGENT_SANDBOX"
DEFAULT_SANDBOX_NAME = ".joeyagent"


class SandboxError(Exception):
    """Raised when sandbox operations fail."""


class Sandbox:
    """Per-session sandbox directory with access boundary enforcement."""

    def __init__(self, root: Path, session_id: str) -> None:
        self._root = root
        self._session_id = session_id
        self._session_dir: Optional[Path] = None

    @property
    def path(self) -> Path:
        if self._session_dir is None:
            raise SandboxError("Sandbox not initialized; call init() first")
        return self._session_dir

    def init(self) -> Path:
        self._session_dir = self._root / "sessions" / self._session_id
        (self._session_dir / "tmp").mkdir(parents=True, exist_ok=True)
        (self._session_dir / "output").mkdir(parents=True, exist_ok=True)
        logger.info("sandbox_initialized session=%s path=%s", self._session_id, self._session_dir)
        return self._session_dir

    def tmp_path(self, *segments: str) -> Path:
        p = self.path / "tmp" / os.path.join(*segments)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def output_path(self, *segments: str) -> Path:
        p = self.path / "output" / os.path.join(*segments)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def assert_path_allowed(self, target: str) -> Path:
        resolved = (self.path / target).resolve()
        if not str(resolved).startswith(str(self.path.resolve())):
            raise SandboxError(f"Path {target} escapes sandbox boundary {self.path}")
        return resolved

    def cleanup(self) -> None:
        if self._session_dir and self._session_dir.exists():
            shutil.rmtree(self._session_dir, ignore_errors=True)
            logger.info("sandbox_cleaned session=%s", self._session_id)


class SandboxManager:
    """Singleton that manages sandbox root and per-session sandboxes."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = root or self._resolve_root()
        self._sandboxes: dict[str, Sandbox] = {}
        self._init_root()

    @staticmethod
    def _resolve_root() -> Path:
        env = os.environ.get(SANDBOX_ENV_VAR)
        if env:
            return Path(env)
        return Path.home() / DEFAULT_SANDBOX_NAME

    def _init_root(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / "sessions").mkdir(exist_ok=True)
        (self._root / "global").mkdir(exist_ok=True)

    async def create_sandbox(self, session_id: str) -> Sandbox:
        sandbox = Sandbox(self._root, session_id)
        sandbox.init()
        self._sandboxes[session_id] = sandbox
        return sandbox

    async def get_sandbox(self, session_id: str) -> Optional[Sandbox]:
        return self._sandboxes.get(session_id)

    async def remove_sandbox(self, session_id: str) -> None:
        sandbox = self._sandboxes.pop(session_id, None)
        if sandbox:
            sandbox.cleanup()

    @property
    def root(self) -> Path:
        return self._root


_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager(root: Optional[Path] = None) -> SandboxManager:
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager(root=root)
    return _sandbox_manager
