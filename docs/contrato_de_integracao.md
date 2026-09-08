# Contrato de integração — o que atravessa a fronteira

Documento de referência do repositório template. O contrato **da vossa equipa** escreve-se no
template T12 (`docs/templates/`); este explica o que já vem feito e porquê.

## Os três sistemas

| Sistema | Guarda | Tecnologia |
|---|---|---|
| Aplicação externa (`frontend/`) | pedidos de contacto submetidos no formulário | SQLite |
| Odoo (ERP e CRM) | clientes, leads, artigos, encomendas, facturas | PostgreSQL, acedido por API |
| Parceiro (`exchange/`) | extractos e listas trocados por ficheiro | CSV ou JSON |

## Sistema-mestre por entidade

Regra: cada entidade tem **um** mestre. Sem esta decisão, dois sistemas divergem e ninguém dá por
isso até alguém reparar que os números não batem certo.

| Entidade | Mestre | Quem mais a guarda | Porquê |
|---|---|---|---|
| Pedido de contacto | aplicação externa | — | nasce lá e não é alterado no Odoo |
| Lead | Odoo | a aplicação guarda só o `odoo_id` | o ciclo comercial corre no CRM |
| Artigo e preço | Odoo | cópia exportada em `exchange/out/` | o preçário é do ERP; o exterior consome-o |

## Via síncrona — `frontend/sync.py`

| | |
|---|---|
| Sentido | aplicação externa → Odoo |
| Dispara | manualmente, ou por agendamento |
| Endereço | `POST {ODOO_URL}/json/2/crm.lead/create`, via `agent/odoo_client.py` |
| Autenticação | chave API no `.env`, do lado do servidor. **Nunca no browser** |
| Chave de identificação | email |
| Idempotência | a tabela `sincronizacao` marca o que já foi; um registo `sincronizada` nunca é reenviado |
| Duplicados | se já existir lead com o mesmo email, liga-se ao existente e marca-se `duplicada` |
| Erros | ficam em `sincronizacao.erro`; a submissão volta à fila na execução seguinte |

## Via assíncrona — `scripts/import_leads.py` e `scripts/export_catalogo.py`

| | |
|---|---|
| Entrada | ficheiros em `exchange/in/`, CSV ou JSON, UTF-8 |
| Esquema | `schema/lead.json`, validado por `scripts/esquema.py` antes de qualquer escrita |
| Chave de identificação | `referencia_externa`, gravada no lead e procurada antes de criar |
| Rejeições | relatório `exchange/errors/<ficheiro>-rejeitadas.json`, com linha e razão |
| Ficheiro tratado | vai para `processed/` se não houve rejeições, para `errors/` se houve |
| Reprocessamento | um ficheiro corrigido pode ser reimportado: o que já entrou é reconhecido pela referência |
| Saída | `exchange/out/catalogo-AAAAMMDD-HHMM.csv|json`, conforme `schema/artigo.json` |

## Porque existem as duas vias

A síncrona dá resposta imediata e é a certa quando alguém está à espera do outro lado do ecrã. A
assíncrona não precisa de os dois sistemas estarem de pé ao mesmo tempo, aguenta volume e deixa
rasto em ficheiro — e é a que se usa quando o parceiro manda um extracto por noite. Saber escolher,
e saber dizer porquê, é parte do que se avalia.

## Alterar o contrato

Depois de os dois lados o terem implementado, mudar um campo é um **pedido de alteração** (T06):
análise de impacto, decisão registada, e nova versão na tabela do T12. Um contrato que muda sem
aviso é a forma mais comum de partir uma integração que estava a funcionar.
