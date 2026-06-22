"""Re-test scan after fix."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=15)

# Upload fix
sftp = client.open_sftp()
sftp.put(
    r"C:\Projects\agent-platform\hermes-bridge\bridge\github_importer.py",
    "/home/admin/agent-platform/hermes-bridge/bridge/github_importer.py",
)
sftp.close()
print("Uploaded fix.")

# Test scan directly (no restart needed, just test the module)
test_cmd = '''cd /home/admin/agent-platform/hermes-bridge && \
/home/admin/agent-platform/agent/.venv/bin/python3 -c "
from bridge.github_importer import scan_skills, parse_skill_md

clone_path = '/root/.agent-platform/skill-packs/finance/financial-services'
results = scan_skills(clone_path, 'plugins/agent-plugins')
print(f'Found {len(results)} skills:')
for skill_dir, role_group in results[:20]:
    print(f'  [{role_group or \"flat\"}] {skill_dir.name}')

print()
print('=== Parsed samples ===')
for skill_dir, role_group in results[:5]:
    s = parse_skill_md(skill_dir, role_group=role_group)
    print(f'  id={s.skill_id}')
    print(f'    desc={s.description[:100]}')
    print()
"
'''
stdin, stdout, stderr = client.exec_command(test_cmd, timeout=30)
rc = stdout.channel.recv_exit_status()
out = stdout.read().decode().strip()
err = stderr.read().decode().strip()
print(out)
if rc != 0 and err:
    print(f"ERR: {err[:500]}")

client.close()
import os
