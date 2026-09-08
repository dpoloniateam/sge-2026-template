# T12 — Contrato de integração e dicionário de dados

Preenchido na fase 3 e entregue com M3. É o documento que permite a outra equipa — ou a mesma daqui a seis meses —
ligar-se ao sistema sem ter de ler o código.

## 1. Sistemas em jogo

| Sistema | O que guarda | Tecnologia | Quem o administra |
|---|---|---|---|
| Aplicação externa (`frontend/`) | | base de dados própria | |
| Odoo (ERP e CRM) | | | |
| Parceiro / ficheiro (`exchange/`) | | CSV ou JSON | |

## 2. Sistema-mestre por entidade

Para cada entidade que existe em mais do que um sistema, um e só um é o mestre. É esta tabela que evita que dois
sistemas divirjam sem ninguém dar por isso.

| Entidade | Sistema-mestre | Quem mais a guarda | Como se resolve um conflito |
|---|---|---|---|
| | | | |

## 3. Via síncrona (HTTP + JSON)

| Campo | Valor |
|---|---|
| Sentido | (aplicação externa → Odoo / Odoo → aplicação externa) |
| Acontecimento que a dispara | |
| Endereço e método | |
| Autenticação | onde vive a chave (nunca no browser, nunca no repositório) |
| Chave de identificação | o campo que evita duplicados |
| Idempotência | o que acontece se a mesma submissão for enviada duas vezes |
| Erros | o que o chamador vê e o que fica registado |

## 4. Via assíncrona (ficheiro)

| Campo | Valor |
|---|---|
| Sentido e periodicidade | |
| Pasta e convenção de nomes | |
| Formato e codificação | CSV ou JSON; UTF-8 |
| Esquema | ficheiro em `schema/` |
| Validação | regras aplicadas antes de escrever no Odoo |
| Rejeições | onde vão, que relatório sai, quem o lê e em quanto tempo |
| Reprocessamento | como se repete um ficheiro corrigido sem duplicar |

## 5. Dicionário de dados

Um quadro por entidade trocada. Os nomes são os que atravessam a fronteira, não os internos de cada sistema.

| Campo | Tipo | Obrigatório | Domínio ou formato | Corresponde a (Odoo) | Corresponde a (externo) | Exemplo |
|---|---|---|---|---|---|---|
| | | | | | | |

## 6. Dados pessoais

Que campos do contrato seriam dados pessoais num sistema real, que base de licitude teriam e quanto tempo se
guardariam. No projecto todos os dados são sintéticos; esta secção declara o que mudaria se não fossem.

## 7. Versão do contrato

| Versão | Data | O que mudou | Quem aprovou |
|---|---|---|---|
| 1.0 | | primeira versão | |

Uma alteração ao contrato depois de ambos os lados o terem implementado passa por change request (T06).
