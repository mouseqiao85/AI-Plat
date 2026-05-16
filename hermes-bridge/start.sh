#!/bin/bash
# Hermes Bridge - use agent's venv python for uvicon/fastapi
cd "$(dirname "$0")"
exec /home/admin/agent-platform/agent/.venv/bin/python3 main.py
