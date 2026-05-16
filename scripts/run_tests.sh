#!/bin/bash
set -e

echo "=== Running Go tests ==="
cd "$(dirname "$0")/.."
GOPROXY=https://goproxy.cn,direct go test ./... -v -count=1

echo ""
echo "=== Running Python tests ==="
cd agent
python -m pytest tests/ -v --tb=short

echo ""
echo "=== All tests passed ==="
