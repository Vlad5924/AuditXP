#!/usr/bin/env bash
# Формирование дистрибутива auditxp-<версия>.tar.gz (запуск из корня проекта)
set -euo pipefail
VERSION=${VERSION:-1.0.0}
NAME=auditxp-$VERSION
OUT=${OUT:-dist}
(cd frontend && npm ci && npm run build)
rm -rf "$OUT/$NAME" && mkdir -p "$OUT/$NAME/frontend"
cp -r backend "$OUT/$NAME/backend"
rm -rf "$OUT/$NAME/backend/tests" "$OUT/$NAME/backend/.env" \
       "$OUT/$NAME/backend/.coverage" \
       "$OUT/$NAME"/backend/*.db* "$OUT/$NAME/backend/outbox"
find "$OUT/$NAME" -name "__pycache__" -prune -exec rm -rf {} +
find "$OUT/$NAME" -name ".pytest_cache" -prune -exec rm -rf {} +
find "$OUT/$NAME" -name ".ruff_cache" -prune -exec rm -rf {} +
cp -r frontend/dist "$OUT/$NAME/frontend/dist"
cp -r db deploy README.md "$OUT/$NAME/"
tar -czf "$OUT/$NAME.tar.gz" -C "$OUT" "$NAME"
(cd "$OUT" && sha256sum "$NAME.tar.gz" > "$NAME.tar.gz.sha256")
echo "Дистрибутив $OUT/$NAME.tar.gz"
