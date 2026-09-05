#!/usr/bin/env python3
"""Teste ponta a ponta do ambiente: Odoo (leitura e escrita), LLM (chat) e embeddings.
Uso: python scripts/smoke_test.py [--no-llm]
"""
import sys, traceback
sys.path.insert(0, ".")
from agent.odoo_client import OdooClient

ok = True


def step(title, fn):
    global ok
    try:
        out = fn(); print(f"[OK]  {title}: {out}")
    except Exception as e:
        ok = False; print(f"[ERRO] {title}: {e}")
        if "--debug" in sys.argv: traceback.print_exc()


odoo = OdooClient()
step("Odoo: utilizador da chave API", lambda: odoo.whoami())
step("Odoo: transporte usado", lambda: odoo.transport)
step("Odoo: ler parceiros", lambda: [p["name"] for p in odoo.search_read("res.partner", [], ["name"], limit=3)])


def create_and_delete():
    lid = odoo.create("crm.lead", {"name": "SMOKE TEST — apagar", "contact_name": "Teste", "email_from": "teste@exemplo.pt"})
    odoo.unlink("crm.lead", [lid]); return f"lead {lid} criado e apagado"


step("Odoo: criar e apagar um lead (app CRM instalada?)", create_and_delete)

if "--no-llm" not in sys.argv:
    from agent import llm
    step(f"LLM ({llm.PROVIDER}/{llm.model()}): pergunta", lambda: llm.ask("Numa frase: o que é um ERP?")[:120])
    step(f"Embeddings ({llm.embed_model()})", lambda: f"{len(llm.embed(['ERP', 'CRM'])[0])} dimensões")

print("\nRESULTADO:", "tudo OK" if ok else "há erros — veja as dicas no README (secção Problemas frequentes)")
sys.exit(0 if ok else 1)
