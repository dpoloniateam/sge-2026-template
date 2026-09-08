# `frontend/` — a aplicação externa

Uma aplicação web mínima com **base de dados própria**. É o outro sistema da integração de SGE.

Não é um formulário que escreve no Odoo. É um sistema separado, com o seu repositório de dados, que
grava os pedidos localmente e depois os sincroniza. É essa fronteira que faz aparecer as perguntas
que interessam nesta unidade curricular — quem é o sistema-mestre de cada entidade, o que acontece
quando a sincronização corre duas vezes, o que se faz com um duplicado, quem repara um erro — e
nenhuma delas existe se os dois lados forem a mesma base de dados.

Vem pronta a funcionar. **O trabalho da equipa é alterá-la**, não escrevê-la: acrescentar campos,
pôr regras de negócio do vosso cliente, tratar duplicados à vossa maneira e explicar o contrato.
O HTML não é avaliado.

## Correr

```bash
python frontend/app.py                 # http://localhost:8000
python frontend/sync.py --ensaio       # mostra o que iria para o Odoo, sem escrever
python frontend/sync.py                # cria os leads em falta
python frontend/sync.py                # correr outra vez NÃO deve criar nada: é a prova de idempotência
```

Sem dependências novas: `http.server` e `sqlite3` são da biblioteca-padrão. A base fica em
`frontend/submissoes.db` (fora do repositório) ou onde `FRONTEND_DB` apontar.

## Ficheiros

| Ficheiro | O que é |
|---|---|
| `index.html` | o formulário |
| `app.py` | servidor: recebe, valida, grava. Não fala com o Odoo |
| `db.py` | esquema e acesso a SQLite: `submissao` e `sincronizacao` |
| `validacao.py` | regras de negócio — é aqui que a equipa acrescenta as suas |
| `sync.py` | a integração síncrona: submissões locais → leads no CRM |

## O que se avalia em M3

- as duas vias a funcionar: esta e o canal por ficheiro em [`../exchange/`](../exchange/);
- **idempotência**: correr `sync.py` duas vezes não duplica nada;
- **deduplicação**: um email que já existe no CRM não gera um segundo lead;
- **rastreabilidade**: o id do Odoo fica gravado do lado da aplicação, e o chatter do lead diz de onde veio;
- o **contrato de dados** e a escolha do sistema-mestre escritos no template T12.

## Se quiserem ir mais longe

A base é SQLite porque não obriga a mais nenhum serviço. Trocar para MySQL ou PostgreSQL é mudar a
ligação em `db.py`. E uma equipa que já tenha uma aplicação web feita noutra unidade curricular pode
apontá-la a este mesmo contrato em vez de usar esta — é uma extensão legítima, não é exigida, e não
altera o que é avaliado.
