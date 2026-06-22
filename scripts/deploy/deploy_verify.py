"""Final verification — confirm deployment success via end-to-end checks."""
from __future__ import annotations
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=20)

def run(cmd, tmo=30):
    print(f"$ {cmd}")
    _, o, e = c.exec_command(cmd, timeout=tmo)
    try:
        out = o.read().decode("utf-8", "replace").rstrip()
        err = e.read().decode("utf-8", "replace").rstrip()
        rc = o.channel.recv_exit_status()
    except Exception as ex:
        print(f"[channel err: {ex}]\n"); return
    if out:
        try: print(out)
        except UnicodeEncodeError: print(out.encode("ascii","replace").decode("ascii"))
    if err:
        try: print(f"[stderr] {err[:500]}")
        except UnicodeEncodeError: print(f"[stderr] {err[:500].encode('ascii','replace').decode('ascii')}")
    print(f"[exit={rc}]\n")

# ── 1. Gateway exe matches new binary
print("=== 1. verify gateway exe matches NEW binary ===")
run("readlink -f /proc/100954/exe")
run("md5sum /proc/100954/exe /home/admin/agent-platform/build/agent-gateway")

# ── 2. agent service: tools endpoint includes brave_search
print("=== 2. agent /api/v1/tools includes brave_search ===")
run("curl -fsS --max-time 5 http://127.0.0.1:8001/api/v1/agent/tools 2>&1 | head -c 1500 || echo no-route")
# Try alternate paths
run("curl -fsS --max-time 5 http://127.0.0.1:8001/api/v1/agent/chat/tools 2>&1 | head -c 1000 || echo alt-no-route")
run("curl -fsS --max-time 5 http://127.0.0.1:8001/openapi.json 2>&1 | python3 -c \"import json,sys; d=json.load(sys.stdin); print('\\n'.join(sorted(d['paths'].keys())))\" | head -40")

# ── 3. gateway routes brave_search through
print("=== 3. gateway routes /api/v1/tools ===")
run("curl -fsS --max-time 5 http://127.0.0.1:8080/api/v1/tools 2>&1 | head -c 2000 || echo gw-tools-fail")

# ── 4. external public-IP reachability
print("=== 4. external access ===")
run("curl -fsS --max-time 5 http://8.215.63.182:8080/api/v1/tools 2>&1 | head -c 1500 || echo ext-fail")
run("curl -fsS --max-time 5 http://8.215.63.182:8001/health 2>&1 || echo ext-agent-fail")

# ── 5. verify no process orphans / zombies
print("=== 5. process hygiene ===")
run("ps -ef | grep -E 'agent-gateway|agent/\\.venv' | grep -v grep")

# ── 6. BRAVE_API_KEY source (since .env missing but 'brave_search enabled' logged)
print("=== 6. where does BRAVE_API_KEY come from ===")
run("cat /proc/101122/environ 2>/dev/null | tr '\\0' '\\n' | grep -iE 'brave|api_key' | sed 's/=.*/=<redacted>/'")
run("cat /proc/101124/environ 2>/dev/null | tr '\\0' '\\n' | grep -iE 'brave|api_key' | sed 's/=.*/=<redacted>/'")
# Also check where the service looks for .env
run("grep -n 'BRAVE_API_KEY\\|env_file\\|load_dotenv' /home/admin/agent-platform/agent/app/core/config.py | head -10")

# ── 7. hermes-bridge still OK
print("=== 7. hermes-bridge untouched ===")
run("pgrep -fa 'hermes-bridge.*main.py'")
run("curl -fsS --max-time 3 http://172.19.30.12:8002/health 2>&1 || echo bridge-unreachable")

# ── 8. clean up stale staging files (keep backup tarball)
print("=== 8. cleanup ===")
run("ls -la /home/admin/agent-platform-new/build/ 2>&1")  # before rm
# We leave /home/admin/agent-platform-new alone for manual rollback convenience

c.close()
print("=== FINAL VERIFY DONE ===")
import os
