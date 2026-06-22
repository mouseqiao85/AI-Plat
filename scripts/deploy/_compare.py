"""Compare production files with local, report differences."""
import os
import paramiko
import hashlib
from pathlib import Path

HOST = "8.215.63.182"
USER = "root"
PASS = os.environ.get("DEPLOY_PASS", "")
LIVE = "/home/admin/agent-platform"
LOCAL_ROOT = Path(r"C:\Projects\agent-platform")

FILES_TO_CHECK = [
    "hermes-bridge/main.py",
    "hermes-bridge/bridge/__init__.py",
    "hermes-bridge/bridge/types.py",
    "hermes-bridge/bridge/db.py",
    "hermes-bridge/bridge/hermes_cli.py",
    "hermes-bridge/bridge/gstack_loader.py",
    "hermes-bridge/bridge/scenarios.py",
    "hermes-bridge/bridge/flows.py",
    "hermes-bridge/bridge/runs.py",
    "hermes-bridge/bridge/orchestrator.py",
    "hermes-bridge/bridge/chat_handler.py",
    "hermes-bridge/bridge/skill_tabs.py",
    "hermes-bridge/bridge/github_importer.py",
    "hermes-bridge/bridge/llm_classifier.py",
    "hermes-bridge/requirements.txt",
    "hermes-bridge/.env.example",
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USER, PASS, timeout=15)
sftp = client.open_sftp()

diffs = []
missing_remote = []
missing_local = []

for rel in FILES_TO_CHECK:
    local_path = LOCAL_ROOT / rel
    remote_path = f"{LIVE}/{rel}"

    # Local hash
    if not local_path.exists():
        missing_local.append(rel)
        continue
    local_content = local_path.read_bytes()
    local_hash = hashlib.md5(local_content).hexdigest()

    # Remote hash
    try:
        with sftp.open(remote_path, "rb") as f:
            remote_content = f.read()
        remote_hash = hashlib.md5(remote_content).hexdigest()
    except FileNotFoundError:
        missing_remote.append(rel)
        continue

    if local_hash != remote_hash:
        # Show line count diff
        local_lines = local_content.decode("utf-8", errors="replace").count("\n")
        remote_lines = remote_content.decode("utf-8", errors="replace").count("\n")
        diffs.append((rel, local_lines, remote_lines, local_hash[:8], remote_hash[:8]))

sftp.close()
client.close()

print(f"=== Comparison: {len(FILES_TO_CHECK)} files ===\n")

if not diffs and not missing_remote and not missing_local:
    print("All files are in sync!")
else:
    if diffs:
        print(f"DIFFERENT ({len(diffs)} files):")
        for rel, ll, rl, lh, rh in diffs:
            print(f"  {rel}")
            print(f"    local: {ll} lines (md5:{lh})  |  remote: {rl} lines (md5:{rh})")
        print()
    if missing_remote:
        print(f"MISSING ON SERVER ({len(missing_remote)}):")
        for rel in missing_remote:
            print(f"  {rel}")
        print()
    if missing_local:
        print(f"MISSING LOCALLY ({len(missing_local)}):")
        for rel in missing_local:
            print(f"  {rel}")
        print()

    # Sync: download production files to local
    print("=" * 50)
    print(f"Total: {len(diffs)} different, {len(missing_remote)} missing on server, {len(missing_local)} missing locally")
import os
