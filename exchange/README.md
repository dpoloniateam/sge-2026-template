# `exchange/` — canal assíncrono

Troca de dados por ficheiro entre o sistema de gestão e sistemas externos. É a segunda via de
integração exigida em M3, e em vários casos é a via principal e não o plano B: quando o parceiro
manda um extracto por noite, ou quando o volume não justifica uma chamada por registo.

| Pasta | O que lá está |
|---|---|
| `in/` | ficheiros à espera de serem importados |
| `processed/` | ficheiros importados sem uma única rejeição |
| `errors/` | ficheiros com linhas rejeitadas, e o respectivo relatório `*-rejeitadas.json` |
| `out/` | ficheiros gerados pelo sistema de gestão para consumo externo |
| `exemplos/` | dois ficheiros de arranque: um limpo e um com erros propositados |

```bash
python scripts/import_leads.py exchange/exemplos/leads_limpo.csv
python scripts/import_leads.py exchange/exemplos/leads_sujo.csv    # veja o relatório em errors/
python scripts/import_leads.py                                     # trata tudo o que estiver em in/
python scripts/export_catalogo.py --formato json
```

O contrato dos ficheiros está em `schema/` e explica-se em `docs/contrato_de_integracao.md`. Se
mudarem o contrato depois de o outro lado o ter implementado, isso é um pedido de alteração (T06).

Os ficheiros de dados não vão para o repositório — só os exemplos. Dados sintéticos apenas.
