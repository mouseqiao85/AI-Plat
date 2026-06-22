"""Deploy the Obsidian import JSON-safe frontmatter fix and verify it."""
from __future__ import annotations

import io
import json
import sys
import time
import zipfile
from pathlib import Path

from ssh_config import DeployConfigError, DeployConnectionError, RemoteCommandError, connect, load_deploy_config, run_remote


LOCAL_ROOT = Path(__file__).resolve().parents[2]
LIVE = "/home/admin/agent-platform"
FILES = [
    "agent/app/knowledge/obsidian_importer.py",
    "agent/app/knowledge/service.py",
]


def run(client, command: str, *, label: str, timeout: int = 120, check: bool = False, secrets: list[str] | None = None):
    return run_remote(
        client,
        command,
        timeout=timeout,
        label=label,
        check=check,
        secrets=secrets or [],
    )


def build_test_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "Dated.md",
            """---
title: Dated Note
created: 2026-06-05
review:
  due: 2026-06-06
tags: [deploy-test]
---
# Dated Note
Linked to [[Target]].
""",
        )
        zf.writestr("Target.md", "# Target\n")
    return buf.getvalue()


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
        sftp = client.open_sftp()
        try:
            for rel in FILES:
                local = LOCAL_ROOT / rel
                remote = f"{LIVE}/{rel}"
                run(client, f"mkdir -p {'/'.join(remote.split('/')[:-1])}", label="mkdir", check=True, secrets=secrets)
                print(f"[put] {rel} -> {remote}")
                sftp.put(str(local), remote)
            test_remote = "/tmp/kg-dated-vault.zip"
            with sftp.file(test_remote, "wb") as handle:
                handle.write(build_test_zip())
        finally:
            sftp.close()

        run(
            client,
            f"cd {LIVE}/agent && ./.venv/bin/python -m py_compile app/knowledge/obsidian_importer.py app/knowledge/service.py",
            label="remote-py-compile",
            check=True,
            secrets=secrets,
        )
        run(client, "fuser -k 8001/tcp 2>/dev/null || true", label="stop-agent", timeout=60, secrets=secrets)
        time.sleep(2)
        client.exec_command(
            f"cd {LIVE}/agent; nohup env PYTHONUNBUFFERED=1 ./.venv/bin/python main.py > ../logs/agent.log 2>&1 < /dev/null &",
            timeout=5,
        )
        client.close()
        time.sleep(8)

        client = connect(config)
        run(client, "curl -fsS --max-time 5 http://127.0.0.1:8001/health", label="agent-health", check=True, secrets=secrets)
        rc, out, _ = run(
            client,
            "curl -sS --max-time 30 -X POST "
            "-F source_name=DeployDateRegression "
            "-F file=@/tmp/kg-dated-vault.zip "
            "http://127.0.0.1:8001/api/v1/knowledge-graph/import/obsidian",
            label="import-dated-vault",
            timeout=60,
            check=True,
            secrets=secrets,
        )
        data = json.loads(out)
        if data.get("status") != "completed" or data.get("stats", {}).get("notes") != 2:
            raise RuntimeError(f"unexpected import response: {data}")
        run(
            client,
            "curl -fsS --max-time 8 'http://127.0.0.1:8001/api/v1/knowledge-graph/nodes?q=Dated%20Note&node_type=note&limit=5'",
            label="query-dated-note",
            check=True,
            secrets=secrets,
        )
        print("=== KNOWLEDGE IMPORT FIX DEPLOYED ===")
        return 0
    except (RemoteCommandError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        run(client, f"tail -120 {LIVE}/logs/agent.log 2>&1 || true", label="agent-log", timeout=30)
        return 2
    finally:
        try:
            client.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
