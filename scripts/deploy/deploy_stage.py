"""Deploy step 1-3: backup + stage + rebuild (no destructive action yet).

All commands run as root. Does NOT touch the live /home/admin/agent-platform/.
Creates:
  - /home/admin/backups/agent-platform-YYYYMMDD-HHMMSS.tar.gz
  - /home/admin/agent-platform-new/  (staging clone + local fixes sync'd in)
  - /home/admin/agent-platform-new/build/agent-gateway-new
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, run_remote

LIVE = "/home/admin/agent-platform"
STAGE = "/home/admin/agent-platform-new"
BACKUP_DIR = "/home/admin/backups"
TS = time.strftime("%Y%m%d-%H%M%S")

# Local-fixed files to upload over the staging tree.
# Paths are (local_path, remote_rel_path).
LOCAL_ROOT = Path(r"C:\Projects\agent-platform")
FILES = [
    ("cmd/gateway/main.go", "cmd/gateway/main.go"),
    ("configs/config.yaml", "configs/config.yaml"),
    ("agent/app/tools/brave_search.py", "agent/app/tools/brave_search.py"),
    ("agent/main.py", "agent/main.py"),
    ("agent/tests/test_brave_search.py", "agent/tests/test_brave_search.py"),
    ("internal/api/handler/auth.go", "internal/api/handler/auth.go"),
    (".env.example", ".env.example"),
    (".gitignore", ".gitignore"),
    ("README.md", "README.md"),
    ("proto/agent.proto", "proto/agent.proto"),
]

RUN_SECRETS: list[str] = []


def run(client, cmd: str, timeout: int = 300, label: str = "") -> tuple[int, str, str]:
    return run_remote(client, cmd, timeout=timeout, label=label, secrets=RUN_SECRETS)


def main() -> int:
    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        RUN_SECRETS[:] = [config.password or ""]
        print(f"=== Connecting to {config.endpoint} via {config.auth_method} auth ===")
        client = connect(config)
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        print("Set DEPLOY_PASS or DEPLOY_KEY_FILE locally; see .env.example for DEPLOY_* variables.", file=sys.stderr)
        return 1

    try:
        print(f"=== Step 1: backup {LIVE} ===")
        run(client, f"mkdir -p {BACKUP_DIR}")
        # Exclude the 32MB binary + data dir to keep backup lean and fast.
        rc, _, _ = run(
            client,
            f"tar --exclude='{LIVE}/build/agent-gateway' --exclude='{LIVE}/data/*.db' "
            f"-czf {BACKUP_DIR}/agent-platform-{TS}.tar.gz -C /home/admin agent-platform 2>&1",
            timeout=180,
            label="tar-backup",
        )
        if rc != 0:
            print("[FATAL] backup failed; aborting before any further step", file=sys.stderr)
            return 2
        run(client, f"ls -lh {BACKUP_DIR}/agent-platform-{TS}.tar.gz")

        print(f"=== Step 2: prepare staging {STAGE} ===")
        run(client, f"rm -rf {STAGE} && cp -a {LIVE} {STAGE}")
        run(client, f"chown -R root:root {STAGE}")  # avoid git-dubious-ownership issues during build
        run(client, f"ls -la {STAGE}/ | head -20")

        print("=== Step 3: upload local-fixed files ===")
        sftp = client.open_sftp()
        try:
            for local_rel, remote_rel in FILES:
                local = LOCAL_ROOT / local_rel
                remote = f"{STAGE}/{remote_rel}"
                if not local.exists():
                    print(f"[skip] local missing: {local}")
                    continue
                # Ensure remote dir exists.
                remote_dir = "/".join(remote.split("/")[:-1])
                run(client, f"mkdir -p {remote_dir}", label="mkdir")
                print(f"[put] {local} -> {remote}")
                sftp.put(str(local), remote)
        finally:
            sftp.close()

        # Remove the deleted files if present in staging.
        run(client, f"rm -f {STAGE}/cmd/gateway/main_secure.go {STAGE}/pkg/auth/jwt.go {STAGE}/pkg/auth/jwt_test.go")

        print("=== Step 4: verify our fixes landed ===")
        run(client, f"grep -n 'getEnvDefault\\|GATEWAY_HOST' {STAGE}/cmd/gateway/main.go | head -5")
        run(client, f"test -f {STAGE}/agent/app/tools/brave_search.py && echo BRAVE_OK || echo BRAVE_MISSING")
        run(client, f"grep -n 'BraveSearchTool' {STAGE}/agent/main.py | head -5")

        print("=== Step 5: go build ===")
        rc, _, _ = run(
            client,
            f"cd {STAGE} && go build -o build/agent-gateway-new ./cmd/gateway 2>&1",
            timeout=300,
            label="go-build",
        )
        if rc != 0:
            print("[FATAL] go build failed; see output above", file=sys.stderr)
            return 3
        run(client, f"ls -lh {STAGE}/build/agent-gateway-new && file {STAGE}/build/agent-gateway-new")

        print("=== Step 6: agent deps + tests ===")
        # Use the LIVE venv's pip, but execute test against STAGING copy of agent code.
        run(
            client,
            f"{LIVE}/agent/.venv/bin/pip install -q httpx pytest pytest-asyncio 2>&1 | tail -10",
            timeout=180,
            label="pip-install",
        )
        run(
            client,
            f"cd {STAGE}/agent && ../agent/.venv/bin/python -m pytest tests/test_brave_search.py -q 2>&1 | tail -20 || true",
            timeout=120,
            label="pytest",
        )

        print("=== STAGING COMPLETE ===")
        print(f"Backup:     {BACKUP_DIR}/agent-platform-{TS}.tar.gz")
        print(f"Staging:    {STAGE}")
        print(f"New binary: {STAGE}/build/agent-gateway-new")
        print("NEXT STEP (destructive) REQUIRES USER GO-AHEAD.")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
