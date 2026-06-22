"""Inspect remote Python virtualenv details needed by deployment."""
from __future__ import annotations

import sys

from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, run_remote


LIVE = "/home/admin/agent-platform"
STAGE = "/home/admin/agent-platform-stage"


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
            ("live-venv-bin", f"ls -la {LIVE}/agent/.venv/bin | grep -E 'pip|python' || true"),
            ("stage-venv-bin", f"ls -la {STAGE}/agent/.venv/bin | grep -E 'pip|python' || true"),
            ("live-pip-module", f"{LIVE}/agent/.venv/bin/python -m pip --version 2>&1 || true"),
            ("live-pip-bin", f"{LIVE}/agent/.venv/bin/pip --version 2>&1 || true"),
            ("ensurepip", f"{LIVE}/agent/.venv/bin/python -m ensurepip --version 2>&1 || true"),
            ("multipart-import", f"cd {STAGE}/agent && ./.venv/bin/python -c 'import multipart; print(multipart.__version__)' 2>&1 || true"),
            ("main-import", f"cd {STAGE}/agent && ./.venv/bin/python -c 'import main; print(\"main-import-ok\")' 2>&1 | tail -50 || true"),
        ]
        for label, command in commands:
            run_remote(client, command, timeout=config.command_timeout, label=label, secrets=secrets)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
