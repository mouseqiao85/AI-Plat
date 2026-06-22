from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

DEPLOY_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEPLOY_DIR))

from ssh_config import DeployConfigError, DeployConnectionError, DeploySSHConfig  # noqa: E402


def _load_module():
    spec = importlib.util.spec_from_file_location("check_ssh_connection", DEPLOY_DIR / "check_ssh_connection.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_preflight_reports_missing_config_without_secret(monkeypatch, capsys):
    module = _load_module()
    monkeypatch.setattr(module, "load_deploy_config", lambda **_: (_ for _ in ()).throw(DeployConfigError("missing authentication")))

    rc = module.main()

    captured = capsys.readouterr()
    assert rc == 2
    assert "Invalid SSH config" in captured.err
    assert "missing authentication" in captured.err
    assert "secret-value" not in captured.out
    assert "secret-value" not in captured.err


def test_preflight_connection_failure_is_sanitized(monkeypatch, capsys):
    module = _load_module()
    config = DeploySSHConfig(host="8.215.63.182", username="root", password="secret-value")
    monkeypatch.setattr(module, "load_deploy_config", lambda **_: config)
    monkeypatch.setattr(
        module,
        "connect",
        lambda _: (_ for _ in ()).throw(
            DeployConnectionError("auth", config.endpoint, "authentication failed; check DEPLOY_USER and auth method")
        ),
    )

    rc = module.main()

    captured = capsys.readouterr()
    assert rc == 3
    assert "SSH auth error" in captured.err
    assert "secret-value" not in captured.out
    assert "secret-value" not in captured.err


def test_preflight_success_closes_client_and_prints_ok(monkeypatch, capsys):
    module = _load_module()
    config = DeploySSHConfig(host="8.215.63.182", username="root", password="secret-value")
    client = FakeClient()
    monkeypatch.setattr(module, "load_deploy_config", lambda **_: config)
    monkeypatch.setattr(module, "connect", lambda _: client)
    monkeypatch.setattr(module, "run_remote", lambda *_, **__: (0, "ssh-ok user=root host=server\n", ""))

    rc = module.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert client.closed is True
    assert "[OK] ssh-ok user=root host=server" in captured.out
    assert "secret-value" not in captured.out
    assert "secret-value" not in captured.err


def test_preflight_remote_command_failure_closes_client(monkeypatch, capsys):
    module = _load_module()
    config = DeploySSHConfig(host="8.215.63.182", username="root", password="secret-value")
    client = FakeClient()
    monkeypatch.setattr(module, "load_deploy_config", lambda **_: config)
    monkeypatch.setattr(module, "connect", lambda _: client)
    monkeypatch.setattr(module, "run_remote", lambda *_, **__: (7, "", "remote failed"))

    rc = module.main()

    captured = capsys.readouterr()
    assert rc == 4
    assert client.closed is True
    assert "Remote preflight command failed" in captured.err
    assert "secret-value" not in captured.out
    assert "secret-value" not in captured.err
