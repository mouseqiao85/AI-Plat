"""Deploy env-override patch: upload config.go, rebuild on server, restart with env."""
from __future__ import annotations

import sys
import time

from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, run_remote

REMOTE_ROOT = "/home/admin/agent-platform"
LOCAL_ROOT = r"C:\Projects\agent-platform"
RUN_SECRETS: list[str] = []


def run(client, cmd, tmo=120):
    return run_remote(client, cmd, timeout=tmo, secrets=RUN_SECRETS, max_output_chars=800)


def main() -> int:
    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        RUN_SECRETS[:] = [config.password or ""]
        print(f"=== Connecting to {config.endpoint} via {config.auth_method} auth ===")
        c = connect(config)
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        print("Set DEPLOY_PASS or DEPLOY_KEY_FILE locally; see .env.example for DEPLOY_* variables.", file=sys.stderr)
        return 1

    try:
        # 1. Upload patched config.go
        sftp = c.open_sftp()
        try:
            src = LOCAL_ROOT + r"\pkg\config\config.go"
            dst = REMOTE_ROOT + "/pkg/config/config.go"
            print(f"SFTP: {src} -> {dst}")
            sftp.put(src, dst)
        finally:
            sftp.close()

        # 2. Backup old binary, rebuild
        run(c, f"cp -a {REMOTE_ROOT}/build/agent-gateway {REMOTE_ROOT}/build/agent-gateway.bak-envfix-$(date +%Y%m%d-%H%M%S)")
        print("=== building on server ===")
        rc, _, _ = run(
            c,
            f"cd {REMOTE_ROOT} && go build -buildvcs=false -o build/agent-gateway-envfix ./cmd/gateway",
            tmo=240,
        )
        if rc != 0:
            print("!!! build FAILED, aborting")
            return 2

        run(c, f"md5sum {REMOTE_ROOT}/build/agent-gateway {REMOTE_ROOT}/build/agent-gateway-envfix")

        # 3. Revert config.yaml hermes back to localhost (clean default) — env will drive prod
        run(
            c,
            "sed -i '/^hermes:/,/^[a-z]/ "
            "s|service_url: http://172.19.30.12:8002|service_url: http://localhost:8002|' "
            f"{REMOTE_ROOT}/configs/config.yaml",
        )
        run(c, f"grep -n service_url {REMOTE_ROOT}/configs/config.yaml")

        # 4. Swap binary + restart with env vars
        run(c, "fuser -k -KILL 8080/tcp 2>&1 || true")
        time.sleep(2)
        run(c, f"mv {REMOTE_ROOT}/build/agent-gateway-envfix {REMOTE_ROOT}/build/agent-gateway")
        run(c, f"md5sum {REMOTE_ROOT}/build/agent-gateway")

        # start with BOTH env vars (agent on loopback, bridge on internal IP)
        gw = (
            f"cd {REMOTE_ROOT} && "
            "( GATEWAY_HOST=0.0.0.0 "
            "AGENT_SERVICE_URL=http://127.0.0.1:8001 "
            "HERMES_SERVICE_URL=http://172.19.30.12:8002 "
            "nohup ./build/agent-gateway --config configs/config.yaml "
            ">> logs/gateway.log 2>&1 < /dev/null & ) && echo spawned"
        )
        run(c, gw)
        time.sleep(5)

        # 5. verify running, inspect env names without printing raw values
        run(c, "pgrep -fa 'agent-gateway --config' || echo NOT-RUNNING")
        run(c, "NEWPID=$(pgrep -f 'build/agent-gateway --config' | head -1); "
               "cat /proc/$NEWPID/environ 2>/dev/null | tr '\\0' '\\n' | "
               "grep -E '^(GATEWAY_HOST|AGENT_SERVICE_URL|HERMES_SERVICE_URL)=' | sed 's/=.*$/=<set>/'")

        run(c, "ss -tlnp | grep ':8080'")
        run(c, "tail -8 /home/admin/agent-platform/logs/gateway.log")

        # 6. sanity smoke: hit a hermes route through gateway; 401 expected (auth required) means wired up
        run(c, "curl -fsS -o /dev/null -w 'http=%{http_code}\\n' --max-time 3 "
               "http://127.0.0.1:8080/api/v1/hermes/skills || true")

        print("=== env-driven config rollout DONE ===")
        return 0
    finally:
        c.close()


if __name__ == "__main__":
    sys.exit(main())
