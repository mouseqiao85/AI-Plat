"""Start live services without waiting on background shell stdout."""
from __future__ import annotations

import sys
import time

from ssh_config import DeployConfigError, DeployConnectionError, RemoteCommandError, connect, load_deploy_config, run_remote


LIVE = "/home/admin/agent-platform"


def fire_and_forget(client, command: str) -> None:
    client.exec_command(command, timeout=5)


def run(client, command: str, *, label: str, timeout: int = 60, check: bool = False, secrets: list[str] | None = None):
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
        run(client, f"mkdir -p {LIVE}/logs {LIVE}/agent/data", label="ensure-runtime-dirs", check=True, secrets=secrets)
        run(client, "fuser -k 8080/tcp 2>/dev/null || true", label="stop-gateway", timeout=30, secrets=secrets)
        run(client, "fuser -k 8001/tcp 2>/dev/null || true", label="stop-agent", timeout=30, secrets=secrets)
        run(client, "fuser -k 8002/tcp 2>/dev/null || true", label="stop-hermes", timeout=30, secrets=secrets)
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

        time.sleep(10)
        client = connect(config)
        checks = [
            ("ports", "ss -tlnp | grep -E ':8080|:8001|:8002'"),
            ("gateway-health", "curl -fsS --max-time 5 http://127.0.0.1:8080/api/v1/health"),
            ("agent-health", "curl -fsS --max-time 5 http://127.0.0.1:8001/health"),
            ("hermes-health", "curl -fsS --max-time 5 http://127.0.0.1:8002/api/v2/health"),
            ("kg-stats-agent", "curl -fsS --max-time 8 http://127.0.0.1:8001/api/v1/knowledge-graph/stats"),
            ("frontend-kg-asset", f"grep -o 'KnowledgeGraphPage[^\" ]*' {LIVE}/web/dist/index.html {LIVE}/web/dist/assets/*.js 2>/dev/null | head -5 || true"),
        ]
        for label, command in checks:
            run(client, command, label=label, timeout=60, check=True, secrets=secrets)

        print("=== LIVE SERVICES STARTED ===")
        return 0
    except RemoteCommandError as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        run(client, f"tail -100 {LIVE}/logs/gateway.log 2>&1 || true", label="gateway-log", timeout=30)
        run(client, f"tail -100 {LIVE}/logs/agent.log 2>&1 || true", label="agent-log", timeout=30)
        run(client, "tail -100 /tmp/hermes-bridge.log 2>&1 || true", label="hermes-log", timeout=30)
        return 2
    finally:
        try:
            client.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
