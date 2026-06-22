from __future__ import annotations

import socket
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ssh_config import (  # noqa: E402
    DeployConfigError,
    DeployConnectionError,
    DeploySSHConfig,
    RemoteCommandError,
    connect,
    load_deploy_config,
    run_remote,
)


ENV_KEYS = [
    "DEPLOY_HOST",
    "DEPLOY_PORT",
    "DEPLOY_USER",
    "DEPLOY_PASS",
    "DEPLOY_KEY_FILE",
    "DEPLOY_TIMEOUT",
    "DEPLOY_COMMAND_TIMEOUT",
    "DEPLOY_KNOWN_HOSTS_POLICY",
    "PARAMIKO_HOST",
    "PARAMIKO_PORT",
    "PARAMIKO_USERNAME",
    "PARAMIKO_PASSWORD",
    "PARAMIKO_KEY_FILE",
    "PARAMIKO_TIMEOUT",
    "PARAMIKO_COMMAND_TIMEOUT",
    "PARAMIKO_KNOWN_HOSTS_POLICY",
]


@pytest.fixture(autouse=True)
def _clear_deploy_env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_load_config_requires_auth(monkeypatch):
    monkeypatch.setenv("DEPLOY_HOST", "8.215.63.182")
    monkeypatch.setenv("DEPLOY_USER", "root")

    with pytest.raises(DeployConfigError, match="DEPLOY_PASS.*DEPLOY_KEY_FILE"):
        load_deploy_config()


def test_load_config_from_password_env(monkeypatch):
    monkeypatch.setenv("DEPLOY_HOST", "8.215.63.182")
    monkeypatch.setenv("DEPLOY_PORT", "2222")
    monkeypatch.setenv("DEPLOY_USER", "root")
    monkeypatch.setenv("DEPLOY_PASS", "secret-value")

    config = load_deploy_config()

    assert config.host == "8.215.63.182"
    assert config.port == 2222
    assert config.username == "root"
    assert config.password == "secret-value"
    assert config.auth_method == "password"
    assert "secret-value" not in repr(config)


def test_load_config_rejects_bad_port(monkeypatch):
    monkeypatch.setenv("DEPLOY_PASS", "secret-value")
    monkeypatch.setenv("DEPLOY_PORT", "not-a-port")

    with pytest.raises(DeployConfigError, match="DEPLOY_PORT"):
        load_deploy_config()


def test_load_config_supports_paramiko_aliases(monkeypatch):
    monkeypatch.setenv("PARAMIKO_HOST", "example.com")
    monkeypatch.setenv("PARAMIKO_PORT", "2200")
    monkeypatch.setenv("PARAMIKO_USERNAME", "deployer")
    monkeypatch.setenv("PARAMIKO_PASSWORD", "secret-value")
    monkeypatch.setenv("PARAMIKO_TIMEOUT", "11")
    monkeypatch.setenv("PARAMIKO_COMMAND_TIMEOUT", "33")

    config = load_deploy_config(default_host=None, default_user="")

    assert config.host == "example.com"
    assert config.port == 2200
    assert config.username == "deployer"
    assert config.password == "secret-value"
    assert config.timeout == 11
    assert config.command_timeout == 33


def test_deploy_env_takes_precedence_over_paramiko_alias(monkeypatch):
    monkeypatch.setenv("DEPLOY_HOST", "deploy.example.com")
    monkeypatch.setenv("PARAMIKO_HOST", "paramiko.example.com")
    monkeypatch.setenv("DEPLOY_PASS", "secret-value")

    config = load_deploy_config()

    assert config.host == "deploy.example.com"


def test_key_file_path_is_expanded_and_validated(monkeypatch, tmp_path):
    key_file = tmp_path / "deploy_key"
    key_file.write_text("fake-key", encoding="utf-8")
    monkeypatch.setenv("DEPLOY_KEY_FILE", str(key_file))

    config = load_deploy_config()

    assert config.key_filename == str(key_file)
    assert config.auth_method == "key"


def test_missing_key_file_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_KEY_FILE", str(tmp_path / "missing_key"))

    with pytest.raises(DeployConfigError, match="DEPLOY_KEY_FILE"):
        load_deploy_config()


class FakeChannel:
    def __init__(self, rc: int):
        self._rc = rc

    def recv_exit_status(self):
        return self._rc


