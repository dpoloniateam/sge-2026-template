# T07 — Guião de testes de aceitação (UAT)

Testador: | Papel: | Data: | Ambiente (base edu / Community):

| N.º | Requisito | Passos (o que o testador faz) | Resultado esperado | Resultado obtido | Passou / Falhou / Não percebi | Observações |
|---|---|---|---|---|---|---|
| 1 | R01 | | | | | |

Regras: um caso por requisito «Must»; passos escritos para quem nunca viu o sistema; incluir 2 casos de erro (dados inválidos, utilizador sem permissão).
Incluir obrigatoriamente **dois casos de integração ponta a ponta**: (a) submeter o formulário na aplicação externa e confirmar o registo no CRM, incluindo a repetição da sincronização para provar que não duplica; (b) importar um ficheiro com linhas inválidas pelo canal `exchange/` e confirmar que as boas entram, as más vão para `errors/` e o relatório as identifica.
Falhas geram tarefas no repositório com prazo.
