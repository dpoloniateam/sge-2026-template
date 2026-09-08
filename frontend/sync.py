#!/usr/bin/env python3
"""Sincronização da aplicação externa para o Odoo: submissões locais → leads no CRM.

É aqui que vive a integração síncrona. Três propriedades que se exigem em M3 e que se demonstram
correndo o script duas vezes seguidas:

  · idempotência — uma submissão já sincronizada não gera um segundo lead;
  · deduplicação — se já existe no CRM um lead com o mesmo email, não se cria outro; regista-se a
    ligação ao existente e marca-se 'duplicada';
  · rastreabilidade — o id do Odoo fica gravado do lado da aplicação externa, e o chatter do lead
    diz de onde veio.

    python frontend/sync.py             # sincroniza o que falta
    python frontend/sync.py --ensaio    # mostra o que faria, sem escrever no Odoo

O sistema-mestre do pedido é a aplicação externa; o do lead é o Odoo. Está declarado no T12.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from frontend import db  # noqa: E402
from agent.odoo_client import OdooClient  # noqa: E402


def lead_existente(odoo, email):
    achados = odoo.search_read("crm.lead", [["email_from", "=ilike", email]], ["id", "name"], limit=1)
    return achados[0]["id"] if achados else None


def para_lead(s):
    """Tradução dos campos da aplicação externa para os do CRM. É o contrato de dados (T12)."""
    descricao = s.get("mensagem") or ""
    vals = {
        "name": f"Pedido de contacto — {s.get('empresa') or s['nome']}",
        "contact_name": s["nome"],
        "email_from": s["email"],
        "description": descricao,
    }
    if s.get("empresa"):
        vals["partner_name"] = s["empresa"]
    if s.get("telefone"):
        vals["phone"] = s["telefone"]
    return vals


def sincronizar(ensaio=False):
    pendentes = db.por_sincronizar()
    if not pendentes:
        print("Nada por sincronizar.")
        return 0
    odoo = None if ensaio else OdooClient()
    criados = duplicados = falhados = 0
    for s in pendentes:
        rotulo = f"#{s['id']} {s['nome']} <{s['email']}>"
        if ensaio:
            print(f"[ENSAIO] criaria lead: {para_lead(s)}")
            continue
        try:
            existente = lead_existente(odoo, s["email"])
            if existente:
                db.registar_sincronizacao(s["id"], "duplicada", odoo_id=existente)
                print(f"[DUPLICADA] {rotulo} — já existe o lead {existente}")
                duplicados += 1
                continue
            lead_id = odoo.create("crm.lead", para_lead(s))
            odoo.message_post("crm.lead", lead_id,
                              f"Origem: aplicação externa, submissão #{s['id']} de {s['criado_em']}.")
            db.registar_sincronizacao(s["id"], "sincronizada", odoo_id=lead_id)
            print(f"[OK] {rotulo} → lead {lead_id}")
            criados += 1
        except Exception as e:  # noqa: BLE001 — queremos continuar com as restantes
            db.registar_sincronizacao(s["id"], "erro", erro=str(e)[:500])
            print(f"[ERRO] {rotulo}: {e}")
            falhados += 1
    print(f"\nCriados {criados}, duplicados {duplicados}, falhados {falhados}.")
    return 1 if falhados else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ensaio", action="store_true", help="não escreve no Odoo")
    sys.exit(sincronizar(ensaio=p.parse_args().ensaio))
