"""Application-level sandbox policy for Hermes flow tool execution."""
from __future__ import annotations

import ipaddress
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List

SECURITY_LEVELS = {"local_dev", "standard", "high"}
FILESYSTEM_MODES = {"workspace", "read_only", "none"}
FILE_TOOLS = {"Read", "Grep", "Glob", "Write"}
NETWORK_COMMANDS = {"curl", "wget", "ssh", "scp", "sftp", "ftp", "nc", "netcat"}
DESTRUCTIVE_COMMANDS = {
    "rm", "rmdir", "mv", "cp", "mkdir", "touch", "chmod", "chown",
    "git add", "git commit", "git push", "npm install", "pip install",
}

DEFAULT_SANDBOX_POLICY: Dict[str, Any] = {
    "security_level": "local_dev",
    "resources": {
        "cpu_seconds": None,
        "memory_mb": None,
        "disk_mb": None,
    },
    "network": {
        "allow_all": True,
        "allowed_domains": [],
        "denied_ips": [],
    },
    "filesystem": {
        "mode": "workspace",
        "read_paths": ["."],
        "write_paths": ["."],
    },
}

HIGH_SECURITY_SANDBOX_POLICY: Dict[str, Any] = {
    "security_level": "high",
    "resources": {
        "cpu_seconds": 60,
        "memory_mb": 512,
        "disk_mb": 256,
    },
    "network": {
        "allow_all": False,
        "allowed_domains": [],
        "denied_ips": ["0.0.0.0/0", "::/0"],
    },
    "filesystem": {
        "mode": "read_only",
        "read_paths": ["."],
        "write_paths": [],
    },
}

_DOMAIN_RE = re.compile(r"^(?:\*\.)?(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$")


class SandboxPolicyError(ValueError):
    """Raised when a sandbox policy is invalid or denies an operation."""


