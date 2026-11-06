#!/usr/bin/env bash
# AuditXP. Запуск в Linux или macOS с базой SQLite и демо-данными
set -euo pipefail
cd "$(dirname "$0")/backend"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
[ -f ../frontend/dist/index.html ] || (cd ../frontend && npm ci && npm run build)
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
