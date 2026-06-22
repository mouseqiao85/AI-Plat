"""Debug: check cloned repo structure."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=15)

cmds = [
    "ls /root/.agent-platform/skill-packs/finance/financial-services/plugins/agent-plugins/ | head -15",
    "find /root/.agent-platform/skill-packs/finance/financial-services/plugins/agent-plugins -name 'SKILL.md' | head -20",
    "find /root/.agent-platform/skill-packs/finance/financial-services/plugins/agent-plugins -maxdepth 4 -type f -name '*.md' | head -20",
    "ls /root/.agent-platform/skill-packs/finance/financial-services/plugins/agent-plugins/earnings-reviewer/",
]

for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    print(f"$ {cmd[:80]}")
    print(f"  {out if out else err}")
    print()

client.close()
import os
