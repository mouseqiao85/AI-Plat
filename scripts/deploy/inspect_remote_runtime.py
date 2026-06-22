"""Inspect the remote agent-platform runtime before deployment."""
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
        print(f"=== Inspecting {config.endpoint} via {config.auth_method} auth ===")
        commands = [
            ("host", "whoami && hostname && pwd"),
            ("live-dir", f"test -d {LIVE} && ls -la {LIVE} | head -30 || echo live-dir-missing"),
            ("ports", "ss -tlnp | grep -E ':8080|:8001|:8002' || true"),
            ("processes", "pgrep -fa 'agent-gateway|agent/.venv|hermes-bridge.*main.py' || true"),
            ("health-gateway", "curl -fsS --max-time 5 http://127.0.0.1:8080/api/v1/health 2>&1 || true"),
            ("health-agent", "curl -fsS --max-time 5 http://127.0.0.1:8001/health 2>&1 || true"),
            ("agent-venv", f"test -x {LIVE}/agent/.venv/bin/python && {LIVE}/agent/.venv/bin/python --version || true"),
            ("go-version", "go version || true"),
            ("disk", "df -h /home/admin | tail -1"),
            ("config-agent-url", f"grep -n 'service_url\\|serviceURL\\|agent' {LIVE}/configs/config.yaml | head -20 || true"),
        ]
        for label, command in commands:
            run_remote(
                client,
                command,
                timeout=config.command_timeout,
                label=label,
                secrets=secrets,
            )
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