def _merge_dict(default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(default)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _validate_resource(name: str, value: Any, *, min_value: int, max_value: int) -> Any:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise SandboxPolicyError(f"resources.{name} must be a positive integer or null")
    if value < min_value or value > max_value:
        raise SandboxPolicyError(f"resources.{name} must be between {min_value} and {max_value}")
    return value


def _validate_domain(domain: Any) -> str:
    if not isinstance(domain, str) or not domain:
        raise SandboxPolicyError("network.allowed_domains entries must be non-empty strings")
    if "://" in domain or "/" in domain or any(ch.isspace() for ch in domain):
        raise SandboxPolicyError(f"invalid domain: {domain}")
    if "*" in domain and not domain.startswith("*."):
        raise SandboxPolicyError(f"invalid wildcard domain: {domain}")
    if not _DOMAIN_RE.match(domain):
        raise SandboxPolicyError(f"invalid domain: {domain}")
    return domain.lower()


def _validate_ip_or_network(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise SandboxPolicyError("network.denied_ips entries must be non-empty strings")
    try:
        if "/" in value:
            return str(ipaddress.ip_network(value, strict=False))
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise SandboxPolicyError(f"invalid IP/CIDR: {value}") from exc


def _validate_policy_path(path: Any) -> str:
    if not isinstance(path, str) or not path:
        raise SandboxPolicyError("filesystem paths must be non-empty strings")
    if "\x00" in path:
        raise SandboxPolicyError("filesystem paths cannot contain NUL bytes")
    parts = Path(path).parts
    if ".." in parts:
        raise SandboxPolicyError(f"filesystem path escapes workspace: {path}")
    return path


def normalize_policy(policy: Dict[str, Any] | None) -> Dict[str, Any]:
    if policy is None:
        raw: Dict[str, Any] = {}
    elif isinstance(policy, dict):
        raw = policy
    else:
        raise SandboxPolicyError("sandbox_policy must be an object")

    merged = _merge_dict(DEFAULT_SANDBOX_POLICY, raw)

    level = merged.get("security_level")
    if level not in SECURITY_LEVELS:
        raise SandboxPolicyError(f"security_level must be one of {sorted(SECURITY_LEVELS)}")

    resources = merged.get("resources")
    if not isinstance(resources, dict):
        raise SandboxPolicyError("resources must be an object")
    resources["cpu_seconds"] = _validate_resource("cpu_seconds", resources.get("cpu_seconds"), min_value=1, max_value=86400)
    resources["memory_mb"] = _validate_resource("memory_mb", resources.get("memory_mb"), min_value=16, max_value=262144)
    resources["disk_mb"] = _validate_resource("disk_mb", resources.get("disk_mb"), min_value=1, max_value=1048576)

    network = merged.get("network")
    if not isinstance(network, dict):
        raise SandboxPolicyError("network must be an object")
    if not isinstance(network.get("allow_all"), bool):
        raise SandboxPolicyError("network.allow_all must be a boolean")
    allowed_domains = network.get("allowed_domains") or []
    denied_ips = network.get("denied_ips") or []
    if not isinstance(allowed_domains, list):
        raise SandboxPolicyError("network.allowed_domains must be a list")
    if not isinstance(denied_ips, list):
        raise SandboxPolicyError("network.denied_ips must be a list")
    network["allowed_domains"] = [_validate_domain(domain) for domain in allowed_domains]
    network["denied_ips"] = [_validate_ip_or_network(ip) for ip in denied_ips]

    filesystem = merged.get("filesystem")
    if not isinstance(filesystem, dict):
        raise SandboxPolicyError("filesystem must be an object")
    mode = filesystem.get("mode")
    if mode not in FILESYSTEM_MODES:
        raise SandboxPolicyError(f"filesystem.mode must be one of {sorted(FILESYSTEM_MODES)}")
    read_paths = filesystem.get("read_paths") or []
    write_paths = filesystem.get("write_paths") or []
    if not isinstance(read_paths, list):
        raise SandboxPolicyError("filesystem.read_paths must be a list")
    if not isinstance(write_paths, list):
        raise SandboxPolicyError("filesystem.write_paths must be a list")
    filesystem["read_paths"] = [_validate_policy_path(path) for path in read_paths]
    filesystem["write_paths"] = [_validate_policy_path(path) for path in write_paths]
    if mode == "none":
        filesystem["read_paths"] = []
        filesystem["write_paths"] = []
    if mode == "read_only":
        filesystem["write_paths"] = []

    return merged


def effective_tool_names(policy: Dict[str, Any] | None) -> set[str]:
    normalized = normalize_policy(policy)
    allowed = {"Read", "Bash", "Grep", "Glob", "Write", "git_status", "git_diff"}
    level = normalized["security_level"]
    fs_mode = normalized["filesystem"]["mode"]
    network = normalized["network"]

    if fs_mode == "none":
        allowed -= FILE_TOOLS
        allowed.discard("Bash")
    elif fs_mode == "read_only":
        allowed.discard("Write")

    if level == "high":
        allowed.discard("Bash")
        allowed.discard("Write")

    if not network.get("allow_all", True) and not network.get("allowed_domains"):
        allowed.discard("Bash")

    return allowed


def filter_tool_schemas(tool_schemas: List[Dict[str, Any]], policy: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    allowed = effective_tool_names(policy)
    return [schema for schema in tool_schemas if schema.get("function", {}).get("name") in allowed]


def ensure_tool_allowed(name: str, policy: Dict[str, Any] | None) -> Dict[str, Any]:
    normalized = normalize_policy(policy)
    if name not in effective_tool_names(normalized):
        raise SandboxPolicyError(f"tool denied by sandbox policy: {name}")
    return normalized


def _resolved_allowed_roots(paths: Iterable[str], workdir: str) -> List[Path]:
    base = Path(workdir).resolve()
    roots: List[Path] = []
    for raw in paths:
        path = Path(raw)
        candidate = path.resolve() if path.is_absolute() else (base / path).resolve()
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise SandboxPolicyError(f"sandbox policy path escapes workspace: {raw}") from exc
        roots.append(candidate)
    return roots or [base]


def resolve_policy_path(requested_path: str, workdir: str, policy: Dict[str, Any] | None, *, operation: str) -> str:
    normalized = normalize_policy(policy)
    filesystem = normalized["filesystem"]
    mode = filesystem["mode"]
    if mode == "none":
        raise SandboxPolicyError(f"filesystem {operation} denied by sandbox policy")
    if operation == "write" and mode == "read_only":
        raise SandboxPolicyError("filesystem write denied by read-only sandbox policy")

    if not requested_path:
        requested_path = "."
    if "\x00" in requested_path:
        raise SandboxPolicyError("path cannot contain NUL bytes")

    base = Path(workdir).resolve()
    path = Path(requested_path)
    resolved = path.resolve() if path.is_absolute() else (base / path).resolve()

    raw_paths = filesystem["write_paths"] if operation == "write" else filesystem["read_paths"]
    allowed_roots = _resolved_allowed_roots(raw_paths, workdir)
    for root in allowed_roots:
        if resolved == root or root in resolved.parents:
            return str(resolved)
    raise SandboxPolicyError(f"{operation} denied outside sandbox workspace: {requested_path}")


def validate_write_size(content: str, policy: Dict[str, Any] | None) -> None:
    normalized = normalize_policy(policy)
    disk_mb = normalized["resources"].get("disk_mb")
    if disk_mb is None:
        return
    max_bytes = disk_mb * 1024 * 1024
    if len(content.encode("utf-8")) > max_bytes:
        raise SandboxPolicyError(f"write denied: content exceeds disk limit of {disk_mb}MB")


def validate_bash_command(command: str, policy: Dict[str, Any] | None) -> None:
    normalized = normalize_policy(policy)
    level = normalized["security_level"]
    filesystem = normalized["filesystem"]
    network = normalized["network"]
    lowered = command.lower()

    if level == "high" or filesystem["mode"] == "none":
        raise SandboxPolicyError("Bash denied by sandbox policy")

    if filesystem["mode"] == "read_only":
        if ">" in command:
            raise SandboxPolicyError("Bash redirection denied by read-only sandbox policy")
        for token in DESTRUCTIVE_COMMANDS:
            if re.search(rf"(^|[;&|\s]){re.escape(token)}($|[;&|\s])", lowered):
                raise SandboxPolicyError(f"Bash command denied by read-only sandbox policy: {token}")

    if not network.get("allow_all", True):
        for token in NETWORK_COMMANDS:
            if re.search(rf"(^|[;&|\s]){re.escape(token)}($|[;&|\s])", lowered):
                raise SandboxPolicyError(f"network command denied by sandbox policy: {token}")


def bash_timeout(policy: Dict[str, Any] | None, default_timeout: int = 60) -> int:
    normalized = normalize_policy(policy)
    cpu_seconds = normalized["resources"].get("cpu_seconds")
    if cpu_seconds is None:
        return default_timeout
    return max(1, min(default_timeout, int(cpu_seconds)))
