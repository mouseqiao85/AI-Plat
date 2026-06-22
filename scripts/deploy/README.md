# Paramiko Deployment Scripts

These scripts use Paramiko to deploy or verify services on the remote host. Do not store SSH passwords, private keys, API keys, or copied shell history in this directory.

## Configure SSH credentials

The shared helper `ssh_config.py` reads credentials from local environment variables only. `DEPLOY_*` names take precedence; `PARAMIKO_*` aliases are supported for Secret Manager and CI naming.

Required target values:

```powershell
$env:DEPLOY_HOST = "8.215.63.182"
$env:DEPLOY_PORT = "22"
$env:DEPLOY_USER = "root"
```

Choose one authentication method.

Password auth:

```powershell
$env:DEPLOY_PASS = "<local secret>"
```

Key auth:

```powershell
$env:DEPLOY_KEY_FILE = "C:\Users\<user>\.ssh\deploy_key"
```

Equivalent aliases are also accepted:

```powershell
$env:PARAMIKO_HOST = "8.215.63.182"
$env:PARAMIKO_USERNAME = "root"
$env:PARAMIKO_PASSWORD = "<local secret>"
# or
$env:PARAMIKO_KEY_FILE = "C:\Users\<user>\.ssh\deploy_key"
```

## Preflight connectivity check

Before running a deployment script, verify the SSH configuration with:

```powershell
python scripts/deploy/check_ssh_connection.py
```

Expected success output is similar to:

```text
[preflight] target=root@8.215.63.182:22 auth=password timeout=20s
[OK] ssh-ok user=root host=<server-hostname>
```

Failure output is categorized and sanitized:

- invalid config: missing host/user/auth or invalid port/key path
- auth failure: wrong user/password/key
- timeout: host did not complete SSH connection in time
- network/ssh failure: connection refused, SSH negotiation failure, etc.

Do not paste secrets into Linear comments, terminal logs, screenshots, or frontend-visible output. For Linear verification notes, record only the target endpoint, auth method type (`password` or `key`), command labels, exit codes, and redacted errors.

## Supported scripts

The active deployment/monitoring scripts use `ssh_config.py`:

- `deploy_stage.py`
- `deploy_hermes_bridge.py`
- `deploy_skill_tabs.py`
- `deploy_cutover.py`
- `deploy_env_override.py`
- `../monitor_logs.py`
- `auto_deploy.py`

Historical one-off scripts in this directory may still exist for reference. They should not be used unless reviewed first.

## Local tests

```powershell
python -m pytest scripts/deploy/tests -q
python -m compileall -q scripts/deploy
python -m py_compile scripts/deploy/auto_deploy.py scripts/monitor_logs.py
```

## Security note

If a credential ever appeared in a committed file or shared document, rotate it. Removing the literal from the working tree does not remove exposure from previous copies or history.
