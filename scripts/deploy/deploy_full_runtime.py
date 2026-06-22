"""Deploy the current runtime to the remote agent-platform host.

This script packages the local runtime source, uploads it through Paramiko,
backs up the live tree, stages the new tree, builds the Linux gateway binary,
updates Python agent dependencies, swaps the staged tree into place, restarts
the gateway/agent services, and verifies the key endpoints.

Remote data that must survive deployment is copied from the live tree into the
staging tree before cutover: .env files, logs, data, the Python venv, and the
existing build directory.
"""
from __future__ import annotations

import fnmatch
import os
import shutil
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from ssh_config import (
    DeployConfigError,
    DeployConnectionError,
    RemoteCommandError,
    connect,
    load_deploy_config,
    run_remote,
)


LOCAL_ROOT = Path(__file__).resolve().parents[2]
LIVE = "/home/admin/agent-platform"
STAGE = "/home/admin/agent-platform-stage"
BACKUP_DIR = "/home/admin/backups"
HERMES_SKILLS_DIR = "/home/admin/.hermes/skills"
REMOTE_PACKAGE = "/tmp/agent-platform-runtime.tar.gz"
TS = time.strftime("%Y%m%d-%H%M%S")

INCLUDE_PATHS = [
    ".env.example",
    ".gitignore",
    "README.md",
    "go.mod",
    "go.sum",
    "cmd",
    "configs",
    "internal",
    "pkg",
    "agent/main.py",
    "agent/pyproject.toml",
    "agent/app",
    "agent/skills",
    "hermes-bridge",
    "web/dist",
    "web/package.json",
    "web/package-lock.json",
]

EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".DS_Store",
    ".env",
    ".gstack",
    "*.bak*",
    "orchestrator.db",
    "venv",
]

PERSIST_PATHS = [
    ".env",
    "agent/.env",
    "hermes-bridge/.env",
    "logs",
    "data",
    "agent/data",
    "agent/.venv",
    "build",
]

REQUIRED_PYTHON_MODULES = [
    "fastapi",
    "multipart",
    "sqlalchemy",
    "aiosqlite",
    "langgraph",
    "docx",
    "openpyxl",
    "pptx",
]

PYTHON_DEPENDENCIES = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
    "langchain-openai>=0.2.0",
    "openai>=1.30.0",
    "pydantic>=2.6.1",
    "pydantic-settings>=2.1.0",
    "sqlalchemy[asyncio]>=2.0.27",
    "aiosqlite>=0.20.0",
    "redis>=5.0.1",
    "httpx>=0.27.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "numpy>=1.26.0",
    "pyyaml>=6.0",
    "python-multipart>=0.0.6",
    "python-docx>=1.1.0",
    "openpyxl>=3.1.0",
    "python-pptx>=0.6.23",
]


def _excluded(path: Path) -> bool:
    parts = path.parts
    for part in parts:
        if any(fnmatch.fnmatch(part, pattern) for pattern in EXCLUDE_PATTERNS):
            return True
    return False


def _add_path(tar: tarfile.TarFile, source: Path, arcname: str) -> None:
    if not source.exists():
        print(f"[skip] missing local path: {source.relative_to(LOCAL_ROOT)}")
        return
    if source.is_file():
        tar.add(source, arcname=arcname)
        return
    for child in source.rglob("*"):
        if _excluded(child.relative_to(source)):
            continue
        rel = child.relative_to(LOCAL_ROOT).as_posix()
        tar.add(child, arcname=rel, recursive=False)


def build_package() -> Path:
    dist_index = LOCAL_ROOT / "web" / "dist" / "index.html"
    if not dist_index.exists():
        raise RuntimeError("web/dist/index.html is missing; run npm.cmd --prefix web run build first")

    package_path = Path(tempfile.gettempdir()) / f"agent-platform-runtime-{TS}.tar.gz"
    if package_path.exists():
        package_path.unlink()

    with tarfile.open(package_path, "w:gz") as tar:
        for rel in INCLUDE_PATHS:
            _add_path(tar, LOCAL_ROOT / rel, rel.replace("\\", "/"))
    print(f"[package] {package_path} ({package_path.stat().st_size} bytes)")
    return package_path


