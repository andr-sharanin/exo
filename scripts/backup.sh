#!/usr/bin/env bash
# ExoCortex database backup — run via cron or manually.
#
# Usage:
#   ./scripts/backup.sh
#
# Cron (daily at 3 AM):
#   0 3 * * * /path/to/exocortex/scripts/backup.sh >> /var/log/exocortex-backup.log 2>&1
#
# Keeps last 14 daily backups. Backups stored in ./backups/

set -euo pipefail

BACKUP_DIR="$(dirname "$0")/../backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
KEEP_DAYS=14

# Load env vars from .env if present
if [ -f "$(dirname "$0")/../.env" ]; then
  # shellcheck disable=SC1091
  set -o allexport
  source "$(dirname "$0")/../.env"
  set +o allexport
fi

POSTGRES_USER="${POSTGRES_USER:-exocortex}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
CONTAINER="${POSTGRES_CONTAINER:-exocortex20-postgres-1}"

mkdir -p "$BACKUP_DIR"

BACKUP_FILE="$BACKUP_DIR/exocortex_${TIMESTAMP}.sql.gz"

echo "[$(date -u +%FT%TZ)] Starting backup → $BACKUP_FILE"

PGPASSWORD="$POSTGRES_PASSWORD" docker exec "$CONTAINER" \
  pg_dump -U "$POSTGRES_USER" -d exocortex --no-owner --no-acl \
  | gzip > "$BACKUP_FILE"

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "[$(date -u +%FT%TZ)] Backup complete — $SIZE"

# Prune backups older than KEEP_DAYS
find "$BACKUP_DIR" -name "exocortex_*.sql.gz" -mtime +"$KEEP_DAYS" -delete
REMAINING=$(find "$BACKUP_DIR" -name "exocortex_*.sql.gz" | wc -l)
echo "[$(date -u +%FT%TZ)] Pruned old backups — $REMAINING backup(s) retained"
