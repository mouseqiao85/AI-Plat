"""Deploy refactored hermes-bridge + Skill Tab system to the live server.

Uploads all modified/new bridge modules, builds the frontend, syncs the
dist files, restarts services, and verifies endpoints.

Changes in this deployment:
  - hermes-bridge: Removed CLI dependency, added Tab/Import/Classifier modules
  - web: Added Tab UI to FlowsPage, ImportSkillModal component, types, API
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, run_remote

LIVE = "/home/admin/agent-platform"
LOCAL_ROOT = Path(r"C:\Projects\agent-platform")

BRIDGE_FILES = [
    "hermes-bridge/bridge/__init__.py",
    "hermes-bridge/bridge/types.py",
    "hermes-bridge/bridge/db.py",
    "hermes-bridge/bridge/hermes_cli.py",
    "hermes-bridge/bridge/gstack_loader.py",
    "hermes-bridge/bridge/scenarios.py",
    "hermes-bridge/bridge/flows.py",
    "hermes-bridge/bridge/runs.py",
    "hermes-bridge/bridge/orchestrator.py",
    "hermes-bridge/bridge/chat_handler.py",
    "hermes-bridge/bridge/skill_tabs.py",
    "hermes-bridge/bridge/github_importer.py",
    "hermes-bridge/bridge/llm_classifier.py",
    "hermes-bridge/main.py",
]

RUN_SECRETS: list[str] = []


def run(client, cmd: str, timeout: int = 120, label: str = "") -> tuple[int, str, str]:
    return run_remote(client, cmd, timeout=timeout, label=label, secrets=RUN_SECRETS, max_output_chars=800)


def upload_files(client, sftp, files: list, prefix: str = ""):
    for rel in files:
        local = LOCAL_ROOT / rel
        if not local.exists():
            print(f"  SKIP (not found): {rel}")
            continue
        remote = f"{LIVE}/{rel}"
        remote_dir = os.path.dirname(remote)
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            parts = remote_dir.split("/")
            for i in range(2, len(parts) + 1):
                path = "/".join(parts[:i])
                try:
                    sftp.stat(path)
                except FileNotFoundError:
                    sftp.mkdir(path)
        sftp.put(str(local), remote)
        print(f"  {prefix}Uploaded: {rel}")


def main() -> int:
    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        RUN_SECRETS[:] = [config.password or ""]
        print(f"=== Deploying to {config.endpoint} via {config.auth_method} auth ===\n")
        client = connect(config)
        print("Connected.\n")
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"SSH setup failed: {exc}", file=sys.stderr)
        print("Set DEPLOY_PASS or DEPLOY_KEY_FILE locally; see .env.example for DEPLOY_* variables.", file=sys.stderr)
        return 1

    sftp = client.open_sftp()
    try:
        # 1. Upload bridge files
        print("--- Step 1: Upload hermes-bridge files ---")
        upload_files(client, sftp, BRIDGE_FILES)
        print()

        # 2. Restart hermes-bridge
        print("--- Step 2: Restart hermes-bridge ---")
        run(client, "supervisorctl restart hermes-bridge || systemctl restart hermes-bridge", label="restart")
        time.sleep(3)
        print()

        # 3. Verify bridge health
        print("--- Step 3: Verify bridge ---")
        rc, out, _ = run(client, "curl -s http://localhost:8002/api/v2/health", label="health")
        print(f"    Response: {out[:200]}")
        if '"status":"ok"' not in out and '"status": "ok"' not in out:
            print("    WARNING: health check did not return ok")
        print()

        # 4. Verify tabs endpoint
        print("--- Step 4: Verify tabs API ---")
        rc, out, _ = run(client, "curl -s http://localhost:8002/api/v2/tabs", label="tabs")
        print(f"    Response: {out[:200]}")
        print()

        # 5. Build frontend locally if dist doesn't exist
        web_dist = LOCAL_ROOT / "web" / "dist"
        if not web_dist.exists():
            print("--- Step 5a: Build frontend (local) ---")
            print("  NOTE: Frontend build must be done locally before running this script.")
            print("  Run: cd web && npm run build")
            print("  Skipping frontend upload for now.")
        else:
            print("--- Step 5: Upload frontend dist ---")
            remote_web = f"{LIVE}/web/dist"
            run(client, f"rm -rf {remote_web} && mkdir -p {remote_web}", label="clean-dist")
            # Upload all files in dist
            for local_file in web_dist.rglob("*"):
                if local_file.is_file():
                    rel = local_file.relative_to(web_dist)
                    remote_path = f"{remote_web}/{rel.as_posix()}"
                    remote_dir = os.path.dirname(remote_path)
                    try:
                        sftp.stat(remote_dir)
                    except FileNotFoundError:
                        run(client, f"mkdir -p {remote_dir}", label="mkdir")
                    sftp.put(str(local_file), remote_path)
            print(f"  Uploaded dist/ ({sum(1 for _ in web_dist.rglob('*') if _.is_file())} files)")
        print()

        # 6. Restart gateway
        print("--- Step 6: Restart gateway ---")
        run(client, "supervisorctl restart gateway || systemctl restart gateway", label="restart-gw")
        time.sleep(2)
        print()

        # 7. Final verification
        print("--- Step 7: Final verification ---")
        rc, out, _ = run(client, "curl -s http://localhost:8080/api/v1/hermes/health", label="gw-health")
        print(f"    Gateway->Bridge: {out[:200]}")
        rc, out, _ = run(client, "curl -s http://localhost:8002/api/v2/roles | python3 -c \"import sys,json; d=json.load(sys.stdin); print(f'Roles: {d.get(\\\"count\\\", len(d.get(\\\"roles\\\",[])))}'  )\"", label="roles")
        print(f"    {out}")
        print()

        print("=== Deployment complete ===")
        return 0
    finally:
        sftp.close()
        client.close()


if __name__ == "__main__":
    sys.exit(main())
