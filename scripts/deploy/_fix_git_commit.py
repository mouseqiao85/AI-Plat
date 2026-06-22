"""Deploy fix + check what was committed."""
import paramiko
import time
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=15)

# Check git log for recent commits
print("=== Recent git commits on server ===")
stdin, stdout, stderr = client.exec_command(
    "cd /home/admin/agent-platform && git log --oneline -10", timeout=10)
out = stdout.read().decode().strip()
print(out)

print("\n=== Git status ===")
stdin, stdout, stderr = client.exec_command(
    "cd /home/admin/agent-platform && git status --short | head -20", timeout=10)
out = stdout.read().decode().strip()
print(out if out else "(clean)")

print("\n=== Check reports/kyc/ ===")
stdin, stdout, stderr = client.exec_command(
    "find / -path '*/reports/kyc*' -type f 2>/dev/null | head -10", timeout=10)
out = stdout.read().decode().strip()
print(out if out else "(not found)")

# Upload fixed hermes_cli.py
sftp = client.open_sftp()
sftp.put(
    r"C:\Projects\agent-platform\hermes-bridge\bridge\hermes_cli.py",
    "/home/admin/agent-platform/hermes-bridge/bridge/hermes_cli.py",
)
sftp.close()
print("\nUploaded hermes_cli.py (sandbox + no git commit)")

# Restart bridge
stdin, stdout, stderr = client.exec_command("fuser -k 8002/tcp 2>/dev/null || true", timeout=10)
stdout.channel.recv_exit_status()
time.sleep(3)

start_cmd = (
    "cd /home/admin/agent-platform/hermes-bridge && "
    "DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY "
    "GIT_USER_NAME=mouseqiao85 "
    "GIT_USER_EMAIL=mouseqiao@163.com "
    "GSTACK_AUTOLOAD=1 "
    "PYTHONPATH=/home/admin/agent-platform/hermes-bridge "
    "PYTHONUNBUFFERED=1 "
    "nohup /home/admin/agent-platform/agent/.venv/bin/python3 -u main.py "
    "> /tmp/hermes-bridge.log 2>&1 & disown; echo ok"
)
stdin, stdout, stderr = client.exec_command(start_cmd, timeout=10)
try:
    stdout.read(50)
except Exception:
    pass
time.sleep(5)

stdin, stdout, stderr = client.exec_command("curl -s http://localhost:8002/api/v2/health", timeout=10)
print(f"\nHealth: {stdout.read().decode().strip()}")

client.close()
print("Done.")
import os
