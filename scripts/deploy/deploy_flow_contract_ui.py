"""Deploy flow contract UI and flow_spec preservation to the live server."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from ssh_config import (
    DeployConfigError,
    DeployConnectionError,
    RemoteCommandError,
    connect,
    load_deploy_config,
    run_remote,
)


LOCAL_ROOT = Path(__file__).resolve().parents[2]
LIVE = "/home/admin/agent-platform"
BRIDGE_FILES = [
    "hermes-bridge/bridge/flows.py",
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


def upload_text_files(client) -> None:
    sftp = client.open_sftp()
    try:
        for rel in BRIDGE_FILES:
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
        run(client, f"mkdir -p {LIVE}/web/dist", label="mkdir-dist", timeout=60, print_output=False)
        for item in dist.rglob("*"):
            rel = item.relative_to(dist).as_posix()
            remote = f"{LIVE}/web/dist/{rel}"
            if item.is_dir():
                run(client, f"mkdir -p '{remote}'", label="mkdir-dist-dir", timeout=60, print_output=False)
                continue
            run(client, f"mkdir -p '{remote.rsplit('/', 1)[0]}'", label="mkdir-dist-file", timeout=60, print_output=False)
            with sftp.file(remote, "wb") as remote_file:
                remote_file.write(item.read_bytes())
            print(f"[put] web/dist/{rel}")
    finally:
        sftp.close()


def restart_hermes(client) -> None:
    run(client, "pkill -9 -f 'hermes-bridge/main.py' || true", label="stop-hermes-main", timeout=30, print_output=False)
    run(client, "pkill -9 -f 'hermes-bridge.*main.py' || true", label="stop-hermes-wrapper", timeout=30, print_output=False)
    time.sleep(2)
    client.exec_command(
        f"cd {LIVE}/hermes-bridge; nohup env PYTHONPATH={LIVE}/hermes-bridge "
        f"PYTHONUNBUFFERED=1 GSTACK_AUTOLOAD=1 {LIVE}/agent/.venv/bin/python main.py "
        "> /tmp/hermes-bridge.log 2>&1 < /dev/null &",
        timeout=5,
    )
    time.sleep(8)


def smoke_test_flow_contracts(client) -> None:
    payload = {
        "name": f"flow-contract-smoke-{int(time.time())}",
        "flow_type": "dag",
        "role_ids": ["review"],
        "description": "Temporary flow contract smoke test",
        "flow_spec": {
            "nodes": [{"id": "review", "type": "role", "role_id": "review", "label": "Review"}],
            "edges": [],
            "role_contracts": {
                "review": {
                    "stance_name": "Risk reviewer",
                    "must_challenge": "unsupported assumptions",
                    "output_schema": ["Position", "Evidence"],
                }
            },
            "adjudication": {
                "decision_rule": "prefer evidence-backed conclusions",
                "rubric": ["Evidence", "Risk"],
                "required_output_sections": ["Decision", "Score matrix"],
            },
        },
    }
    raw = json.dumps(payload, ensure_ascii=False).replace("'", "'\"'\"'")
    _, out, _ = run(
        client,
        "curl -fsS --max-time 15 -X POST http://127.0.0.1:8002/api/v2/flows "
        "-H 'Content-Type: application/json' "
        f"-d '{raw}'",
        label="create-flow-contract-smoke",
        timeout=30,
        check=True,
        print_output=False,
    )
    data = json.loads(out)
    flow_id = data["id"]
    spec = data.get("flow_spec", {})
    try:
        assert spec.get("role_contracts", {}).get("review", {}).get("stance_name") == "Risk reviewer"
        assert spec.get("adjudication", {}).get("rubric") == ["Evidence", "Risk"]
        print(f"[ok] flow contract smoke flow {flow_id} preserved collaboration spec")
    finally:
        run(
            client,
            f"curl -fsS --max-time 10 -X DELETE http://127.0.0.1:8002/api/v2/flows/{flow_id}",
            label="delete-flow-contract-smoke",
            timeout=30,
            check=True,
            print_output=False,
        )


def main() -> int:
    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        print(f"=== Connecting to {config.endpoint} via {config.auth_method} auth ===")
        client = connect(config)
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1

    try:
        ts = time.strftime("%Y%m%d-%H%M%S")
        print("=== Backup current runtime files ===")
        run(
            client,
            f"mkdir -p /home/admin/backups && "
            f"tar -czf /home/admin/backups/flow-contract-ui-{ts}.tar.gz "
            f"-C {LIVE} hermes-bridge/bridge/flows.py web/dist 2>&1 | tail -5",
            label="backup",
            timeout=120,
            check=True,
        )

        print("=== Upload bridge patch ===")
        upload_text_files(client)

        print("=== Upload frontend dist ===")
        upload_dist(client)

        print("=== Restart Hermes Bridge ===")
        restart_hermes(client)

        print("=== Verify runtime ===")
        run(
            client,
            f"cd {LIVE}/hermes-bridge && {LIVE}/agent/.venv/bin/python -m py_compile bridge/flows.py",
            label="py-compile",
            timeout=60,
            check=True,
        )
        run(client, "curl -fsS --max-time 8 http://127.0.0.1:8002/api/v2/health", label="hermes-health", timeout=30, check=True)
        run(client, "ss -tlnp | grep ':8002'", label="port-8002", timeout=30, check=True)

        print("=== Flow contract API smoke test ===")
        smoke_test_flow_contracts(client)

        print("=== Verify frontend asset ===")
        run(
            client,
            f"grep -R \"协作约束\\|role_contracts\\|裁决规则\" -n {LIVE}/web/dist/assets | head -5",
            label="frontend-contract-asset",
            timeout=30,
            check=True,
        )
        print("=== FLOW CONTRACT UI DEPLOYMENT COMPLETE ===")
        print(f"Backup: /home/admin/backups/flow-contract-ui-{ts}.tar.gz")
        return 0
    except (AssertionError, FileNotFoundError, RuntimeError, RemoteCommandError, json.JSONDecodeError) as exc:
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
