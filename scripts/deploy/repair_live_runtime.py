"""Repair and verify the live tree after an interrupted full deployment."""
from __future__ import annotations

import fnmatch
import sys
import time
from pathlib import Path

from ssh_config import DeployConfigError, DeployConnectionError, RemoteCommandError, connect, load_deploy_config, run_remote


LOCAL_ROOT = Path(__file__).resolve().parents[2]
LIVE = "/home/admin/agent-platform"

UPLOAD_DIRS = [
    "hermes-bridge",
]

EXCLUDE_PATTERNS = {
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "venv",
    ".env",
    ".gstack",
    "*.bak*",
    "orchestrator.db",
}


def _excluded(path: Path) -> bool:
    return any(fnmatch.fnmatch(part, pattern) for part in path.parts for pattern in EXCLUDE_PATTERNS)


def run(client, command: str, *, label: str, timeout: int = 120, check: bool = False, secrets: list[str] | None = None):
    return run_remote(
        client,
        command,
        timeout=timeout,
        label=label,
        check=check,
        secrets=secrets or [],
    )


def fire_and_forget(client, command: str) -> None:
    client.exec_command(command, timeout=5)


def upload_tree(client, rel_dir: str) -> None:
    local_dir = LOCAL_ROOT / rel_dir
    if not local_dir.exists():
        raise FileNotFoundError(local_dir)

    sftp = client.open_sftp()
    try:
        for path in local_dir.rglob("*"):
            rel = path.relative_to(LOCAL_ROOT)
            if _excluded(rel):
                continue
            remote = f"{LIVE}/{rel.as_posix()}"
            if path.is_dir():
                run(client, f"mkdir -p '{remote}'", label=f"mkdir-{rel.as_posix()}", timeout=60)
                continue
            remote_dir = "/".join(remote.split("/")[:-1])
            run(client, f"mkdir -p '{remote_dir}'", label="mkdir-upload", timeout=60)
            print(f"[put] {rel.as_posix()} -> {remote}")
            sftp.put(str(path), remote)
    finally:
        sftp.close()


def main() -> int:
    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        secrets = [config.password or ""]
        print(f"=== Connecting to {config.endpoint} via {config.auth_method} auth ===")
        client = connect(config)
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1

    try:
        run(client, f"test -d {LIVE}", label="assert-live-dir", check=True, secrets=secrets)
        for rel_dir in UPLOAD_DIRS:
            upload_tree(client, rel_dir)

        run(client, f"mkdir -p {LIVE}/logs {LIVE}/agent/data", label="ensure-runtime-dirs", check=True, secrets=secrets)
        run(client, "fuser -k 8080/tcp 2>/dev/null || true", label="stop-gateway", timeout=60, secrets=secrets)
        run(client, "fuser -k 8001/tcp 2>/dev/null || true", label="stop-agent", timeout=60, secrets=secrets)
        run(client, "fuser -k 8002/tcp 2>/dev/null || true", label="stop-hermes", timeout=60, secrets=secrets)
        time.sleep(2)

        fire_and_forget(
            client,
            f"cd {LIVE}; nohup env GATEWAY_HOST=0.0.0.0 ./build/agent-gateway --config configs/config.yaml > logs/gateway.log 2>&1 < /dev/null &",
        )
        fire_and_forget(
            client,
            f"cd {LIVE}/agent; nohup env PYTHONUNBUFFERED=1 ./.venv/bin/python main.py > ../logs/agent.log 2>&1 < /dev/null &",
        )
        fire_and_forget(
            client,
            f"cd {LIVE}/hermes-bridge; nohup env PYTHONPATH={LIVE}/hermes-bridge PYTHONUNBUFFERED=1 GSTACK_AUTOLOAD=1 {LIVE}/agent/.venv/bin/python main.py > /tmp/hermes-bridge.log 2>&1 < /dev/null &",
        )
        print("start commands sent")
        client.close()
        time.sleep(8)
        client = connect(config)

        checks = [
            ("processes", "pgrep -fa 'agent-gateway|agent/.venv/bin/python main.py' || true"),
            ("ports", "ss -tlnp | grep -E ':8080|:8001|:8002'"),
            ("gateway-health", "curl -fsS --max-time 5 http://127.0.0.1:8080/api/v1/health"),
            ("agent-health", "curl -fsS --max-time 5 http://127.0.0.1:8001/health"),
            ("hermes-health", "curl -fsS --max-time 5 http://127.0.0.1:8002/api/v2/health"),
            ("kg-stats-agent", "curl -fsS --max-time 8 http://127.0.0.1:8001/api/v1/knowledge-graph/stats"),
            ("frontend-index", f"test -f {LIVE}/web/dist/index.html && grep -o 'KnowledgeGraphPage[^\" ]*' {LIVE}/web/dist/index.html {LIVE}/web/dist/assets/*.js 2>/dev/null | head -5 || true"),
        ]
        for label, command in checks:
            run(client, command, label=label, timeout=60, check=True, secrets=secrets)

        print("=== LIVE RUNTIME REPAIR COMPLETE ===")
        return 0
    except RemoteCommandError as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        run(client, f"tail -80 {LIVE}/logs/gateway.log 2>&1 || true", label="gateway-log", timeout=30)
        run(client, f"tail -80 {LIVE}/logs/agent.log 2>&1 || true", label="agent-log", timeout=30)
        run(client, "tail -80 /tmp/hermes-bridge.log 2>&1 || true", label="hermes-log", timeout=30)
        return 2
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
