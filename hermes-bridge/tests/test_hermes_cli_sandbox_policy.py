from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_test_dir = os.path.dirname(os.path.abspath(__file__))
_bridge_dir = os.path.join(_test_dir, "..")
sys.path.insert(0, _bridge_dir)

from bridge.hermes_cli import _execute_tool
from bridge.sandbox_policy import HIGH_SECURITY_SANDBOX_POLICY


def test_default_policy_allows_read_and_write_in_workdir():
    with tempfile.TemporaryDirectory() as tmp:
        result = _execute_tool("Write", {"file_path": "note.txt", "content": "hello"}, workdir=tmp)
        assert "Wrote" in result

        read = _execute_tool("Read", {"file_path": "note.txt"}, workdir=tmp)
        assert read == "hello"


def test_high_policy_denies_bash_and_write():
    with tempfile.TemporaryDirectory() as tmp:
        bash = _execute_tool("Bash", {"command": "echo hello"}, workdir=tmp, sandbox_policy=HIGH_SECURITY_SANDBOX_POLICY)
        write = _execute_tool("Write", {"file_path": "note.txt", "content": "hello"}, workdir=tmp, sandbox_policy=HIGH_SECURITY_SANDBOX_POLICY)

        assert "tool denied" in bash
        assert "tool denied" in write


def test_read_only_policy_allows_read_but_denies_write():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "note.txt"
        path.write_text("hello", encoding="utf-8")
        policy = {"filesystem": {"mode": "read_only"}}

        read = _execute_tool("Read", {"file_path": "note.txt"}, workdir=tmp, sandbox_policy=policy)
        write = _execute_tool("Write", {"file_path": "other.txt", "content": "x"}, workdir=tmp, sandbox_policy=policy)

        assert read == "hello"
        assert "tool denied" in write


def test_file_tools_deny_paths_outside_workdir():
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
        outside_file = Path(outside) / "secret.txt"
        outside_file.write_text("secret", encoding="utf-8")
        policy = {"security_level": "standard"}

        read = _execute_tool("Read", {"file_path": str(outside_file)}, workdir=tmp, sandbox_policy=policy)
        grep = _execute_tool("Grep", {"pattern": "secret", "path": str(outside_file)}, workdir=tmp, sandbox_policy=policy)
        glob = _execute_tool("Glob", {"pattern": "*.txt", "path": outside}, workdir=tmp, sandbox_policy=policy)
        write = _execute_tool("Write", {"file_path": "../escape.txt", "content": "x"}, workdir=tmp, sandbox_policy=policy)

        assert "outside sandbox workspace" in read
        assert "outside sandbox workspace" in grep
        assert "outside sandbox workspace" in glob
        assert "outside sandbox workspace" in write


def test_network_restricted_policy_denies_obvious_network_commands():
    with tempfile.TemporaryDirectory() as tmp:
        policy = {"network": {"allow_all": False}}

        result = _execute_tool("Bash", {"command": "curl https://example.com"}, workdir=tmp, sandbox_policy=policy)

        assert "tool denied" in result or "network command denied" in result


def test_disk_limit_denies_large_write():
    with tempfile.TemporaryDirectory() as tmp:
        policy = {"resources": {"disk_mb": 1}}
        content = "x" * (1024 * 1024 + 1)

        result = _execute_tool("Write", {"file_path": "big.txt", "content": content}, workdir=tmp, sandbox_policy=policy)

        assert "exceeds disk limit" in result
