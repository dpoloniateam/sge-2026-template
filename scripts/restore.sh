#!/usr/bin/env bash
# Restaura uma cópia noutro ambiente (VM Azure <-> Codespaces <-> local).
# Uso: ./scripts/restore.sh backups/odoo_20261030-1200.dump [backups/odoo_20261030-1200_filestore.tgz] [DB]
set -euo pipefail
cd "$(dirname "$0")/.."
DUMP=${1:?indique o ficheiro .dump}; FS=${2:-}; DB=${3:-odoo}
docker compose up -d db; sleep 5
docker compose stop web
docker compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS \"$DB\";" -c "CREATE DATABASE \"$DB\" OWNER odoo;"
docker compose exec -T db pg_restore -U odoo -d "$DB" --no-owner < "$DUMP"
if [ -n "$FS" ]; then
  docker compose run --rm -T --entrypoint sh web -c "mkdir -p /var/lib/odoo/filestore && tar xzf - -C /var/lib/odoo/filestore" < "$FS"
fi
docker compose up -d
echo "Base '$DB' restaurada. Abra http://localhost:8069."
