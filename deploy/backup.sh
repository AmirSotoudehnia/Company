#!/usr/bin/env bash
set -euo pipefail

DB=${AGENT_COMPANY_DB:-/var/lib/agent-company/agent_company.db}
DEST=${BACKUP_DIR:-/var/backups/agent-company}
KEEP_DAYS=${BACKUP_KEEP_DAYS:-14}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$DEST/agent_company_$STAMP.db"

mkdir -p "$DEST"
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB" ".backup '$OUT'"
else
  cp "$DB" "$OUT"
fi
chmod 0600 "$OUT"
find "$DEST" -type f -name 'agent_company_*.db' -mtime +"$KEEP_DAYS" -delete
printf '%s\n' "$OUT"
