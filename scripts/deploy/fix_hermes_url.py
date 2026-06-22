"""Quick fix: revert hermes service_url to 172.19.30.12, restart gateway."""
import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=20)

def run(cmd, tmo=30):
    print(f"$ {cmd}")
    _, o, e = c.exec_command(cmd, timeout=tmo)
    out = o.read().decode("utf-8", "replace").rstrip()
    err = e.read().decode("utf-8", "replace").rstrip()
    rc = o.channel.recv_exit_status()
    if out:
        try: print(out)
        except UnicodeEncodeError: print(out.encode("ascii","replace").decode("ascii"))
    if err:
        try: print(f"[stderr] {err[:500]}")
        except UnicodeEncodeError: print(f"[stderr] {err[:500].encode('ascii','replace').decode('ascii')}")
    print(f"[exit={rc}]\n")

CFG = "/home/admin/agent-platform/configs/config.yaml"

# 1. backup
run(f"cp -a {CFG} {CFG}.bak-$(date +%Y%m%d-%H%M%S)")

# 2. sed: the hermes service_url (line 24) only — don't touch agent (line 19)
run(f"sed -i '/^hermes:/,/^[a-z]/ s|service_url: http://localhost:8002|service_url: http://172.19.30.12:8002|' {CFG}")

# 3. verify
run(f"grep -n -E 'service_url|hermes|agent:' {CFG}")

# 4. find current gateway pid
run("pgrep -fa 'agent-gateway --config' || echo no-gateway")

# 5. restart gateway
run("fuser -k -KILL 8080/tcp 2>&1 || true")
time.sleep(2)
run("ss -tlnp | grep ':8080' || echo port-8080-free")

gw = (
    "cd /home/admin/agent-platform && "
    "( GATEWAY_HOST=0.0.0.0 nohup ./build/agent-gateway --config configs/config.yaml "
    ">> logs/gateway.log 2>&1 < /dev/null & ) && echo spawned"
)
run(gw)
time.sleep(5)

# 6. verify gateway back up
run("pgrep -fa 'agent-gateway --config' || echo gateway-NOT-RUNNING")
run("ss -tlnp | grep ':8080'")

# 7. tail log for bridge-related errors
run("tail -20 /home/admin/agent-platform/logs/gateway.log")

# 8. sanity: check bridge is reachable from new gateway's network namespace (same host, should be fine)
run("curl -fsS --max-time 3 http://172.19.30.12:8002/ 2>&1 | head -c 200 || echo bridge-root-unreachable")

c.close()
print("=== hermes service_url reverted + gateway restarted ===")
import os
