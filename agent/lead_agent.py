"""Agente de qualificação de leads: lê leads do Odoo, pede ao LLM uma avaliação e escreve no CRM.

  python -m agent.lead_agent --limit 5            # modo de ensaio: mostra o que faria, não escreve nada
  python -m agent.lead_agent --limit 5 --apply    # escreve prioridade e nota no chatter de cada lead

Como funciona: o LLM recebe uma ferramenta (qualify_lead) e, para cada lead, decide a prioridade (0 a 3),
a razão e o próximo passo. O programa executa as chamadas de ferramenta contra o Odoo (chamada de funções).
Regra da UC: rever sempre o resultado em modo de ensaio antes de aplicar; declarar o uso de IA no portefólio.
"""
import argparse
import json
from agent import llm
from agent.odoo_client import OdooClient

FIELDS = ["name", "partner_name", "contact_name", "email_from", "phone", "description",
          "expected_revenue", "priority", "stage_id", "source_id", "country_id", "create_date"]

TOOLS = [{
    "type": "function",
    "function": {
        "name": "qualify_lead",
        "description": "Regista a qualificação de um lead do CRM.",
        "parameters": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "integer"},
                "priority": {"type": "integer", "description": "0 = baixa, 1 = média, 2 = alta, 3 = muito alta"},
                "reason": {"type": "string", "description": "Uma frase com a razão, baseada nos dados do lead"},
                "next_step": {"type": "string", "description": "Acção concreta para o comercial (ex.: ligar em 24 h)"},
            },
            "required": ["lead_id", "priority", "reason", "next_step"],
        },
    },
}]

SYSTEM = ("És um analista comercial de uma PME. Qualificas leads do CRM Odoo com base nos dados fornecidos. "
          "Critérios: receita esperada, completude dos contactos, adequação ao negócio, urgência expressa na descrição. "
          "Para cada lead chama a ferramenta qualify_lead exactamente uma vez. Não inventes dados.")


def run(limit, apply):
    odoo = OdooClient()
    leads = odoo.search_read("crm.lead", [["priority", "=", "0"]], FIELDS, limit=limit, order="create_date desc")
    if not leads:
        print("Sem leads por qualificar (prioridade 0)."); return
    slim = [{k: (v[1] if isinstance(v, list) and len(v) == 2 else v) for k, v in l.items()} for l in leads]
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": "Qualifica estes leads:\n" + json.dumps(slim, ensure_ascii=False, default=str)}]
    resp = llm.chat(messages, tools=TOOLS)
    calls = resp.choices[0].message.tool_calls or []
    if not calls:
        print(f"O modelo não chamou a ferramenta (finish_reason={resp.choices[0].finish_reason}; se for 'length', aumente max_tokens). Resposta:",
              resp.choices[0].message.content); return
    for c in calls:
        a = json.loads(c.function.arguments)
        lead = next((l for l in leads if l["id"] == a["lead_id"]), None)
        name = lead["name"] if lead else "?"
        print(f"- lead {a['lead_id']} «{name}»: prioridade {a['priority']} — {a['reason']} → {a['next_step']}")
        if apply and lead:
            odoo.write("crm.lead", [a["lead_id"]], {"priority": str(max(0, min(3, int(a["priority"]))))})
            odoo.message_post("crm.lead", a["lead_id"],
                              f"<b>Qualificação por agente de IA ({llm.PROVIDER}/{llm.model()})</b><br/>"
                              f"Prioridade {a['priority']}. {a['reason']}<br/>Próximo passo: {a['next_step']}<br/>"
                              f"<i>Revisto por humano antes de aplicar.</i>")
    print("Aplicado no Odoo." if apply else "Modo de ensaio: nada foi escrito. Use --apply depois de rever.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    run(args.limit, args.apply)
