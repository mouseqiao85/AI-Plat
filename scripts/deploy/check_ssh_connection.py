"""Preflight check for Paramiko deployment SSH configuration.

This verifies that local DEPLOY_* / PARAMIKO_* environment variables can create
an SSH session and run a harmless remote command without printing secrets.
"""
from __future__ import annotations

import sys

from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, run_remote


def main() -> int:
    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
    except DeployConfigError as exc:
        print(f"[FAIL] Invalid SSH config: {exc}", file=sys.stderr)
        print("Set DEPLOY_PASS/PARAMIKO_PASSWORD or DEPLOY_KEY_FILE/PARAMIKO_KEY_FILE locally.", file=sys.stderr)
        return 2

    print(f"[preflight] target={config.endpoint} auth={config.auth_method} timeout={config.timeout}s")

    try:
        client = connect(config)
    except DeployConnectionError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 3

    try:
        rc, out, err = run_remote(
            client,
            "printf 'ssh-ok user=%s host=%s\\n' \"$(whoami)\" \"$(hostname)\"",
            timeout=config.command_timeout,
            label="ssh-preflight",
            print_output=False,
            secrets=[config.password or ""],
        )
        if rc != 0:
            print(f"[FAIL] Remote preflight command failed with exit={rc}", file=sys.stderr)
            if err.strip():
                print(err.strip(), file=sys.stderr)
            return 4
        print(f"[OK] {out.strip()}")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
