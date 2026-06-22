from __future__ import annotations

import os
import sys

import pytest

_test_dir = os.path.dirname(os.path.abspath(__file__))
_bridge_dir = os.path.join(_test_dir, "..")
sys.path.insert(0, _bridge_dir)

from bridge.sandbox_policy import (
    HIGH_SECURITY_SANDBOX_POLICY,
    SandboxPolicyError,
    effective_tool_names,
    filter_tool_schemas,
    normalize_policy,
)


def test_default_policy_normalizes_to_local_dev():
    policy = normalize_policy(None)

    assert policy["security_level"] == "local_dev"
    assert policy["network"]["allow_all"] is True
    assert policy["filesystem"]["mode"] == "workspace"
    assert policy["filesystem"]["read_paths"] == ["."]
    assert policy["filesystem"]["write_paths"] == ["."]


def test_partial_policy_merges_with_defaults():
    policy = normalize_policy({"filesystem": {"mode": "read_only"}})

    assert policy["security_level"] == "local_dev"
    assert policy["network"]["allow_all"] is True
    assert policy["filesystem"]["mode"] == "read_only"
    assert policy["filesystem"]["read_paths"] == ["."]
    assert policy["filesystem"]["write_paths"] == []


def test_high_security_policy_is_valid_and_filters_tools():
    policy = normalize_policy(HIGH_SECURITY_SANDBOX_POLICY)
    allowed = effective_tool_names(policy)

    assert policy["security_level"] == "high"
    assert "Bash" not in allowed
    assert "Write" not in allowed
    assert "Read" in allowed


def test_invalid_security_level_is_rejected():
    with pytest.raises(SandboxPolicyError, match="security_level"):
        normalize_policy({"security_level": "root"})


@pytest.mark.parametrize("field,value", [
    ("cpu_seconds", 0),
    ("cpu_seconds", -1),
    ("memory_mb", 1),
    ("disk_mb", "large"),
])
def test_invalid_resource_values_are_rejected(field: str, value):
    with pytest.raises(SandboxPolicyError, match=f"resources.{field}"):
        normalize_policy({"resources": {field: value}})


@pytest.mark.parametrize("domain", [
    "https://example.com",
    "example.com/path",
    "bad domain.com",
    "*bad.example.com",
    "localhost",
])
def test_invalid_domains_are_rejected(domain: str):
    with pytest.raises(SandboxPolicyError, match="domain"):
        normalize_policy({"network": {"allowed_domains": [domain]}})


@pytest.mark.parametrize("domain", ["example.com", "api.example.com", "*.example.com"])
def test_valid_domains_are_accepted(domain: str):
    policy = normalize_policy({"network": {"allowed_domains": [domain]}})

    assert policy["network"]["allowed_domains"] == [domain]


@pytest.mark.parametrize("value", ["999.999.999.999", "10.0.0.0/99", "not-an-ip"])
def test_invalid_ips_are_rejected(value: str):
    with pytest.raises(SandboxPolicyError, match="IP/CIDR"):
        normalize_policy({"network": {"denied_ips": [value]}})


@pytest.mark.parametrize("value", ["127.0.0.1", "10.0.0.0/8", "::1"])
def test_valid_ips_are_accepted(value: str):
    policy = normalize_policy({"network": {"denied_ips": [value]}})

    assert policy["network"]["denied_ips"]


def test_invalid_filesystem_mode_and_paths_are_rejected():
    with pytest.raises(SandboxPolicyError, match="filesystem.mode"):
        normalize_policy({"filesystem": {"mode": "root"}})

    with pytest.raises(SandboxPolicyError, match="escapes workspace"):
        normalize_policy({"filesystem": {"read_paths": ["../secret"]}})


def test_filter_tool_schemas_removes_denied_tools():
    schemas = [
        {"function": {"name": "Read"}},
        {"function": {"name": "Write"}},
        {"function": {"name": "Bash"}},
    ]

    filtered = filter_tool_schemas(schemas, HIGH_SECURITY_SANDBOX_POLICY)

    assert [schema["function"]["name"] for schema in filtered] == ["Read"]
