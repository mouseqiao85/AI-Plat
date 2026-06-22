"""Deploy knowledge source deletion support and verify it remotely."""
from __future__ import annotations

import io
import json
import sys
import time
import zipfile
from pathlib import Path

from ssh_config import DeployConfigError, DeployConnectionError, RemoteCommandError, connect, load_deploy_config, run_remote


LOCAL_ROOT = Path(__file__).resolve().parents[2]
LIVE = "/home/admin/agent-platform"
FILES = [
    "agent/app/api/knowledge_graph_routes.py",
    "agent/app/knowledge/schemas.py",
    "agent/app/knowledge/service.py",
    "web/src/types/index.ts",
    "web/src/services/api.ts",
    "web/src/components/KnowledgeGraphPage.tsx",
    "web/src/index.css",
]


def run(client, command: str, *, label: str, timeout: int = 120, check: bool = False, secrets: list[str] | None = None):
    return run_remote(
        client,
        command,
        timeout=timeout,
        label=label,
        check=check,
        secrets=secrets or [],
    )


def build_test_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("DeleteTest.md", "# Delete Test\n[[Target]]\n#delete-test")
        zf.writestr("Target.md", "# Target\n")
    return buf.getvalue()


def upload_file(sftp, client, rel: str, secrets: list[str]) -> None:
    local = LOCAL_ROOT / rel
    remote = f"{LIVE}/{rel.replace('\\', '/')}"
    run(client, f"mkdir -p {'/'.join(remote.split('/')[:-1])}", label="mkdir", check=True, secrets=secrets)
    print(f"[put] {rel} -> {remote}")
    sftp.put(str(local), remote)


def upload_dist(sftp, client, secrets: list[str]) -> None:
    dist = LOCAL_ROOT / "web" / "dist"
    for path in dist.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(LOCAL_ROOT).as_posix()
        remote = f"{LIVE}/{rel}"
        run(client, f"mkdir -p {'/'.join(remote.split('/')[:-1])}", label="mkdir-dist", check=True, secrets=secrets)
        print(f"[put] {rel} -> {remote}")
        sftp.put(str(path), remote)


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
        sftp = client.open_sftp()
        try:
            for rel in FILES:
                upload_file(sftp, client, rel, secrets)
            upload_dist(sftp, client, secrets)
            with sftp.file("/tmp/kg-delete-test.zip", "wb") as handle:
                handle.write(build_test_zip())
        finally:
            sftp.close()

        run(
            client,
            f"cd {LIVE}/agent && ./.venv/bin/python -m py_compile app/api/knowledge_graph_routes.py app/knowledge/schemas.py app/knowledge/service.py",
            label="remote-py-compile",
            check=True,
            secrets=secrets,
        )
        run(
            client,
            f"cd {LIVE} && go build -o build/agent-gateway-new ./cmd/gateway && cp -f build/agent-gateway-new build/agent-gateway && chmod +x build/agent-gateway",
            label="go-build-gateway",
            timeout=360,
            check=True,
            secrets=secrets,
        )
        run(client, "fuser -k 8080/tcp 2>/dev/null || true", label="stop-gateway", timeout=60, secrets=secrets)
        run(client, "fuser -k 8001/tcp 2>/dev/null || true", label="stop-agent", timeout=60, secrets=secrets)
        time.sleep(2)
        client.exec_command(
            f"cd {LIVE}; nohup env GATEWAY_HOST=0.0.0.0 ./build/agent-gateway --config configs/config.yaml > logs/gateway.log 2>&1 < /dev/null &",
            timeout=5,
        )
        client.exec_command(
            f"cd {LIVE}/agent; nohup env PYTHONUNBUFFERED=1 ./.venv/bin/python main.py > ../logs/agent.log 2>&1 < /dev/null &",
            timeout=5,
        )
        client.close()
        time.sleep(8)

        client = connect(config)
        run(client, "curl -fsS --max-time 5 http://127.0.0.1:8080/api/v1/health", label="gateway-health", check=True, secrets=secrets)
        run(client, "curl -fsS --max-time 5 http://127.0.0.1:8001/health", label="agent-health", check=True, secrets=secrets)
        rc, out, _ = run(
            client,
            "curl -sS --max-time 30 -X POST "
            "-F source_name=DeleteRegression "
            "-F file=@/tmp/kg-delete-test.zip "
            "http://127.0.0.1:8001/api/v1/knowledge-graph/import/obsidian",
            label="import-delete-test",
            timeout=60,
            check=True,
            secrets=secrets,
        )
        imported = json.loads(out)
        source_id = int(imported["source_id"])
        rc, out, _ = run(
            client,
            f"curl -sS --max-time 10 -X DELETE http://127.0.0.1:8001/api/v1/knowledge-graph/sources/{source_id}",
            label="delete-source-agent",
            timeout=30,
            check=True,
            secrets=secrets,
        )
        deleted = json.loads(out)
        if not deleted.get("deleted") or deleted.get("source_id") != source_id:
            raise RuntimeError(f"unexpected delete response: {deleted}")
        run(
            client,
            f"curl -sS --max-time 10 -X DELETE http://127.0.0.1:8001/api/v1/knowledge-graph/sources/{source_id} -w '\\nHTTP:%{{http_code}}\\n'",
            label="delete-source-missing-agent",
            timeout=30,
            secrets=secrets,
        )
        run(
            client,
            "curl -fsS --max-time 8 http://127.0.0.1:8080/api/v1/knowledge-graph/stats",
            label="gateway-kg-stats",
            check=True,
            secrets=secrets,
        )
        run(
            client,
            f"grep -o 'KnowledgeGraphPage[^\" ]*' {LIVE}/web/dist/index.html {LIVE}/web/dist/assets/*.js 2>/dev/null | head -5 || true",
            label="frontend-delete-build",
            secrets=secrets,
        )
        print("=== KNOWLEDGE SOURCE DELETE DEPLOYED ===")
        return 0
    except (RemoteCommandError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        run(client, f"tail -120 {LIVE}/logs/agent.log 2>&1 || true", label="agent-log", timeout=30)
        run(client, f"tail -120 {LIVE}/logs/gateway.log 2>&1 || true", label="gateway-log", timeout=30)
        return 2
    finally:
        try:
            client.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
