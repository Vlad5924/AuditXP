#!/usr/bin/env bash
# Восстановление БД AuditXP из резервной копии (*.backup или *.sql)
#   sudo ./restore.sh /opt/auditxp/db/backup/auditxp_demo.backup
set -euo pipefail
FILE=${1:?Укажите файл резервной копии}
DB_NAME=${DB_NAME:-auditxp}
DB_USER=${DB_USER:-auditxp}
systemctl stop auditxp-api 2>/dev/null || true
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DROP DATABASE IF EXISTS $DB_NAME;
CREATE DATABASE $DB_NAME WITH OWNER=$DB_USER ENCODING='UTF8'
    CONNECTION LIMIT=-1;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
SQL
case "$FILE" in
  *.sql) sudo -u postgres psql -d "$DB_NAME" < "$FILE" ;;
  *) sudo -u postgres pg_restore -v --no-owner --role="$DB_USER" \
         -d "$DB_NAME" "$FILE" ;;
esac
systemctl start auditxp-api 2>/dev/null || true
echo "База $DB_NAME восстановлена из $FILE"
