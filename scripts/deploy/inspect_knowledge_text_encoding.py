"""Inspect remote knowledge graph text for mojibake-like content."""
from __future__ import annotations

import sys

from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, run_remote


LIVE = "/home/admin/agent-platform"


def main() -> int:
    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        client = connect(config)
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1

    secrets = [config.password or ""]
    try:
        commands = [
            (
                "sources",
                "curl -fsS --max-time 8 http://127.0.0.1:8001/api/v1/knowledge-graph/sources "
                "| python3 -c 'import sys; print(sys.stdin.read().encode(\"unicode_escape\").decode())'",
            ),
            (
                "sample-nodes",
                "curl -fsS --max-time 8 'http://127.0.0.1:8001/api/v1/knowledge-graph/nodes?limit=25' "
                "| python3 -c 'import sys; print(sys.stdin.read().encode(\"unicode_escape\").decode())'",
            ),
            (
                "mojibake-scan-db",
                f"cd {LIVE}/agent && ./.venv/bin/python - <<'PY'\n"
                "import asyncio\n"
                "from app.core.database import async_session_factory\n"
                "from sqlalchemy import text\n"
                "patterns = ['鐭', '鍥', '鏂', '绗', '鈥', '銆', '瀹', '寰']\n"
                "async def main():\n"
                "    async with async_session_factory() as session:\n"
                "        rows = await session.execute(text('select id, node_type, title, path, content_preview from knowledge_nodes order by id desc limit 80'))\n"
                "        bad = []\n"
                "        for row in rows.fetchall():\n"
                "            blob = ' '.join(str(v or '') for v in row)\n"
                "            if any(p in blob for p in patterns):\n"
                "                bad.append(row)\n"
                "        print('mojibake_candidates=', len(bad))\n"
                "        for row in bad[:20]:\n"
                "            print(dict(row._mapping))\n"
                "asyncio.run(main())\n"
                "PY",
            ),
        ]
        for label, command in commands:
            run_remote(client, command, timeout=120, label=label, secrets=secrets)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
