"""Deploy zip entry name recovery and repair already imported node paths."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from ssh_config import DeployConfigError, DeployConnectionError, RemoteCommandError, connect, load_deploy_config, run_remote


LOCAL_ROOT = Path(__file__).resolve().parents[2]
LIVE = "/home/admin/agent-platform"


def run(client, command: str, *, label: str, timeout: int = 120, check: bool = False, secrets: list[str] | None = None):
    return run_remote(
        client,
        command,
        timeout=timeout,
        label=label,
        check=check,
        secrets=secrets or [],
    )


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
            rel = "agent/app/knowledge/obsidian_importer.py"
            remote = f"{LIVE}/{rel}"
            print(f"[put] {rel} -> {remote}")
            sftp.put(str(LOCAL_ROOT / rel), remote)
        finally:
            sftp.close()

        run(
            client,
            f"cd {LIVE}/agent && ./.venv/bin/python -m py_compile app/knowledge/obsidian_importer.py",
            label="remote-py-compile",
            check=True,
            secrets=secrets,
        )
        run(
            client,
            f"cd {LIVE}/agent && ./.venv/bin/python - <<'PY'\n"
            "import asyncio\n"
            "from pathlib import PurePosixPath\n"
            "from app.core.database import async_session_factory\n"
            "from app.knowledge.obsidian_importer import _recover_zip_name, _obsidian_uri\n"
            "from app.models.knowledge_graph import KnowledgeNode, KnowledgeSource\n"
            "from sqlalchemy import select\n"
            "\n"
            "def recover(value):\n"
            "    if not value:\n"
            "        return value\n"
            "    return '/'.join(_recover_zip_name(part, utf8_flag=False) for part in str(value).split('/'))\n"
            "\n"
            "async def main():\n"
            "    changed = 0\n"
            "    async with async_session_factory() as session:\n"
            "        source_result = await session.execute(select(KnowledgeSource))\n"
            "        sources = {source.id: source for source in source_result.scalars().all()}\n"
            "        node_result = await session.execute(select(KnowledgeNode))\n"
            "        for node in node_result.scalars().all():\n"
            "            before = (node.key, node.title, node.path, node.uri, repr(node.properties_json))\n"
            "            if node.key:\n"
            "                node.key = recover(node.key)\n"
            "            if node.path:\n"
            "                node.path = recover(node.path)\n"
            "            if node.node_type == 'folder':\n"
            "                node.title = 'Vault Root' if node.key == '/' else PurePosixPath(node.key).name\n"
            "            else:\n"
            "                node.title = recover(node.title)\n"
            "            props = dict(node.properties_json or {})\n"
            "            if 'folder_path' in props:\n"
            "                props['folder_path'] = recover(props['folder_path'])\n"
            "            node.properties_json = props\n"
            "            source = sources.get(node.source_id)\n"
            "            if node.node_type == 'note' and source and node.path:\n"
            "                node.uri = _obsidian_uri(source.name, node.path)\n"
            "            after = (node.key, node.title, node.path, node.uri, repr(node.properties_json))\n"
            "            if before != after:\n"
            "                changed += 1\n"
            "        await session.commit()\n"
            "    print(f'repaired_nodes={changed}')\n"
            "\n"
            "asyncio.run(main())\n"
            "PY",
            label="repair-existing-nodes",
            timeout=240,
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
        run(
            client,
            "curl -fsS --max-time 8 'http://127.0.0.1:8001/api/v1/knowledge-graph/nodes?node_type=folder&limit=20' "
            "| python3 -c 'import sys; print(sys.stdin.read().encode(\"unicode_escape\").decode())'",
            label="folder-nodes",
            timeout=60,
            check=True,
            secrets=secrets,
        )
        print("=== ZIP NAME ENCODING FIX DEPLOYED ===")
        return 0
    except RemoteCommandError as exc:
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
