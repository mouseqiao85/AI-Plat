"""Monitor server logs via Paramiko — polls every 2s, prints new lines with [tag] prefix."""
from __future__ import annotations

import sys
import time
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "deploy"))
from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, redact_text  # noqa: E402

LOGS = {
    "gateway": "/home/admin/agent-platform/logs/gateway.log",
    "agent": "/home/admin/agent-platform/logs/agent.log",
    "bridge": "/var/log/hermes-bridge.log",
}

# Each log gets a ring buffer of last-seen line hashes to avoid re-printing
ring: dict[str, deque] = {tag: deque(maxlen=200) for tag in LOGS}
RUN_SECRETS: list[str] = []


def main() -> int:
    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        RUN_SECRETS[:] = [config.password or ""]
        print(f"[monitor] connecting to {config.endpoint} via {config.auth_method} auth...", flush=True)
        client = connect(config)
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"[monitor] SSH setup failed: {exc}", file=sys.stderr, flush=True)
        print("[monitor] Set DEPLOY_PASS or DEPLOY_KEY_FILE locally; see .env.example.", file=sys.stderr, flush=True)
        return 1

    print("[monitor] connected — monitoring gateway | agent | bridge", flush=True)
    transient_errors = 0

    try:
        while True:
            for tag, path in LOGS.items():
                try:
                    _, stdout, _ = client.exec_command(f"tail -n 30 {path} 2>/dev/null", timeout=5)
                    lines = stdout.read().decode("utf-8", "replace").rstrip().split("\n")
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        h = hash(line)
                        if h not in ring[tag]:
                            ring[tag].append(h)
                            print(f"[{tag}] {redact_text(line, RUN_SECRETS)}", flush=True)
                except Exception as exc:
                    transient_errors += 1
                    if transient_errors % 30 == 1:
                        print(f"[monitor] transient read error for {tag}: {redact_text(str(exc), RUN_SECRETS)}", file=sys.stderr, flush=True)
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        client.close()
        print("[monitor] stopped.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