def run(client, command: str, *, label: str, timeout: int = 300, check: bool = False, secrets: list[str] | None = None):
    return run_remote(
        client,
        command,
        timeout=timeout,
        label=label,
        check=check,
        secrets=secrets or [],
    )


def fire_and_forget(client, command: str) -> None:
    client.exec_command(command, timeout=5)


def remote_quote(path: str) -> str:
    return "'" + path.replace("'", "'\"'\"'") + "'"


def python_module_check_command(python_path: str) -> str:
    modules = ",".join(REQUIRED_PYTHON_MODULES)
    return (
        f"{python_path} -c \"import importlib.util,sys; "
        f"mods='{modules}'.split(','); "
        f"missing=[m for m in mods if importlib.util.find_spec(m) is None]; "
        f"print('python-modules-ok' if not missing else 'missing:'+','.join(missing)); "
        f"sys.exit(1 if missing else 0)\""
    )


def pip_install_dependencies_command(python_path: str) -> str:
    packages = " ".join(remote_quote(dep) for dep in PYTHON_DEPENDENCIES)
    return f"{python_path} -m pip install -q {packages}"


def main() -> int:
    package_path = build_package()

    try:
        config = load_deploy_config(default_host="8.215.63.182", default_user="root")
        secrets = [config.password or ""]
        print(f"=== Connecting to {config.endpoint} via {config.auth_method} auth ===")
        client = connect(config)
    except (DeployConfigError, DeployConnectionError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1

    try:
        sftp = client.open_sftp()
        try:
            print(f"[put] {package_path} -> {REMOTE_PACKAGE}")
            sftp.put(str(package_path), REMOTE_PACKAGE)
        finally:
            sftp.close()

        run(client, f"test -d {LIVE}", label="assert-live-dir", check=True, secrets=secrets)
        run(client, f"mkdir -p {BACKUP_DIR}", label="mkdir-backup", check=True, secrets=secrets)
        run(
            client,
            f"tar --exclude='{LIVE}/agent/.venv' --exclude='{LIVE}/build/agent-gateway' "
            f"--exclude='{LIVE}/data/*.db' -czf {BACKUP_DIR}/agent-platform-{TS}.tar.gz "
            f"-C /home/admin agent-platform",
            label="backup-live",
            timeout=240,
            check=True,
            secrets=secrets,
        )
        run(client, f"ls -lh {BACKUP_DIR}/agent-platform-{TS}.tar.gz", label="backup-size", secrets=secrets)

        run(client, f"rm -rf {STAGE} && mkdir -p {STAGE}", label="prepare-stage", timeout=120, check=True, secrets=secrets)
        run(client, f"tar -xzf {REMOTE_PACKAGE} -C {STAGE}", label="extract-package", timeout=180, check=True, secrets=secrets)

        for rel in PERSIST_PATHS:
            src = f"{LIVE}/{rel}"
            dst = f"{STAGE}/{rel}"
            run(
                client,
                f"if [ -e {remote_quote(src)} ]; then mkdir -p $(dirname {remote_quote(dst)}) && cp -a {remote_quote(src)} {remote_quote(dst)}; fi",
                label=f"persist-{rel}",
                timeout=180,
                check=False,
                secrets=secrets,
            )

        run(client, f"mkdir -p {STAGE}/logs {STAGE}/agent/data {STAGE}/build", label="ensure-runtime-dirs", check=True, secrets=secrets)
        run(
            client,
            f"cd {STAGE} && go build -o build/agent-gateway-new ./cmd/gateway",
            label="go-build",
            timeout=420,
            check=True,
            secrets=secrets,
        )
        run(
            client,
            f"cp -f {STAGE}/build/agent-gateway-new {STAGE}/build/agent-gateway && chmod +x {STAGE}/build/agent-gateway",
            label="install-gateway-binary",
            check=True,
            secrets=secrets,
        )
        rc, _, _ = run(
            client,
            python_module_check_command(f"{STAGE}/agent/.venv/bin/python"),
            label="python-module-check",
            timeout=120,
            check=False,
            secrets=secrets,
        )
        if rc != 0:
            run(
                client,
                f"{STAGE}/agent/.venv/bin/python -m ensurepip --upgrade",
                label="ensurepip",
                timeout=180,
                check=True,
                secrets=secrets,
            )
            run(
                client,
                pip_install_dependencies_command(f"{STAGE}/agent/.venv/bin/python"),
                label="pip-install-agent",
                timeout=300,
                check=True,
                secrets=secrets,
            )
            run(
                client,
                python_module_check_command(f"{STAGE}/agent/.venv/bin/python"),
                label="python-module-recheck",
                timeout=120,
                check=True,
                secrets=secrets,
            )
        run(
            client,
            f"cd {STAGE}/agent && ./.venv/bin/python -m py_compile app/knowledge/schemas.py app/knowledge/service.py app/rag/graphrag.py app/graph/nodes/rag_retrieval.py",
            label="remote-py-compile",
            timeout=120,
            check=True,
            secrets=secrets,
        )
        run(
            client,
            f"mkdir -p {HERMES_SKILLS_DIR} && cp -a {STAGE}/agent/skills/. {HERMES_SKILLS_DIR}/",
            label="sync-platform-skills",
            timeout=240,
            check=True,
            secrets=secrets,
        )

        run(client, "fuser -k 8080/tcp 2>/dev/null || true", label="stop-gateway", timeout=60, secrets=secrets)
        run(client, "fuser -k 8001/tcp 2>/dev/null || true", label="stop-agent", timeout=60, secrets=secrets)
        run(client, f"mv {LIVE} {LIVE}-prev-{TS} && mv {STAGE} {LIVE}", label="cutover", timeout=180, check=True, secrets=secrets)
        fire_and_forget(
            client,
            f"cd {LIVE}; nohup env GATEWAY_HOST=0.0.0.0 ./build/agent-gateway --config configs/config.yaml > logs/gateway.log 2>&1 < /dev/null &",
        )
        fire_and_forget(
            client,
            f"cd {LIVE}/agent; nohup env PYTHONUNBUFFERED=1 SKILLS_DIR=/home/admin/.hermes/skills ./.venv/bin/python main.py > ../logs/agent.log 2>&1 < /dev/null &",
        )
        fire_and_forget(
            client,
            f"cd {LIVE}/hermes-bridge; nohup env PYTHONPATH={LIVE}/hermes-bridge PYTHONUNBUFFERED=1 GSTACK_AUTOLOAD=1 {LIVE}/agent/.venv/bin/python main.py > /tmp/hermes-bridge.log 2>&1 < /dev/null &",
        )
        print("start commands sent")
        client.close()
        time.sleep(8)
        client = connect(config)

        checks = [
            ("processes", "pgrep -fa 'agent-gateway|agent/.venv/bin/python main.py'"),
            ("ports", "ss -tlnp | grep -E ':8080|:8001|:8002'"),
            ("gateway-health", "curl -fsS --max-time 5 http://127.0.0.1:8080/api/v1/health"),
            ("agent-health", "curl -fsS --max-time 5 http://127.0.0.1:8001/health"),
            ("hermes-health", "curl -fsS --max-time 5 http://127.0.0.1:8002/api/v2/health"),
            ("kg-stats-agent", "curl -fsS --max-time 8 http://127.0.0.1:8001/api/v1/knowledge-graph/stats"),
            ("frontend-index", f"test -f {LIVE}/web/dist/index.html && grep -o 'KnowledgeGraphPage[^\" ]*' {LIVE}/web/dist/index.html {LIVE}/web/dist/assets/*.js 2>/dev/null | head -5 || true"),
        ]
        for label, command in checks:
            run(client, command, label=label, timeout=60, check=True, secrets=secrets)

        run(client, f"rm -f {REMOTE_PACKAGE}", label="cleanup-package", timeout=60, secrets=secrets)
        print("=== DEPLOYMENT COMPLETE ===")
        print(f"Backup: {BACKUP_DIR}/agent-platform-{TS}.tar.gz")
        print(f"Previous live tree: {LIVE}-prev-{TS}")
        return 0
    except RemoteCommandError as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        print(f"[INFO] Live tree was backed up under {BACKUP_DIR}; inspect remote output above before retrying.", file=sys.stderr)
        return 2
    finally:
        client.close()
        try:
            package_path.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
