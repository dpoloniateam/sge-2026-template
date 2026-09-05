#!/usr/bin/env bash
# Cria a base de dados do Odoo com as apps do projecto. Uso: ./scripts/init_db.sh  (DB=nome DEMO=0 para base sem dados de demonstração)
set -euo pipefail
cd "$(dirname "$0")/.."
DB=${DB:-odoo}; DEMO=${DEMO:-1}
MODS="base,contacts,calendar,crm,sale_management,purchase,stock,account,website_sale,project,mass_mailing"
OPTS=""; [ "$DEMO" = "0" ] && OPTS="--without-demo"   # Odoo 18+: opção booleana; em Odoo 17 era --without-demo=all
docker compose up -d db
sleep 5
docker compose run --rm web odoo -d "$DB" -i "$MODS" $OPTS --stop-after-init
docker compose up -d
echo "Base '$DB' criada. Abra http://localhost:8069, entre com admin / admin e mude a senha."
