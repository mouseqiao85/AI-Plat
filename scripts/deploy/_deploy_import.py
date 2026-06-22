"""Deploy and run full import for finance tab."""
import json
import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=15)

# Upload
sftp = client.open_sftp()
sftp.put(
    r"C:\Projects\agent-platform\hermes-bridge\bridge\chat_handler.py",
    "/home/admin/agent-platform/hermes-bridge/bridge/chat_handler.py",
)
sftp.put(
    r"C:\Projects\agent-platform\hermes-bridge\bridge\github_importer.py",
    "/home/admin/agent-platform/hermes-bridge/bridge/github_importer.py",
)
sftp.close()
print("Uploaded chat_handler.py + github_importer.py")

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

# Verify health
stdin, stdout, stderr = client.exec_command("curl -s http://localhost:8002/api/v2/health", timeout=10)
print(f"Health: {stdout.read().decode().strip()}")

# Delete old finance tab first (in case it exists from earlier)
stdin, stdout, stderr = client.exec_command(
    'curl -s -X DELETE http://localhost:8002/api/v2/tabs/finance', timeout=10)
stdout.channel.recv_exit_status()

# Create finance tab
print("\n=== Create finance tab ===")
create_cmd = '''curl -s -X POST http://localhost:8002/api/v2/tabs \
  -H "Content-Type: application/json" \
  -d '{"id":"finance","name":"金融","description":"金融服务专家角色","source_type":"github","source_url":"https://github.com/anthropics/financial-services","branch":"main","sub_path":"plugins/agent-plugins","icon":"bank"}'
'''
stdin, stdout, stderr = client.exec_command(create_cmd, timeout=10)
out = stdout.read().decode().strip()
print(f"  Created: {out[:150]}")

# Import
print("\n=== Import (using repo structure, no LLM) ===")
import_cmd = '''curl -s -X POST http://localhost:8002/api/v2/tabs/finance/import \
  -H "Content-Type: application/json" \
  -d '{"url":"https://github.com/anthropics/financial-services","branch":"main","sub_path":"plugins/agent-plugins"}'
'''
stdin, stdout, stderr = client.exec_command(import_cmd, timeout=180)
rc = stdout.channel.recv_exit_status()
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()

try:
    data = json.loads(out)
    print(f"  Success: {data.get('success')}")
    print(f"  Scanned: {data.get('scanned')}")
    print(f"  Imported: {data.get('imported')}")
    print(f"  Scenarios: {data.get('scenarios_generated')}")
    # Show first few roles
    roles = data.get("roles", [])
    print(f"\n  Sample roles ({len(roles)} total):")
    for r in roles[:8]:
        print(f"    [{r.get('category')}] {r.get('display_name')} - {r.get('description','')[:60]}")
except json.JSONDecodeError:
    print(f"  Raw: {out[:500]}")
    if err:
        print(f"  Err: {err[:300]}")

# List tabs
print("\n=== All tabs ===")
stdin, stdout, stderr = client.exec_command("curl -s http://localhost:8002/api/v2/tabs", timeout=10)
out = stdout.read().decode().strip()
data = json.loads(out)
for t in data.get("tabs", []):
    print(f"  {t['id']}: {t['name']} (roles={t.get('role_count', '?')})")

client.close()
print("\nDone.")
import os
