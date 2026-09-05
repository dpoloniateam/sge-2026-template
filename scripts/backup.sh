#!/usr/bin/env bash
# Cópia de segurança da base e do filestore (Odoo Community em Docker Compose). Uso: ./scripts/backup.sh [DB]
set -euo pipefail
cd "$(dirname "$0")/.."
DB=${1:-${DB:-odoo}}; STAMP=$(date +%Y%m%d-%H%M); mkdir -p backups
docker compose exec -T db pg_dump -U odoo -Fc "$DB" > "backups/${DB}_${STAMP}.dump"
docker compose exec -T web tar czf - -C /var/lib/odoo/filestore "$DB" > "backups/${DB}_${STAMP}_filestore.tgz" || echo "aviso: filestore vazio ou inexistente"
ls -lh backups | tail -n 2
echo "Guarde estes dois ficheiros fora da VM (Storage, repositório privado se < 100 MB, disco pessoal)."
