"""Restart hermes-bridge on remote server."""
import os
import paramiko
import time

HOST = "8.215.63.182"
PORT = 22
USER = "root"
PASS = os.environ.get("DEPLOY_PASS", "")


def run(client, cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    rc = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return rc, out, err


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, PORT, USER, PASS, timeout=15)
    print("Connected.\n")

    # 1. Read start script
    print("=== Start script ===")
    rc, out, err = run(client, "cat /home/admin/agent-platform/scripts/start-hermes-bridge.sh")
    print(out)
    print()

    # 2. Find processes
    print("=== Current hermes-bridge processes ===")
    rc, out, err = run(client, "ps aux | grep hermes-bridge | grep -v grep")
    print(out if out else "(none)")
    print()

    # Also find uvicorn on port 8002
    print("=== Processes on port 8002 ===")
    rc, out, err = run(client, "lsof -i :8002 -t 2>/dev/null || ss -tlnp | grep 8002")
    print(out if out else "(none)")
    print()

    # 3. Kill old processes forcefully
    print("=== Killing old processes ===")
    # Kill by port first (most reliable)
    rc, out, err = run(client, "fuser -k 8002/tcp 2>/dev/null || true")
    print(f"  fuser -k 8002/tcp: {out} {err}")
    time.sleep(1)
    # Also kill any remaining hermes-bridge processes
    run(client, "pkill -9 -f 'hermes-bridge' || true")
    time.sleep(1)
    # Double check
    rc, out, err = run(client, "fuser 8002/tcp 2>/dev/null || true")
    if out.strip():
        print(f"  Still occupied: {out}, killing again...")
        run(client, f"kill -9 {out.strip().split()[-1]}")
    time.sleep(5)  # Wait for TIME_WAIT to clear

    # 4. Verify killed
    rc, out, err = run(client, "lsof -i :8002 -t 2>/dev/null")
    print(f"  Port 8002 after kill: {out if out else 'free'}")
    print()

    # 5. Start new process using the venv python (fire-and-forget)
    print("=== Starting hermes-bridge ===")
    VENV_PYTHON = "/home/admin/agent-platform/agent/.venv/bin/python3"
    start_cmd = (
        f"cd /home/admin/agent-platform/hermes-bridge && "
        f"DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY "
        f"GIT_USER_NAME=mouseqiao85 "
        f"GIT_USER_EMAIL=mouseqiao@163.com "
        f"GSTACK_AUTOLOAD=1 "
        f"PYTHONPATH=/home/admin/agent-platform/hermes-bridge "
        f"PYTHONUNBUFFERED=1 "
        f"nohup {VENV_PYTHON} -u main.py > /tmp/hermes-bridge.log 2>&1 &"
        f" disown; echo started"
    )
    # Use a short timeout since the process backgrounds
    stdin, stdout, stderr = client.exec_command(start_cmd, timeout=10)
    try:
        out = stdout.read(100).decode()
        print(f"  {out.strip()}")
    except Exception:
        print("  Command sent (backgrounded)")
    time.sleep(6)

    # 6. Verify running
    print("\n=== Verify running ===")
    rc, out, err = run(client, "ps aux | grep 'uvicorn main:app' | grep -v grep | head -3")
    print(out if out else "NOT RUNNING!")
    print()

    # 7. Health check
    print("=== Health check ===")
    rc, out, err = run(client, "curl -s http://localhost:8002/api/v2/health")
    print(f"  {out}")
    print()

    # 8. Tabs API
    print("=== Tabs API ===")
    rc, out, err = run(client, "curl -s http://localhost:8002/api/v2/tabs")
    print(f"  {out}")
    print()

    # 9. Check log for errors
    print("=== Startup log (last 30 lines) ===")
    rc, out, err = run(client, "tail -30 /tmp/hermes-bridge.log")
    print(out)

    client.close()
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
import os
