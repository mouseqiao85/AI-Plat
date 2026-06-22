"""Deploy updated github_importer.py and restart bridge."""
import paramiko
import time

HOST = "8.215.63.182"
USER = "root"
PASS = os.environ.get("DEPLOY_PASS", "")
LIVE = "/home/admin/agent-platform"


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, USER, PASS, timeout=15)
    sftp = client.open_sftp()

    # Upload updated file
    local = r"C:\Projects\agent-platform\hermes-bridge\bridge\github_importer.py"
    remote = f"{LIVE}/hermes-bridge/bridge/github_importer.py"
    sftp.put(local, remote)
    print(f"Uploaded: github_importer.py")

    sftp.close()

    # Restart bridge
    print("Restarting hermes-bridge...")
    stdin, stdout, stderr = client.exec_command("fuser -k 8002/tcp 2>/dev/null || true", timeout=10)
    stdout.channel.recv_exit_status()
    time.sleep(3)

    VENV_PYTHON = "/home/admin/agent-platform/agent/.venv/bin/python3"
    start_cmd = (
        f"cd /home/admin/agent-platform/hermes-bridge && "
        f"DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY "
        f"GIT_USER_NAME=mouseqiao85 "
        f"GIT_USER_EMAIL=mouseqiao@163.com "
        f"GSTACK_AUTOLOAD=1 "
        f"PYTHONPATH=/home/admin/agent-platform/hermes-bridge "
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
    stdin, stdout, stderr = client.exec_command("curl -s http://localhost:8002/api/v2/tabs", timeout=10)
    out = stdout.read().decode().strip()
    print(f"Tabs: {out[:200]}")

    client.close()
    print("Done.")


if __name__ == "__main__":
    main()
import os
