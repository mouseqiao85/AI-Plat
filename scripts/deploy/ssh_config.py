"""Shared SSH configuration helpers for Paramiko deployment scripts.

Credentials are loaded from local environment variables only. This module keeps
connection diagnostics useful while avoiding printing deployment secrets.
"""
from __future__ import annotations

import importlib
import os
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal

ConnectionCategory = Literal["auth", "timeout", "network", "ssh", "unknown"]


class DeployConfigError(ValueError):
    """Raised when local deployment SSH configuration is missing or invalid."""


class DeployConnectionError(RuntimeError):
    """Raised when SSH connection setup fails with a sanitized diagnostic."""

    def __init__(self, category: ConnectionCategory, endpoint: str, message: str):
        self.category = category
        self.endpoint = endpoint
        self.detail = message
        super().__init__(f"SSH {category} error for {endpoint}: {message}")


class RemoteCommandError(RuntimeError):
    """Raised when a checked remote command exits with a non-zero status."""

    def __init__(self, label: str, exit_code: int, stdout: str, stderr: str):
        self.label = label or "remote-command"
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        detail = stderr or stdout or "no output"
        super().__init__(f"Remote command failed [{self.label}] with exit code {exit_code}: {detail}")


@dataclass(frozen=True)
class DeploySSHConfig:
    host: str
    port: int = 22
    username: str = "root"
    password: str | None = field(default=None, repr=False)
    key_filename: str | None = None
    timeout: int = 20
    command_timeout: int = 120
    known_hosts_policy: str = "auto_add"

    @property
    def endpoint(self) -> str:
        return f"{self.username}@{self.host}:{self.port}"

    @property
    def auth_method(self) -> str:
        if self.key_filename:
            return "key"
        if self.password:
            return "password"
        return "none"


def _env(primary: str, *aliases: str) -> str | None:
    for name in (primary, *aliases):
        value = os.getenv(name)
        if value is not None and value.strip() != "":
            return value
    return None


def _env_label(primary: str, aliases: tuple[str, ...]) -> str:
    if not aliases:
        return primary
    return f"{primary} ({' or '.join(aliases)})"


def _parse_int_env(
    name: str,
    default: int,
    *,
    aliases: tuple[str, ...] = (),
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    raw = _env(name, *aliases)
    label = _env_label(name, aliases)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise DeployConfigError(f"{label} must be an integer") from exc
    if value < minimum or (maximum is not None and value > maximum):
        if maximum is None:
            raise DeployConfigError(f"{label} must be >= {minimum}")
        raise DeployConfigError(f"{label} must be between {minimum} and {maximum}")
    return value


def load_deploy_config(
    *,
    default_host: str | None = "8.215.63.182",
    default_user: str = "root",
    require_auth: bool = True,
) -> DeploySSHConfig:
    """Load deployment SSH configuration from environment variables.

    Supported variables:
      DEPLOY_HOST/PARAMIKO_HOST, DEPLOY_PORT/PARAMIKO_PORT,
      DEPLOY_USER/PARAMIKO_USERNAME, DEPLOY_PASS/PARAMIKO_PASSWORD,
      DEPLOY_KEY_FILE/PARAMIKO_KEY_FILE, DEPLOY_TIMEOUT/PARAMIKO_TIMEOUT,
      DEPLOY_COMMAND_TIMEOUT, DEPLOY_KNOWN_HOSTS_POLICY.
    """

    host = (_env("DEPLOY_HOST", "PARAMIKO_HOST") or default_host or "").strip()
    username = (_env("DEPLOY_USER", "PARAMIKO_USERNAME") or default_user or "").strip()
    password = _env("DEPLOY_PASS", "PARAMIKO_PASSWORD")
    key_filename = _env("DEPLOY_KEY_FILE", "PARAMIKO_KEY_FILE")

    if not host:
        raise DeployConfigError("DEPLOY_HOST or PARAMIKO_HOST is required")
    if not username:
        raise DeployConfigError("DEPLOY_USER or PARAMIKO_USERNAME is required")

    port = _parse_int_env("DEPLOY_PORT", 22, aliases=("PARAMIKO_PORT",), minimum=1, maximum=65535)
    timeout = _parse_int_env("DEPLOY_TIMEOUT", 20, aliases=("PARAMIKO_TIMEOUT",), minimum=1)
    command_timeout = _parse_int_env("DEPLOY_COMMAND_TIMEOUT", 120, aliases=("PARAMIKO_COMMAND_TIMEOUT",), minimum=1)
    known_hosts_policy = (_env("DEPLOY_KNOWN_HOSTS_POLICY", "PARAMIKO_KNOWN_HOSTS_POLICY") or "auto_add").strip().lower()
    if known_hosts_policy not in {"auto_add", "reject"}:
        raise DeployConfigError("DEPLOY_KNOWN_HOSTS_POLICY must be auto_add or reject")

    if key_filename:
        key_path = Path(key_filename).expanduser()
        if not key_path.exists():
            raise DeployConfigError("DEPLOY_KEY_FILE or PARAMIKO_KEY_FILE does not exist")
        key_filename = str(key_path)

    if require_auth and not password and not key_filename:
        raise DeployConfigError("set DEPLOY_PASS/PARAMIKO_PASSWORD or DEPLOY_KEY_FILE/PARAMIKO_KEY_FILE before running deployment scripts")

    return DeploySSHConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        key_filename=key_filename,
        timeout=timeout,
        command_timeout=command_timeout,
        known_hosts_policy=known_hosts_policy,
    )


