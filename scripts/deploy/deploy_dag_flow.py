"""Deploy DAG flow support for Hermes and the frontend bundle."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from ssh_config import DeployConfigError, DeployConnectionError, RemoteCommandError, connect, load_deploy_config, run_remote


LOCAL_ROOT = Path(__file__).resolve().parents[2]
LIVE = "/home/admin/agent-platform"

TEXT_FILES = [
    "hermes-bridge/bridge/db.py",
    "hermes-bridge/bridge/flows.py",
    "hermes-bridge/bridge/orchestrator.py",
]


def run(client, command: str, *, label: str, timeout: int = 120, check: bool = False, print_output: bool = True):
    return run_remote(
        client,
        command,
        timeout=timeout,
        label=label,
        check=check,
        print_output=print_output,
    )


def fire_and_forget(client, command: str) -> None:
    client.exec_command(command, timeout=5)


def upload_text_files(client) -> None:
    sftp = client.open_sftp()
    try:
        for rel in TEXT_FILES:
            local = LOCAL_ROOT / rel
            remote = f"{LIVE}/{rel}"
            if not local.exists():
                raise FileNotFoundError(local)
            run(client, f"mkdir -p '{remote.rsplit('/', 1)[0]}'", label="mkdir", timeout=60, print_output=False)
            text = local.read_text(encoding="utf-8").replace("\r\n", "\n")
            with sftp.file(remote, "wb") as remote_file:
                remote_file.write(text.encode("utf-8"))
            print(f"[put] {rel}")
    finally:
        sftp.close()


def upload_dist(client) -> None:
    dist = LOCAL_ROOT / "web" / "dist"
    if not (dist / "index.html").exists():
        raise RuntimeError("web/dist/index.html is missing; run npm --prefix web run build first")

    sftp = client.open_sftp()
    try:
        for item in dist.rglob("*"):
            rel = item.relative_to(dist).as_posix()
            remote = f"{LIVE}/web/dist/{rel}"
            if item.is_dir():
                run(client, f"mkdir -p '{remote}'", label="mkdir-dist", timeout=60, print_output=False)
                continue
            run(client, f"mkdir -p '{remote.rsplit('/', 1)[0]}'", label="mkdir-dist-file", timeout=60, print_output=False)
            with sftp.file(remote, "wb") as remote_file:
                remote_file.write(item.read_bytes())
            print(f"[put] web/dist/{rel}")
    finally:
        sftp.close()


def smoke_test_dag_api(client) -> None:
    payload = {
        "name": f"dag-smoke-{int(time.time())}",
        "flow_type": "dag",
        "role_ids": ["autoplan", "review"],
        "description": "Temporary DAG smoke test flow",
        "flow_spec": {
            "nodes": [
                {"id": "plan", "role_id": "autoplan", "label": "Plan"},
                {"id": "review", "role_id": "review", "label": "Review"},
            ],
            "edges": [{"from": "plan", "to": "review"}],
        },
    }
    raw = json.dumps(payload, ensure_ascii=False).replace("'", "'\"'\"'")
    cmd = (
        "curl -fsS --max-time 15 -X POST http://127.0.0.1:8002/api/v2/flows "
        "-H 'Content-Type: application/json' "
        f"-d '{raw}'"
    )
    _, out, _ = run(client, cmd, label="create-dag-flow", timeout=30, check=True, print_output=False)
    data = json.loads(out)
    if data.get("flow_type") != "dag" or data.get("flow_spec", {}).get("edges", [{}])[0].get("from") != "plan":
        raise RuntimeError(f"unexpected dag flow response: {data}")
    flow_id = data["id"]
    print(f"[ok] created dag flow {flow_id}")
    run(client, f"curl -fsS --max-time 10 -X DELETE http://127.0.0.1:8002/api/v2/flows/{flow_id}", label="delete-dag-flow", timeout=30, check=True, print_output=False)
    print(f"[ok] deleted dag flow {flow_id}")


def main() -> int:
    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        print(f"=== Connecting to {config.endpoint} via {config.auth_method} auth ===")
        client = connect(config)
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1

    try:
        print("=== Upload Hermes DAG files ===")
        upload_text_files(client)

        print("=== Upload frontend dist ===")
        upload_dist(client)

        print("=== Restart Hermes with live Python venv ===")
        run(client, "fuser -k 8002/tcp 2>/dev/null || true", label="stop-hermes", timeout=30, print_output=False)
        time.sleep(2)
        fire_and_forget(
            client,
            f"cd {LIVE}/hermes-bridge; nohup env PYTHONPATH={LIVE}/hermes-bridge "
            f"PYTHONUNBUFFERED=1 GSTACK_AUTOLOAD=1 {LIVE}/agent/.venv/bin/python main.py "
            "> /tmp/hermes-bridge.log 2>&1 < /dev/null &",
        )
        time.sleep(8)

        print("=== Verify runtime ===")
        run(client, f"cd {LIVE}/hermes-bridge && {LIVE}/agent/.venv/bin/python -m py_compile bridge/db.py bridge/flows.py bridge/orchestrator.py", label="py-compile", timeout=60, check=True)
        run(client, "curl -fsS --max-time 8 http://127.0.0.1:8002/api/v2/health", label="hermes-health", timeout=30, check=True)
        run(client, "ss -tlnp | grep ':8002'", label="port-8002", timeout=30, check=True)

        print("=== DAG API smoke test ===")
        smoke_test_dag_api(client)

        print("=== Verify frontend asset ===")
        run(client, f"grep -R \"DAG edges\" -n {LIVE}/web/dist/assets | head -3", label="frontend-dag-asset", timeout=30, check=True)
        print("=== DAG DEPLOYMENT COMPLETE ===")
        return 0
    except (RemoteCommandError, RuntimeError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        try:
            run(client, "tail -120 /tmp/hermes-bridge.log 2>&1 || true", label="hermes-log", timeout=30)
        except Exception:
            pass
        return 2
    finally:
        try:
            client.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
