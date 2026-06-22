"""Fix pip install for python-dotenv."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=15)

cmds = [
    "ls /home/admin/agent-platform/agent/.venv/bin/pip*",
    "/home/admin/agent-platform/agent/.venv/bin/python3 -m pip install python-dotenv -q",
    "tail -5 /tmp/hermes-bridge.log",
]

for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    rc = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    print(f"$ {cmd}")
    print(f"  rc={rc} | {out[:200]}")
    if err:
        print(f"  ERR: {err[:200]}")
    print()

client.close()
import os
