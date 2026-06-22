"""Deploy frontend dist only."""
import os
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("8.215.63.182", 22, "root", os.environ.get("DEPLOY_PASS", ""), timeout=15)
sftp = client.open_sftp()

from pathlib import Path
web_dist = Path(r"C:\Projects\agent-platform\web\dist")
LIVE = "/home/admin/agent-platform"
remote_web = f"{LIVE}/web/dist"

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    stdout.channel.recv_exit_status()

run(f"rm -rf {remote_web} && mkdir -p {remote_web}")

count = 0
for local_file in web_dist.rglob("*"):
    if local_file.is_file():
        rel = local_file.relative_to(web_dist)
        remote_path = f"{remote_web}/{rel.as_posix()}"
        remote_dir = os.path.dirname(remote_path)
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            run(f"mkdir -p {remote_dir}")
        sftp.put(str(local_file), remote_path)
        count += 1

sftp.close()
client.close()
print(f"Deployed {count} frontend files.")
