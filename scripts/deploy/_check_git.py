"""Check git clone capability on the server."""
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=15)


def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    rc = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return rc, out, err


print("=== Git version ===")
rc, out, err = run("git --version")
print(f"  {out}")

print("\n=== Git global config ===")
rc, out, err = run("git config --global --list 2>/dev/null")
print(f"  {out if out else '(empty)'}")

print("\n=== SSH keys ===")
rc, out, err = run("ls -la ~/.ssh/ 2>/dev/null")
print(f"  {out if out else '(no .ssh dir)'}")

print("\n=== GitHub SSH test ===")
rc, out, err = run("ssh -T git@github.com 2>&1 || true")
print(f"  {out}")

print("\n=== GitHub HTTPS credential helper ===")
rc, out, err = run("git config --global credential.helper 2>/dev/null")
print(f"  {out if out else '(none)'}")

print("\n=== Test clone (public repo, dry-run) ===")
rc, out, err = run("git ls-remote --heads https://github.com/garrytan/gstack.git 2>&1 | head -5")
print(f"  rc={rc}")
print(f"  {out[:300] if out else err[:300]}")

print("\n=== Env vars (GIT_*) ===")
rc, out, err = run("env | grep -i GIT || true")
print(f"  {out if out else '(none in current shell)'}")

print("\n=== Stored credentials ===")
rc, out, err = run("cat ~/.git-credentials 2>/dev/null || echo '(no credential file)'")
print(f"  {out[:200]}")

client.close()
import os
