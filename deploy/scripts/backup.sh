#!/usr/bin/env bash
# Резервное копирование БД AuditXP (cron, ежедневно в 02:00)
#   0 2 * * * postgres /opt/auditxp/deploy/scripts/backup.sh
set -euo pipefail
TARGET=${BACKUP_DIR:-/var/backups/auditxp}
DB_NAME=${DB_NAME:-auditxp}
KEEP_DAYS=${KEEP_DAYS:-30}
mkdir -p "$TARGET"
STAMP=$(date +%Y%m%d_%H%M)
FILE="$TARGET/${DB_NAME}_$STAMP.backup"
pg_dump -Fc -d "$DB_NAME" -f "$FILE"
find "$TARGET" -name "${DB_NAME}_*.backup" -mtime +"$KEEP_DAYS" -delete
echo "Резервная копия $FILE ($(du -h "$FILE" | cut -f1))"
