"""Verify remote Obsidian import recovers GB18030 zip entry names."""
from __future__ import annotations

import io
import sys
import zipfile

from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, run_remote


def build_zip() -> bytes:
    buf = io.BytesIO()
    mojibake_name = "90_模板/示例.md".encode("gb18030").decode("cp437")
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(mojibake_name, "# 示例\n#中文标签")
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
            with sftp.file("/tmp/kg-encoding-test.zip", "wb") as handle:
                handle.write(build_zip())
        finally:
            sftp.close()

        commands = [
            (
                "import-encoding-test",
                "curl -sS --max-time 30 -X POST -F source_name=EncodingRegression "
                "-F file=@/tmp/kg-encoding-test.zip "
                "http://127.0.0.1:8001/api/v1/knowledge-graph/import/obsidian",
            ),
            (
                "query-encoding-note",
                "curl -fsS --max-time 8 'http://127.0.0.1:8001/api/v1/knowledge-graph/nodes?q=%E7%A4%BA%E4%BE%8B&limit=10' "
                "| python3 -c 'import sys; print(sys.stdin.read().encode(\"unicode_escape\").decode())'",
            ),
            (
                "delete-encoding-source",
                "SID=$(curl -sS --max-time 20 http://127.0.0.1:8001/api/v1/knowledge-graph/sources "
                "| python3 -c 'import sys,json; data=json.load(sys.stdin); "
                "print(next(s[\"id\"] for s in data if s[\"name\"]==\"EncodingRegression\"))'); "
                "curl -fsS --max-time 10 -X DELETE http://127.0.0.1:8001/api/v1/knowledge-graph/sources/$SID",
            ),
        ]
        for label, command in commands:
            run_remote(client, command, timeout=90, label=label, secrets=secrets)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
