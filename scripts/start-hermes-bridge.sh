#!/bin/bash
cd /home/admin/agent-platform/hermes-bridge
source /home/admin/agent-platform/agent/.venv/bin/activate
pip install -r requirements.txt -q
nohup python main.py > /tmp/hermes-bridge.log 2>&1 &
echo "Hermes Bridge PID: $!"
