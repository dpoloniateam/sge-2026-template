#!/usr/bin/env python3
"""Canal assíncrono, entrada: ficheiro CSV ou JSON → leads no CRM.

    python scripts/import_leads.py exchange/exemplos/leads_limpo.csv
    python scripts/import_leads.py exchange/in/            # trata tudo o que lá estiver
    python scripts/import_leads.py exchange/in/x.csv --ensaio

O que faz, por ficheiro: valida cada linha contra `schema/lead.json`, deduplica pela chave
`referencia_externa` e pelo email, cria o que falta, escreve um relatório em `exchange/errors/` com
as linhas rejeitadas e move o ficheiro para `exchange/processed/` ou `exchange/errors/`.

Um ficheiro só é dado por processado quando a decisão sobre TODAS as linhas está tomada. Reimportar
um ficheiro corrigido é seguro: as linhas já criadas são reconhecidas pela referência externa.
"""
import argparse
import csv
import json
import os
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.esquema import validar  # noqa: E402
from agent.odoo_client import OdooClient  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TROCA = os.path.join(RAIZ, "exchange")
ESQUEMA = json.load(open(os.path.join(RAIZ, "schema", "lead.json"), encoding="utf-8"))
MARCA = "ref-externa:"


def ler(caminho):
    """Lê CSV ou JSON e devolve uma lista de registos. Vazios passam a None, para o esquema os ver."""
    if caminho.lower().endswith(".json"):
        with open(caminho, encoding="utf-8-sig") as f:
            dados = json.load(f)
        return dados if isinstance(dados, list) else [dados]
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        return [{k: (v.strip() or None) if isinstance(v, str) else v for k, v in linha.items()}
                for linha in csv.DictReader(f)]


def ja_importada(odoo, registo):
    """Já existe no CRM? Primeiro pela referência externa (a chave do contrato), depois pelo email."""
    marca = MARCA + registo["referencia_externa"]
    achados = odoo.search_read("crm.lead", [["description", "ilike", marca]], ["id"], limit=1)
    if achados:
        return achados[0]["id"], "referência externa"
    achados = odoo.search_read("crm.lead", [["email_from", "=ilike", registo["email"]]], ["id"], limit=1)
    return (achados[0]["id"], "email") if achados else (None, None)


def para_lead(r):
    descricao = (r.get("mensagem") or "").strip()
    descricao = f"{descricao}\n\n{MARCA}{r['referencia_externa']}".strip()
    vals = {"name": f"Pedido — {r.get('empresa') or r['nome']}", "contact_name": r["nome"],
            "email_from": r["email"], "description": descricao}
    if r.get("empresa"):
        vals["partner_name"] = r["empresa"]
    if r.get("telefone"):
        vals["phone"] = r["telefone"]
    return vals


def processar(caminho, odoo, ensaio=False):
    nome = os.path.basename(caminho)
    registos = ler(caminho)
    criados, duplicados, rejeitados = [], [], []
    for i, r in enumerate(registos, start=2 if caminho.lower().endswith(".csv") else 1):
        erros = validar(r, ESQUEMA)
        if erros:
            rejeitados.append({"linha": i, "erros": erros, "registo": r})
            continue
        if ensaio:
            criados.append({"linha": i, "lead": None})
            continue
        try:
            existente, porque = ja_importada(odoo, r)
            if existente:
                duplicados.append({"linha": i, "lead": existente, "porque": porque})
                continue
            criados.append({"linha": i, "lead": odoo.create("crm.lead", para_lead(r))})
        except Exception as e:  # noqa: BLE001
            rejeitados.append({"linha": i, "erros": [f"escrita no Odoo: {e}"], "registo": r})

    print(f"\n{nome}: {len(registos)} linhas — {len(criados)} criadas, "
          f"{len(duplicados)} duplicadas, {len(rejeitados)} rejeitadas")
    for d in duplicados:
        print(f"  [DUPLICADA] linha {d['linha']} → lead {d['lead']} (por {d['porque']})")
    for r in rejeitados:
        print(f"  [REJEITADA] linha {r['linha']}: {'; '.join(r['erros'])}")

    if ensaio:
        return len(rejeitados)

    if rejeitados:
        relatorio = os.path.join(TROCA, "errors", f"{os.path.splitext(nome)[0]}-rejeitadas.json")
        os.makedirs(os.path.dirname(relatorio), exist_ok=True)
        with open(relatorio, "w", encoding="utf-8") as f:
            json.dump({"ficheiro": nome,
                       "processado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "criadas": len(criados), "duplicadas": len(duplicados),
                       "rejeitadas": rejeitados}, f, ensure_ascii=False, indent=2)
        print(f"  relatório: {os.path.relpath(relatorio, RAIZ)}")

    destino = "errors" if rejeitados else "processed"
    if os.path.dirname(os.path.abspath(caminho)) == os.path.join(TROCA, "in"):
        os.makedirs(os.path.join(TROCA, destino), exist_ok=True)
        shutil.move(caminho, os.path.join(TROCA, destino, nome))
        print(f"  ficheiro movido para exchange/{destino}/")
    return len(rejeitados)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("caminho", nargs="?", default=os.path.join(TROCA, "in"),
                   help="ficheiro CSV/JSON ou pasta (por omissão, exchange/in/)")
    p.add_argument("--ensaio", action="store_true", help="valida e mostra, sem escrever no Odoo")
    args = p.parse_args()

    alvos = ([os.path.join(args.caminho, f) for f in sorted(os.listdir(args.caminho))
              if f.lower().endswith((".csv", ".json"))] if os.path.isdir(args.caminho)
             else [args.caminho])
    if not alvos:
        print("Nada a importar.")
        return 0
    odoo = None if args.ensaio else OdooClient()
    return 1 if sum(processar(a, odoo, args.ensaio) for a in alvos) else 0


if __name__ == "__main__":
    sys.exit(main())
