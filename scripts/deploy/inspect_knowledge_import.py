"""Inspect remote knowledge graph import failures."""
from __future__ import annotations

import sys

from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, run_remote


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
                "agent-log-errors",
                "tail -240 /home/admin/agent-platform/logs/agent.log | "
                "grep -iE 'knowledge|obsidian|traceback|error|exception|multipart|sqlite|folder|node_type' -C 4 "
                "|| tail -120 /home/admin/agent-platform/logs/agent.log",
            ),
            (
                "gateway-log-errors",
                "tail -160 /home/admin/agent-platform/logs/gateway.log | "
                "grep -iE 'knowledge|error|badgateway|500' -C 4 || tail -80 /home/admin/agent-platform/logs/gateway.log",
            ),
            ("kg-stats", "curl -sS --max-time 8 http://127.0.0.1:8001/api/v1/knowledge-graph/stats 2>&1"),
            (
                "kg-openapi",
                "python3 - <<'PY'\n"
                "import json, urllib.request\n"
                "data=json.load(urllib.request.urlopen('http://127.0.0.1:8001/openapi.json', timeout=8))\n"
                "print('\\n'.join(p for p in sorted(data.get('paths', {})) if 'knowledge-graph' in p))\n"
                "PY",
            ),
            (
                "kg-db-tables",
                "cd /home/admin/agent-platform/agent && ./.venv/bin/python - <<'PY'\n"
                "import asyncio\n"
                "from app.core.database import engine\n"
                "async def main():\n"
                "    async with engine.begin() as conn:\n"
                "        rows = await conn.exec_driver_sql(\"select name from sqlite_master where type='table' and name like 'knowledge_%' order by name\")\n"
                "        print([r[0] for r in rows.fetchall()])\n"
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
