"""Deploy updated github_importer and test import with financial-services repo."""
import json
import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=15)

# Upload
sftp = client.open_sftp()
sftp.put(
    r"C:\Projects\agent-platform\hermes-bridge\bridge\github_importer.py",
    "/home/admin/agent-platform/hermes-bridge/bridge/github_importer.py",
)
print("Uploaded github_importer.py")
sftp.close()

# Restart
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

# Health
stdin, stdout, stderr = client.exec_command("curl -s http://localhost:8002/api/v2/health", timeout=10)
health = stdout.read().decode().strip()
print(f"Health: {health}")

# Test: create a finance tab then import
print("\n=== Creating finance tab ===")
create_cmd = '''curl -s -X POST http://localhost:8002/api/v2/tabs \
  -H "Content-Type: application/json" \
  -d '{"id":"finance","name":"金融","description":"金融服务专家角色","source_type":"github","source_url":"https://github.com/anthropics/financial-services","branch":"main","sub_path":"plugins/agent-plugins","icon":"bank"}'
'''
stdin, stdout, stderr = client.exec_command(create_cmd, timeout=10)
out = stdout.read().decode().strip()
print(f"  {out[:200]}")

# Test clone only (skip LLM classify which costs API calls)
print("\n=== Testing scan (clone + scan only) ===")
test_cmd = '''cd /home/admin/agent-platform/hermes-bridge && \
/home/admin/agent-platform/agent/.venv/bin/python3 -c "
from bridge.github_importer import clone_repo, scan_skills, parse_skill_md
import json

url = 'https://github.com/anthropics/financial-services'
clone_path = clone_repo(url, 'finance', branch='main')
print(f'Cloned to: {clone_path}')

results = scan_skills(clone_path, 'plugins/agent-plugins')
print(f'Found {len(results)} skills:')
for skill_dir, role_group in results[:15]:
    print(f'  [{role_group or \"flat\"}] {skill_dir.name}')

# Parse first few
print()
print('=== Parsed samples ===')
for skill_dir, role_group in results[:3]:
    s = parse_skill_md(skill_dir, role_group=role_group)
    print(f'  id={s.skill_id} | name={s.name} | role_group={s.role_group} | desc={s.description[:80]}')
"
'''
stdin, stdout, stderr = client.exec_command(test_cmd, timeout=120)
rc = stdout.channel.recv_exit_status()
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print(out)
if err and rc != 0:
    print(f"STDERR: {err[:500]}")

client.close()
print("\nDone.")
import os