def redact_text(text: str, secrets: Iterable[str] = ()) -> str:
    """Replace known secret values in text with a redaction marker."""

    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "<redacted>")
    return redacted


def _truncate(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    return f"{text[:limit]}\n... <truncated {len(text) - limit} chars>"


def _policy(paramiko_module, config: DeploySSHConfig):
    if config.known_hosts_policy == "reject":
        return paramiko_module.RejectPolicy()
    return paramiko_module.AutoAddPolicy()


def connect(config: DeploySSHConfig, *, paramiko_module=None):
    """Create and connect a Paramiko SSHClient using sanitized error handling."""

    pm = paramiko_module or importlib.import_module("paramiko")
    client = pm.SSHClient()
    client.set_missing_host_key_policy(_policy(pm, config))

    try:
        client.connect(
            hostname=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            key_filename=config.key_filename,
            timeout=config.timeout,
            banner_timeout=config.timeout,
            auth_timeout=config.timeout,
            look_for_keys=not bool(config.password or config.key_filename),
        )
        return client
    except getattr(pm, "AuthenticationException", Exception) as exc:
        raise DeployConnectionError("auth", config.endpoint, "authentication failed; check DEPLOY_USER and auth method") from exc
    except (socket.timeout, TimeoutError) as exc:
        raise DeployConnectionError("timeout", config.endpoint, f"timed out after {config.timeout}s") from exc
    except getattr(pm, "SSHException", Exception) as exc:
        msg = redact_text(str(exc), [config.password or ""])
        raise DeployConnectionError("ssh", config.endpoint, msg or "SSH negotiation failed") from exc
    except OSError as exc:
        msg = redact_text(str(exc), [config.password or ""])
        raise DeployConnectionError("network", config.endpoint, msg or "network failure") from exc
    except Exception as exc:  # pragma: no cover - final safety net
        msg = redact_text(str(exc), [config.password or ""])
        raise DeployConnectionError("unknown", config.endpoint, msg or "unknown connection failure") from exc


def connect_from_env(**kwargs):
    config = load_deploy_config(**kwargs)
    return connect(config)


def run_remote(
    client,
    command: str,
    *,
    timeout: int | None = None,
    label: str = "",
    check: bool = False,
    print_output: bool = True,
    max_output_chars: int = 4000,
    secrets: Iterable[str] = (),
) -> tuple[int, str, str]:
    """Run a remote command and return sanitized stdout/stderr."""

    display = f"$ [{label}] {command}" if label else f"$ {command}"
    if print_output:
        print(display)

    _, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()

    safe_out = _truncate(redact_text(out, secrets), max_output_chars)
    safe_err = _truncate(redact_text(err, secrets), max_output_chars)

    if print_output:
        if safe_out.rstrip():
            print(safe_out.rstrip())
        if safe_err.rstrip():
            print(f"[stderr] {safe_err.rstrip()}")
        print(f"[exit={rc}]\n")

    if check and rc != 0:
        raise RemoteCommandError(label, rc, safe_out, safe_err)

    return rc, safe_out, safe_err
