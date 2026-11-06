#!/usr/bin/env bash
# Установка AuditXP на Ubuntu Server 24.04 LTS из дистрибутива
#   sudo DB_PASSWORD=... ./install.sh auditxp-1.0.0.tar.gz
set -euo pipefail
DIST=${1:-auditxp-1.0.0.tar.gz}
PREFIX=/opt/auditxp
DB_NAME=${DB_NAME:-auditxp}
DB_USER=${DB_USER:-auditxp}
DB_PASSWORD=${DB_PASSWORD:?Укажите пароль БД в переменной DB_PASSWORD}

echo "1. Установка системных компонентов"
apt-get update
apt-get install -y python3 python3-venv postgresql nginx openssl

echo "2. Распаковка дистрибутива в $PREFIX"
id auditxp >/dev/null 2>&1 || useradd --system --home "$PREFIX" \
    --shell /usr/sbin/nologin auditxp
mkdir -p "$PREFIX"
tar -xzf "$DIST" -C "$PREFIX" --strip-components=1 --no-same-owner

echo "3. Виртуальное окружение Python и зависимости"
python3 -m venv "$PREFIX/venv"
"$PREFIX/venv/bin/pip" install --upgrade pip
"$PREFIX/venv/bin/pip" install -r "$PREFIX/backend/requirements.txt"

echo "4. Создание базы данных"
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
    CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD';
  END IF;
END \$\$;
CREATE DATABASE $DB_NAME WITH OWNER=$DB_USER ENCODING='UTF8'
    CONNECTION LIMIT=-1;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
SQL

echo "5. Файл настроек"
if [ ! -f "$PREFIX/backend/.env" ]; then
  sed -e "s#CHANGE_ME@localhost#$DB_PASSWORD@localhost#" \
      -e "s#JWT_SECRET=.*#JWT_SECRET=$(openssl rand -hex 32)#" \
      -e "s#SIGNATURE_SECRET=.*#SIGNATURE_SECRET=$(openssl rand -hex 32)#" \
      "$PREFIX/backend/.env.example" > "$PREFIX/backend/.env"
  chmod 600 "$PREFIX/backend/.env"
fi
chown -R auditxp:auditxp "$PREFIX"

echo "6. Схема БД, справочники и представления"
cd "$PREFIX/backend"
sudo -u auditxp "$PREFIX/venv/bin/python" -m app.cli init-db
PGPASSWORD=$DB_PASSWORD psql -h localhost -U "$DB_USER" -d "$DB_NAME" \
    -f "$PREFIX/db/02_views.sql"

echo "7. Служба API и веб-сервер"
CERT=/etc/ssl/auditxp
if [ ! -f "$CERT/auditxp.crt" ]; then
  echo "Сертификат не найден, создается временный самоподписанный"
  mkdir -p "$CERT"
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
      -subj "/CN=auditxp.goldberg-soft.by" \
      -keyout "$CERT/auditxp.key" -out "$CERT/auditxp.crt"
  chmod 600 "$CERT/auditxp.key"
fi
install -m 644 "$PREFIX/deploy/systemd/auditxp-api.service" \
    /etc/systemd/system/auditxp-api.service
install -m 644 "$PREFIX/deploy/nginx/auditxp.conf" \
    /etc/nginx/sites-available/auditxp.conf
ln -sf /etc/nginx/sites-available/auditxp.conf \
    /etc/nginx/sites-enabled/auditxp.conf
rm -f /etc/nginx/sites-enabled/default
systemctl daemon-reload
systemctl enable --now auditxp-api
nginx -t && systemctl reload nginx

echo "Установка завершена. Создайте администратора командой"
echo "  cd $PREFIX/backend && sudo -u auditxp ../venv/bin/python -m app.cli create-admin --email admin@goldberg-soft.by"
