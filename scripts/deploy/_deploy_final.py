"""Deploy env config + frontend + restart."""
import os
import os
import paramiko
import time
from pathlib import Path

HOST = "8.215.63.182"
USER = "root"
PASS = os.environ.get("DEPLOY_PASS", "")
LIVE = "/home/admin/agent-platform"
LOCAL_ROOT = Path(r"C:\Projects\agent-platform")


def run(client, cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    rc = stdout.channel.recv_exit_status()
    return rc, stdout.read().decode("utf-8", errors="replace").strip()


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, USER, PASS, timeout=15)
    sftp = client.open_sftp()

    # Upload bridge files
    files = [
        "hermes-bridge/main.py",
        "hermes-bridge/requirements.txt",
        "hermes-bridge/.env.example",
        "hermes-bridge/bridge/github_importer.py",
    ]
    for rel in files:
        local = str(LOCAL_ROOT / rel)
        remote = f"{LIVE}/{rel}"
        sftp.put(local, remote)
        print(f"  Uploaded: {rel}")

    # Copy .env.example to .env if not exists
    run(client, f"test -f {LIVE}/hermes-bridge/.env || cp {LIVE}/hermes-bridge/.env.example {LIVE}/hermes-bridge/.env")

    # Install python-dotenv
    print("\n  Installing python-dotenv...")
    rc, out = run(client, "/home/admin/agent-platform/agent/.venv/bin/pip install python-dotenv -q", timeout=30)
    print(f"  pip rc={rc}")

    # Upload frontend dist
    print("\n  Uploading frontend dist...")
    web_dist = LOCAL_ROOT / "web" / "dist"
    remote_web = f"{LIVE}/web/dist"
    run(client, f"rm -rf {remote_web} && mkdir -p {remote_web}")
    count = 0
    for local_file in web_dist.rglob("*"):
        if local_file.is_file():
            rel = local_file.relative_to(web_dist)
            remote_path = f"{remote_web}/{rel.as_posix()}"
            remote_dir = os.path.dirname(remote_path)
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                run(client, f"mkdir -p {remote_dir}")
            sftp.put(str(local_file), remote_path)
            count += 1
    print(f"  Uploaded {count} dist files")

    # Restart bridge
    print("\n  Restarting hermes-bridge...")
    run(client, "fuser -k 8002/tcp 2>/dev/null || true")
    time.sleep(3)

    VENV_PYTHON = "/home/admin/agent-platform/agent/.venv/bin/python3"
    start_cmd = (
        f"cd {LIVE}/hermes-bridge && "
        f"DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY "
        f"GIT_USER_NAME=mouseqiao85 "
        f"GIT_USER_EMAIL=mouseqiao@163.com "
        f"GSTACK_AUTOLOAD=1 "
        f"PYTHONPATH={LIVE}/hermes-bridge "
        f"PYTHONUNBUFFERED=1 "
        f"nohup {VENV_PYTHON} -u main.py > /tmp/hermes-bridge.log 2>&1 & disown; echo ok"
    )
    stdin, stdout, stderr = client.exec_command(start_cmd, timeout=10)
    try:
        print(f"  {stdout.read(50).decode().strip()}")
    except Exception:
        print("  Backgrounded")
    time.sleep(5)

    # Verify
    rc, out = run(client, "curl -s http://localhost:8002/api/v2/health")
    print(f"\n  Health: {out}")
    rc, out = run(client, "curl -s http://localhost:8002/api/v2/tabs")
    print(f"  Tabs: {out[:150]}")

    sftp.close()
    client.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
