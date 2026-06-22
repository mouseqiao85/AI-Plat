#!/usr/bin/env bash
set -euo pipefail

TS="$(date +%Y%m%d-%H%M%S)"
SRC="/home/admin/agent-platform/web/dist/"
DST="/var/www/chuansha.tech/"
BACKUP="/home/admin/backups/var-www-chuansha-tech-${TS}.tar.gz"

mkdir -p /home/admin/backups
if [ -d "$DST" ]; then
  tar -czf "$BACKUP" -C /var/www chuansha.tech
fi

mkdir -p "$DST"
find "$DST" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
tar -C "$SRC" -cf - . | tar -C "$DST" -xf -
caddy reload --config /etc/caddy/Caddyfile

grep -o 'assets/index-[^" ]*' "${DST}/index.html" | head -1
FLOW_CHUNK="$(find "${DST}/assets" -maxdepth 1 -name 'FlowsPage-*.js' | sort | tail -1)"
test -n "$FLOW_CHUNK"
grep -q '协作约束' "$FLOW_CHUNK"
grep -q 'role_contracts' "$FLOW_CHUNK"
grep -q '裁决规则' "$FLOW_CHUNK"
grep -q 'flow-collaboration-tabs' "$FLOW_CHUNK"
printf '%s\n' "$FLOW_CHUNK"
if [ -f "$BACKUP" ]; then
  ls -lh "$BACKUP"
fi
