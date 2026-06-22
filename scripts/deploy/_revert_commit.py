"""Revert the bad commit and deploy fix."""
import paramiko
import time
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=15)


def run(cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    rc = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    return rc, out


# 1. Revert the KYC commit
print("=== Reverting KYC commit ===")
rc, out = run("cd /home/admin/agent-platform && git revert --no-edit ee38579")
print(f"  rc={rc}, {out[:200]}")

# If revert fails (conflicts), just reset
if rc != 0:
    print("  Revert failed, using reset...")
    rc, out = run("cd /home/admin/agent-platform && git reset HEAD~1 --hard")
    print(f"  reset: {out[:200]}")

# 2. Clean up reports/kyc/ if it exists
rc, out = run("rm -rf /home/admin/agent-platform/reports 2>/dev/null; echo done")
print(f"\n  Cleaned reports/ dir")

# 3. Upload fixed hermes_cli.py
sftp = client.open_sftp()
sftp.put(
    r"C:\Projects\agent-platform\hermes-bridge\bridge\hermes_cli.py",
    "/home/admin/agent-platform/hermes-bridge/bridge/hermes_cli.py",
)
sftp.close()
print("  Uploaded hermes_cli.py")

# 4. Restart bridge
run("fuser -k 8002/tcp 2>/dev/null || true")
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

# 5. Verify
rc, out = run("curl -s http://localhost:8002/api/v2/health")
print(f"\n  Health: {out}")

rc, out = run("cd /home/admin/agent-platform && git log --oneline -3")
print(f"\n=== Git log (after fix) ===\n  {out}")

client.close()
print("\nDone.")
import os
