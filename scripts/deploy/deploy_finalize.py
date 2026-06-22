"""Finalize: kill agent by pid, start gateway + agent via subshell-fork so the
SSH channel closes immediately."""
from __future__ import annotations

import os
import paramiko, time, socket

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=20)

def run(cmd, tmo=40):
    print(f"$ {cmd}")
    _, o, e = c.exec_command(cmd, timeout=tmo, get_pty=False)
    try:
        out = o.read().decode("utf-8", "replace").rstrip()
        err = e.read().decode("utf-8", "replace").rstrip()
        rc = o.channel.recv_exit_status()
    except (socket.timeout, Exception) as ex:
        print(f"[channel timeout: {type(ex).__name__}]\n")
        return -1, "", ""
    if out:
        try: print(out)
        except UnicodeEncodeError: print(out.encode("ascii","replace").decode("ascii"))
    if err:
        try: print(f"[stderr] {err[:500]}")
        except UnicodeEncodeError: print(f"[stderr] {err[:500].encode('ascii','replace').decode('ascii')}")
    print(f"[exit={rc}]\n")
    return rc, out, err

# ---- find agent pids holding port 8001
print("=== find agent pid on port 8001 ===")
run("ss -tlnp | grep ':8001' | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u")

# ---- kill by port (more reliable than cmd-pattern)
print("=== kill agent (by port) ===")
run("fuser -k -KILL 8001/tcp 2>&1 || true")
time.sleep(2)
run("ss -tlnp | grep ':8001' || echo port-8001-free")

# ---- verify gateway port free
run("ss -tlnp | grep ':8080' || echo port-8080-free")

# ---- start gateway using subshell fork: ( CMD & ) pattern
print("=== start gateway via subshell fork ===")
gw = (
    "cd /home/admin/agent-platform && "
    "( GATEWAY_HOST=0.0.0.0 nohup ./build/agent-gateway --config configs/config.yaml "
    ">> logs/gateway.log 2>&1 < /dev/null & ) && echo spawned"
)
run(gw)

print("=== start agent via subshell fork ===")
ag = (
    "cd /home/admin/agent-platform/agent && "
    "( nohup ./.venv/bin/python main.py >> ../logs/agent.log 2>&1 < /dev/null & ) && echo spawned"
)
run(ag)

print("waiting 8s for boot...")
time.sleep(8)

# ---- verify
print("=== verify ===")
run("pgrep -fa 'agent-gateway --config' || echo gateway-NOT-RUNNING")
run("pgrep -fa '.venv/bin/python main.py' || echo agent-NOT-RUNNING")
run("ss -tlnp | grep -E ':8080|:8001'")
run("curl -fsS --max-time 5 http://127.0.0.1:8080/health 2>&1 || echo gw-FAIL")
run("curl -fsS --max-time 5 http://127.0.0.1:8001/health 2>&1 || echo agent-FAIL")
run("curl -fsS --max-time 5 http://172.19.30.12:8080/health 2>&1 || echo gw-internal-FAIL")

# ---- inspect tools list (if agent has an endpoint for it — try common paths)
run("curl -fsS --max-time 5 http://127.0.0.1:8001/api/v1/tools 2>&1 | head -c 800 || echo no-v1-tools")
run("curl -fsS --max-time 5 http://127.0.0.1:8001/tools 2>&1 | head -c 800 || echo no-tools")
run("curl -fsS --max-time 5 http://127.0.0.1:8001/docs 2>&1 | head -c 400 || echo no-docs")

# Scan routes from openapi if available
run("curl -fsS --max-time 5 http://127.0.0.1:8001/openapi.json 2>&1 | head -c 2000 || echo no-openapi")

# ---- log tails
print("=== gateway log ===")
run("tail -40 /home/admin/agent-platform/logs/gateway.log 2>&1 | head -100")
print("=== agent log ===")
run("tail -60 /home/admin/agent-platform/logs/agent.log 2>&1 | head -100")

c.close()
