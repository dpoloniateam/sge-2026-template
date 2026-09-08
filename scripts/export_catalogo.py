#!/usr/bin/env python3
"""Canal assíncrono, saída: Odoo → ficheiro CSV ou JSON em exchange/out/.

    python scripts/export_catalogo.py                       # CSV do catálogo activo
    python scripts/export_catalogo.py --formato json
    python scripts/export_catalogo.py --modelo res.partner --campos name,email --ficheiro clientes

Serve o padrão «exportação nocturna»: quem consome o catálogo lê um ficheiro, não bate no ERP a cada
visita. O sistema-mestre do artigo continua a ser o ERP — o ficheiro é uma cópia com data.
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.odoo_client import OdooClient  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "exchange", "out")

# Tradução dos campos do Odoo para os nomes do contrato (schema/artigo.json).
CATALOGO = {"default_code": "referencia", "name": "designacao", "list_price": "preco", "active": "activo"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modelo", default="product.template")
    p.add_argument("--campos", default=",".join(CATALOGO))
    p.add_argument("--formato", choices=["csv", "json"], default="csv")
    p.add_argument("--ficheiro", default="catalogo")
    p.add_argument("--limite", type=int, default=1000)
    args = p.parse_args()

    campos = [c.strip() for c in args.campos.split(",") if c.strip()]
    linhas = OdooClient().search_read(args.modelo, [], campos, limit=args.limite)
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    registos = [{CATALOGO.get(k, k): v for k, v in linha.items() if k != "id"} for linha in linhas]
    for r in registos:
        if "preco" in r:
            r["moeda"] = "EUR"
        r["actualizado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    os.makedirs(SAIDA, exist_ok=True)
    destino = os.path.join(SAIDA, f"{args.ficheiro}-{carimbo}.{args.formato}")
    if args.formato == "json":
        with open(destino, "w", encoding="utf-8") as f:
            json.dump(registos, f, ensure_ascii=False, indent=2)
    else:
        cabecalho = sorted({k for r in registos for k in r})
        with open(destino, "w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=cabecalho)
            escritor.writeheader()
            escritor.writerows(registos)
    print(f"{len(registos)} registos → {os.path.relpath(destino, RAIZ)}")


if __name__ == "__main__":
    main()
