"""Destructive cut-over: kill old gateway + agent, swap binary, rsync source,
restart, health-check.

Rollback data:
  Binary backup: /home/admin/agent-platform/build/agent-gateway.bak-<TS>
  Tree backup:   /home/admin/backups/agent-platform-20260513-135408.tar.gz
  Staging kept:  /home/admin/agent-platform-new/  (not deleted on success)
"""
from __future__ import annotations

import sys
import time

from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, run_remote

LIVE = "/home/admin/agent-platform"
STAGE = "/home/admin/agent-platform-new"
TS = time.strftime("%Y%m%d-%H%M%S")

# Files to copy from staging → live
SYNC_FILES = [
    "cmd/gateway/main.go",
    "configs/config.yaml",
    "agent/app/tools/brave_search.py",
    "agent/main.py",
    "agent/tests/test_brave_search.py",
    "internal/api/handler/auth.go",
    ".env.example",
    ".gitignore",
    "README.md",
    "proto/agent.proto",
]

# Files to DELETE in live (they were broken code from the earlier cleanup)
DELETE_FILES = [
    "cmd/gateway/main_secure.go",
    "pkg/auth/jwt.go",
    "pkg/auth/jwt_test.go",
]

RUN_SECRETS: list[str] = []


def run(c, cmd, tmo=120, label=""):
    return run_remote(c, cmd, timeout=tmo, label=label, secrets=RUN_SECRETS)


def main() -> int:
    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        RUN_SECRETS[:] = [config.password or ""]
        print(f"=== Connecting to {config.endpoint} via {config.auth_method} auth ===")
        c = connect(config)
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        print("Set DEPLOY_PASS or DEPLOY_KEY_FILE locally; see .env.example for DEPLOY_* variables.", file=sys.stderr)
        return 1

    try:
        # ── Phase 1: identify current pids
        print("=== phase 1: snapshot current pids ===")
        run(c, "pgrep -f 'agent-gateway --config' || echo none", label="pid-gateway")
        run(c, "pgrep -f 'agent/.venv/bin/python main.py' || echo none", label="pid-agent")
        run(c, "pgrep -f 'hermes-bridge.*main.py' || echo none", label="pid-bridge")

        # ── Phase 2: backup old binary
        print("=== phase 2: backup live binary ===")
        rc, _, _ = run(c, f"cp -av {LIVE}/build/agent-gateway {LIVE}/build/agent-gateway.bak-{TS}")
        if rc != 0:
            print("[FATAL] backup of live binary failed; aborting")
            return 2

        # ── Phase 3: rsync source files + delete broken files
        print("=== phase 3: sync source files ===")
        for rel in SYNC_FILES:
            run(c, f"cp -av {STAGE}/{rel} {LIVE}/{rel}", label="cp")
        for rel in DELETE_FILES:
            run(c, f"rm -fv {LIVE}/{rel}", label="rm")

        # Restore admin ownership on modified files (admin user runs the services)
        run(c, f"chown -R admin:admin {LIVE}/agent {LIVE}/cmd {LIVE}/configs {LIVE}/internal {LIVE}/proto "
               f"{LIVE}/.env.example {LIVE}/.gitignore {LIVE}/README.md 2>/dev/null; true")

        # ── Phase 4: swap binary
        print("=== phase 4: swap binary ===")
        run(c, f"cp -av {STAGE}/build/agent-gateway-new {LIVE}/build/agent-gateway && chown admin:admin {LIVE}/build/agent-gateway && chmod +x {LIVE}/build/agent-gateway")

        # ── Phase 5: stop old processes
        print("=== phase 5: stop old processes ===")
        run(c, "pkill -TERM -f 'agent-gateway --config' || true")
        run(c, "pkill -TERM -f 'agent/.venv/bin/python main.py' || true")
        run(c, "pkill -TERM -f 'multiprocessing.resource_tracker' || true")
        time.sleep(2)
        run(c, "pgrep -f 'agent-gateway --config' || echo gateway-stopped")
        run(c, "pgrep -f 'agent/.venv/bin/python main.py' || echo agent-stopped")

        # Ensure ports freed
        run(c, "ss -tlnp | grep -E ':8080|:8001' || echo ports-free")

        # ── Phase 6: start new processes
        print("=== phase 6: start new gateway + agent ===")
        run(
            c,
            f"mkdir -p {LIVE}/logs && cd {LIVE} && "
            f"GATEWAY_HOST=0.0.0.0 nohup ./build/agent-gateway --config configs/config.yaml "
            f"> logs/gateway.log 2>&1 &",
            label="start-gw",
        )
        run(
            c,
            f"cd {LIVE}/agent && nohup ./.venv/bin/python main.py > ../logs/agent.log 2>&1 &",
            label="start-agent",
        )

        print("waiting 6s for startup...")
        time.sleep(6)

        # ── Phase 7: health-check
        print("=== phase 7: health-check ===")
        run(c, "pgrep -fa 'agent-gateway --config' || echo gateway-NOT-RUNNING")
        run(c, "pgrep -fa 'agent/.venv/bin/python main.py' || echo agent-NOT-RUNNING")
        run(c, "ss -tlnp | grep -E ':8080|:8001'")
        run(c, "curl -fsS --max-time 5 http://127.0.0.1:8080/health 2>&1 || echo gw-localhost-fail")
        run(c, "curl -fsS --max-time 5 http://127.0.0.1:8001/health 2>&1 || echo agent-localhost-fail")
        run(c, "curl -fsS --max-time 5 http://172.19.30.12:8080/health 2>&1 || echo gw-internal-fail")

        # Brave search in tool list
        run(c, "curl -fsS --max-time 5 http://127.0.0.1:8001/api/v1/tools 2>&1 | head -c 600 || echo no-tools-endpoint")

        # Recent log tails
        print("=== logs ===")
        run(c, f"tail -40 {LIVE}/logs/gateway.log 2>&1")
        run(c, f"tail -40 {LIVE}/logs/agent.log 2>&1")
        return 0
    finally:
        c.close()


if __name__ == "__main__":
    sys.exit(main())