class FakeStream:
    def __init__(self, data: str, rc: int = 0):
        self._data = data
        self.channel = FakeChannel(rc)

    def read(self):
        return self._data.encode("utf-8")


class FakeSSHClient:
    def __init__(self, *, connect_error=None, command_result=None):
        self.connect_error = connect_error
        self.command_result = command_result or (0, "", "")
        self.policy = None
        self.connect_kwargs = None

    def set_missing_host_key_policy(self, policy):
        self.policy = policy

    def connect(self, **kwargs):
        self.connect_kwargs = kwargs
        if self.connect_error:
            raise self.connect_error

    def exec_command(self, command, timeout=None):
        rc, out, err = self.command_result
        return None, FakeStream(out, rc), FakeStream(err, rc)


class FakeParamiko:
    class AuthenticationException(Exception):
        pass

    class SSHException(Exception):
        pass

    class AutoAddPolicy:
        pass

    class RejectPolicy:
        pass

    def __init__(self, client):
        self.client = client

    def SSHClient(self):
        return self.client


def test_connect_passes_config_to_paramiko():
    fake_client = FakeSSHClient()
    paramiko = FakeParamiko(fake_client)
    config = DeploySSHConfig(
        host="8.215.63.182",
        port=2222,
        username="root",
        password="secret-value",
        timeout=9,
    )

    client = connect(config, paramiko_module=paramiko)

    assert client is fake_client
    assert fake_client.connect_kwargs == {
        "hostname": "8.215.63.182",
        "port": 2222,
        "username": "root",
        "password": "secret-value",
        "key_filename": None,
        "timeout": 9,
        "banner_timeout": 9,
        "auth_timeout": 9,
        "look_for_keys": False,
    }


def test_connect_auth_failure_is_categorized():
    fake_client = FakeSSHClient(connect_error=FakeParamiko.AuthenticationException("bad secret-value"))
    paramiko = FakeParamiko(fake_client)
    config = DeploySSHConfig(host="8.215.63.182", username="root", password="secret-value")

    with pytest.raises(DeployConnectionError) as exc:
        connect(config, paramiko_module=paramiko)

    assert exc.value.category == "auth"
    assert "secret-value" not in str(exc.value)


def test_connect_timeout_is_categorized():
    fake_client = FakeSSHClient(connect_error=socket.timeout("timed out"))
    paramiko = FakeParamiko(fake_client)
    config = DeploySSHConfig(host="8.215.63.182", username="root", password="secret-value")

    with pytest.raises(DeployConnectionError) as exc:
        connect(config, paramiko_module=paramiko)

    assert exc.value.category == "timeout"
    assert "secret-value" not in str(exc.value)


def test_connect_network_failure_is_categorized():
    fake_client = FakeSSHClient(connect_error=OSError("connection refused secret-value"))
    paramiko = FakeParamiko(fake_client)
    config = DeploySSHConfig(host="8.215.63.182", username="root", password="secret-value")

    with pytest.raises(DeployConnectionError) as exc:
        connect(config, paramiko_module=paramiko)

    assert exc.value.category == "network"
    assert "secret-value" not in str(exc.value)


def test_run_remote_returns_exit_code_stdout_stderr():
    client = FakeSSHClient(command_result=(0, "ok", "warn"))

    rc, out, err = run_remote(client, "echo ok", print_output=False)

    assert rc == 0
    assert out == "ok"
    assert err == "warn"


def test_run_remote_raises_on_check_failure():
    client = FakeSSHClient(command_result=(7, "stdout", "stderr"))

    with pytest.raises(RemoteCommandError) as exc:
        run_remote(client, "false", label="fail-step", check=True, print_output=False)

    assert exc.value.exit_code == 7
    assert exc.value.label == "fail-step"


def test_run_remote_redacts_known_password_from_output():
    client = FakeSSHClient(command_result=(0, "secret-value in stdout", "secret-value in stderr"))

    _, out, err = run_remote(client, "show", print_output=False, secrets=["secret-value"])

    assert "secret-value" not in out
    assert "secret-value" not in err
    assert "<redacted>" in out
    assert "<redacted>" in err


def test_run_remote_truncates_large_output():
    client = FakeSSHClient(command_result=(0, "x" * 20, ""))

    _, out, _ = run_remote(client, "show", print_output=False, max_output_chars=5)

    assert out.startswith("xxxxx")
    assert "truncated" in out
