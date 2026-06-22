"""Deploy hermes-bridge multi-agent orchestrator additions to the live server.

Uploads the 6 new modules + 2 modified files to /home/admin/agent-platform/
hermes-bridge/, restarts the service, and verifies the new /api/v2 endpoints.

Files synced (relative to repo root):
  hermes-bridge/bridge/gstack_loader.py   [NEW]
  hermes-bridge/bridge/db.py              [NEW]
  hermes-bridge/bridge/scenarios.py       [NEW]
  hermes-bridge/bridge/flows.py           [NEW]
  hermes-bridge/bridge/runs.py            [NEW]
  hermes-bridge/bridge/orchestrator.py    [NEW]
  hermes-bridge/bridge/chat_handler.py    [MOD]
  hermes-bridge/main.py                   [MOD]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, run_remote

LIVE = "/home/admin/agent-platform"
LOCAL_ROOT = Path(r"C:\Projects\agent-platform")

FILES = [
    "hermes-bridge/bridge/gstack_loader.py",
    "hermes-bridge/bridge/db.py",
    "hermes-bridge/bridge/scenarios.py",
    "hermes-bridge/bridge/flows.py",
    "hermes-bridge/bridge/runs.py",
    "hermes-bridge/bridge/orchestrator.py",
    "hermes-bridge/bridge/chat_handler.py",
    "hermes-bridge/main.py",
]

RUN_SECRETS: list[str] = []


def run(client, cmd: str, timeout: int = 120, label: str = "") -> tuple[int, str, str]:
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
        print("=== Step 1: backup current hermes-bridge ===")
        ts = time.strftime("%Y%m%d-%H%M%S")
        run(
            client,
            f"mkdir -p /home/admin/backups && "
            f"tar -czf /home/admin/backups/hermes-bridge-{ts}.tar.gz "
            f"-C {LIVE} hermes-bridge 2>&1 | tail -5",
            timeout=120,
            label="tar-backup",
        )

        print("=== Step 2: ensure orchestrator data dir ===")
        run(client, "mkdir -p /root/.agent-platform && ls -la /root/.agent-platform/")

        print("=== Step 3: upload new + modified files ===")
        sftp = client.open_sftp()
        try:
            for rel in FILES:
                local = LOCAL_ROOT / rel
                remote = f"{LIVE}/{rel}"
                if not local.exists():
                    print(f"[FATAL] missing local file: {local}", file=sys.stderr)
                    return 2
                remote_dir = "/".join(remote.split("/")[:-1])
                run(client, f"mkdir -p {remote_dir}", label="mkdir")
                # Convert CRLF -> LF in transit by reading text and writing bytes.
                text = local.read_text(encoding="utf-8")
                with sftp.file(remote, "wb") as f:
                    f.write(text.replace("\r\n", "\n").encode("utf-8"))
                size = local.stat().st_size
                print(f"[put] {local.name} ({size}B) -> {remote}")
        finally:
            sftp.close()

        print("=== Step 4: install deps into hermes-bridge venv ===")
        run(
            client,
            f"{LIVE}/hermes-bridge/venv/bin/pip install -q pyyaml 2>&1 | tail -5",
            timeout=120,
            label="pip-install",
        )

        print("=== Step 5: restart hermes-bridge ===")
        # Kill both the parent bash wrapper and the python child.
        run(client, "pkill -9 -f 'hermes-bridge/main.py' || true")
        run(client, "pkill -9 -f 'hermes-bridge && source venv' || true")
        time.sleep(2)
        # Start in background; must bind to internal IP (existing config).
        run(
            client,
            f"nohup bash -c 'cd {LIVE}/hermes-bridge && source venv/bin/activate && python3 main.py' "
            f"> /var/log/hermes-bridge.log 2>&1 &",
            label="start",
        )
        time.sleep(6)
        run(client, "tail -50 /var/log/hermes-bridge.log")
        run(client, "ss -ltn 2>/dev/null | grep 8002 || echo 'PORT 8002 NOT LISTENING'")

        print("=== Step 6: verify /api/v2 endpoints ===")
        # hermes-bridge binds to 172.19.30.12:8002 (internal), not 127.0.0.1
        rc, out, _ = run(
            client,
            "curl -sS -m 10 http://172.19.30.12:8002/api/v2/health",
            label="health",
        )
        if rc != 0 or '"ok"' not in out:
            print("[FATAL] health check failed", file=sys.stderr)
            run(client, "tail -80 /var/log/hermes-bridge.log")
            return 3

        run(
            client,
            "curl -sS -m 30 http://172.19.30.12:8002/api/v2/roles | "
            "python3 -c 'import sys,json; d=json.load(sys.stdin); "
            "print(\"role count =\", d.get(\"count\")); "
            "print(\"first 3:\", [r[\"id\"] for r in d.get(\"roles\",[])[:3]])'",
            label="roles",
        )

        run(
            client,
            "curl -sS -m 10 http://172.19.30.12:8002/api/v2/scenarios | "
            "python3 -c 'import sys,json; d=json.load(sys.stdin); "
            "print(\"scenario count =\", len(d.get(\"scenarios\",[]))); "
            "print(\"ids:\", [s[\"id\"] for s in d.get(\"scenarios\",[])])'",
            label="scenarios",
        )

        run(
            client,
            "curl -sS -m 10 http://172.19.30.12:8002/api/v2/flows | head -c 500",
            label="flows-list",
        )

        print("=== Step 7: upload frontend dist ===")
        sftp = client.open_sftp()
        try:
            dist_local = LOCAL_ROOT / "web" / "dist"
            dist_remote = f"{LIVE}/web/dist"
            # Backup current index.html just in case
            run(client, f"cp {dist_remote}/index.html {dist_remote}/index.html.bak.{ts} 2>/dev/null || true")

            # Upload all files recursively
            def upload_tree(local_dir: Path, remote_dir: str):
                run(client, f"mkdir -p {remote_dir}", label="mkdir")
                for item in local_dir.iterdir():
                    if item.name.startswith(".") or item.name == "node_modules":
                        continue
                    rp = f"{remote_dir}/{item.name}"
                    if item.is_dir():
                        upload_tree(item, rp)
                    else:
                        data = item.read_bytes()
                        with sftp.file(rp, "wb") as f:
                            f.write(data)
                        print(f"[put] {item.name} ({len(data)}B)")

            upload_tree(dist_local, dist_remote)
        finally:
            sftp.close()
        run(client, f"ls -la {LIVE}/web/dist/ | head -15")
        run(client, f"ls -la {LIVE}/web/dist/assets/ | head -20")

        print("=== DEPLOYMENT COMPLETE ===")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
