#!/usr/bin/env python3
"""Package the local project and deploy it to the configured remote host."""

from __future__ import annotations

import sys
import tarfile
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

sys.path.insert(0, str(SCRIPT_DIR))
from ssh_config import DeployConfigError, DeployConnectionError, connect, load_deploy_config, run_remote  # noqa: E402

SERVER_PATH = "/opt/ai-plat"
PACKAGE_NAME = "ai-plat-deploy.tar.gz"
UPDATE_SCRIPT = SCRIPT_DIR / "deploy_update_v2.sh"
RUN_SECRETS: list[str] = []


def create_deployment_package() -> Path:
    print("=" * 50)
    print("1. Creating deployment package...")
    print("=" * 50)

    package_path = PROJECT_ROOT / PACKAGE_NAME
    files_to_include = [
        "platform/web/src",
        "platform/api",
        "platform/mlops",
        "platform/auth",
        "platform/database",
        "platform/agents",
        "platform/ontology",
        "platform/vibecoding",
        "platform/workflow",
        "platform/gateway",
        "platform/app.py",
        "platform/main.py",
        "platform/requirements.txt",
        "deploy",
    ]

    with tarfile.open(package_path, "w:gz") as tar:
        for item in files_to_include:
            full_path = PROJECT_ROOT / item
            if full_path.exists():
                print(f"  Adding: {item}")
                tar.add(full_path, arcname=item)
            else:
                print(f"  Skipping (not found): {item}")

        if UPDATE_SCRIPT.exists():
            tar.add(UPDATE_SCRIPT, arcname="deploy_update_v2.sh")

    size_mb = package_path.stat().st_size / (1024 * 1024)
    print(f"\nPackage created: {package_path} ({size_mb:.2f} MB)")
    return package_path


def connect_server():
    print("\n" + "=" * 50)
    print("2. Connecting to server...")
    print("=" * 50)

    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        RUN_SECRETS[:] = [config.password or ""]
        client = connect(config)
        print(f"  Connected to {config.endpoint} via {config.auth_method} auth")
        return client, config
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"  Connection failed: {exc}", file=sys.stderr)
        print("  Set DEPLOY_PASS or DEPLOY_KEY_FILE locally; see .env.example for DEPLOY_* variables.", file=sys.stderr)
        sys.exit(1)


def upload_file(client, local_path: Path) -> str:
    print("\n" + "=" * 50)
    print("3. Uploading deployment package...")
    print("=" * 50)

    sftp = client.open_sftp()
    remote_file = f"/tmp/{PACKAGE_NAME}"

    try:
        print(f"  Uploading to {remote_file}...")
        sftp.put(str(local_path), remote_file)
        print("  Upload completed")
        return remote_file
    except Exception as exc:
        print(f"  Upload failed: {exc}")
        sys.exit(1)
    finally:
        sftp.close()


def run_command(client, command: str, show_output: bool = True):
    return run_remote(client, command, print_output=show_output, secrets=RUN_SECRETS)


def deploy(client) -> None:
    print("\n" + "=" * 50)
    print("4. Deploying to server...")
    print("=" * 50)

    commands = [
        f"mkdir -p {SERVER_PATH}",
        f"if [ -d {SERVER_PATH}/platform ]; then cd {SERVER_PATH} && tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz platform 2>/dev/null || true; fi",
        f"cd {SERVER_PATH} && tar -xzf /tmp/{PACKAGE_NAME}",
        f"chmod +x {SERVER_PATH}/deploy_update_v2.sh 2>/dev/null || true",
        f"echo 'Current git status:' && cd {SERVER_PATH} && git log -1 --oneline 2>/dev/null || echo 'Not a git repo'",
        "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}' 2>/dev/null || echo 'Docker not running'",
    ]

    for command in commands:
        print(f"\n> {command}")
        run_command(client, command)

    print("\n" + "=" * 50)
    print("5. Checking Docker Compose...")
    print("=" * 50)

    _, output, _ = run_command(
        client,
        f"test -f {SERVER_PATH}/deploy/docker-compose.yml && echo 'exists' || echo 'not_found'",
        False,
    )

    if "exists" in output:
        print("  Docker Compose file found. Rebuilding services...")
        deploy_commands = [
            f"cd {SERVER_PATH} && docker-compose -f deploy/docker-compose.yml down || true",
            f"cd {SERVER_PATH} && docker-compose -f deploy/docker-compose.yml build --no-cache",
            f"cd {SERVER_PATH} && docker-compose -f deploy/docker-compose.yml up -d",
        ]

        for command in deploy_commands:
            print(f"\n> {command}")
            exit_code, _, _ = run_command(client, command)
            if exit_code != 0:
                print(f"  Warning: Command exited with code {exit_code}")
    else:
        print("  Docker Compose file not found. Skipping container rebuild.")
        print("  You may need to run: ./deploy_update_v2.sh manually")


def verify_deployment(client) -> None:
    print("\n" + "=" * 50)
    print("6. Verifying deployment...")
    print("=" * 50)

    time.sleep(5)

    print("\n  Container status:")
    run_command(client, "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")

    print("\n  API health check:")
    _, output, _ = run_command(client, "curl -s http://localhost:8000/health || echo 'API not responding'", False)
    print(f"  {output.strip()}")

    print("\n  Web service check:")
    _, output, _ = run_command(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000 || echo 'Web not responding'", False)
    print(f"  HTTP Status: {output.strip()}")


def main() -> None:
    print("\n" + "=" * 60)
    print("  AI-Plat Platform - Auto Deployment Script")
    print("=" * 60)

    try:
        package_path = create_deployment_package()
        client, config = connect_server()

        try:
            upload_file(client, package_path)
            deploy(client)
            verify_deployment(client)

            print("\n" + "=" * 60)
            print("  Deployment completed successfully!")
            print("=" * 60)
            print("\n  Access URLs:")
            print(f"    Web:   http://{config.host}:3000")
            print(f"    API:   http://{config.host}:8000")
            print(f"    Docs:  http://{config.host}:8000/docs")
            print()
        finally:
            client.close()

    except Exception as exc:
        print(f"\nDeployment failed: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
