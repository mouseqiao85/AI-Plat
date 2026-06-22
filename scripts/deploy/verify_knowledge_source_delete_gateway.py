"""Verify source deletion through the authenticated gateway route."""
from __future__ import annotations

import io
import sys
import zipfile

from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, run_remote


def build_test_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("GatewayDelete.md", "# Gateway Delete\n[[Target]]\n#gateway-delete")
        zf.writestr("Target.md", "# Target\n")
    return buf.getvalue()


def main() -> int:
    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        client = connect(config)
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1

    secrets = [config.password or ""]
    try:
        sftp = client.open_sftp()
        try:
            with sftp.file("/tmp/kg-gateway-delete.zip", "wb") as handle:
                handle.write(build_test_zip())
        finally:
            sftp.close()

        commands = [
            (
                "gateway-auth-stats",
                "TOKEN=$(curl -sS --max-time 10 -X POST http://127.0.0.1:8080/api/v1/auth/dev-login "
                "| python3 -c 'import sys,json; print(json.load(sys.stdin)[\"access_token\"])'); "
                'curl -fsS --max-time 8 -H "Authorization: Bearer $TOKEN" '
                "http://127.0.0.1:8080/api/v1/knowledge-graph/stats",
            ),
            (
                "import-for-gateway-delete",
                "curl -sS --max-time 30 -X POST -F source_name=GatewayDeleteRegression "
                "-F file=@/tmp/kg-gateway-delete.zip "
                "http://127.0.0.1:8001/api/v1/knowledge-graph/import/obsidian",
            ),
            (
                "gateway-delete",
                "SID=$(curl -sS --max-time 20 http://127.0.0.1:8001/api/v1/knowledge-graph/sources "
                "| python3 -c 'import sys,json; data=json.load(sys.stdin); "
                "print(next(s[\"id\"] for s in data if s[\"name\"]==\"GatewayDeleteRegression\"))'); "
                "TOKEN=$(curl -sS --max-time 10 -X POST http://127.0.0.1:8080/api/v1/auth/dev-login "
                "| python3 -c 'import sys,json; print(json.load(sys.stdin)[\"access_token\"])'); "
                'curl -fsS --max-time 10 -X DELETE -H "Authorization: Bearer $TOKEN" '
                "http://127.0.0.1:8080/api/v1/knowledge-graph/sources/$SID",
            ),
        ]
        for label, command in commands:
            run_remote(client, command, label=label, timeout=90, secrets=secrets)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
