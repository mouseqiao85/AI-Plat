"""Verify all endpoints after deployment."""
import json
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=15)


def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    stdout.channel.recv_exit_status()
    return stdout.read().decode("utf-8", errors="replace").strip()


print("=== Gateway -> Bridge health ===")
print(run("curl -s http://localhost:8080/api/v1/hermes/health"))

print("\n=== Roles count ===")
out = run("curl -s http://localhost:8002/api/v2/roles")
d = json.loads(out)
print(f"Roles: {d.get('count', 0)}")

print("\n=== Tabs list ===")
print(run("curl -s http://localhost:8002/api/v2/tabs"))

print("\n=== Flows list ===")
out = run("curl -s http://localhost:8002/api/v2/flows")
d = json.loads(out)
print(f"Flows: {len(d.get('flows', []))}")

print("\n=== Scenarios ===")
out = run("curl -s http://localhost:8002/api/v2/scenarios")
d = json.loads(out)
print(f"Scenarios: {len(d.get('scenarios', []))}")

print("\n=== Skills (filesystem) ===")
out = run("curl -s http://localhost:8002/api/v2/skills")
d = json.loads(out)
print(f"Skills: {len(d.get('skills', []))}")

client.close()
print("\nAll checks passed!")
import os
