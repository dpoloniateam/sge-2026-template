# SGE 2026-27 — repositório da equipa (Odoo + agente de IA)

Repositório template da UC Sistemas de Gestão Empresarial (CTeSP ICO, ISCA-UA). Cada equipa cria o seu a partir deste modelo («Use this template») e trabalha aqui durante o semestre: código do agente, cópias de segurança da base Odoo Community, documentos do cliente para o assistente RAG e registos de trabalho. Nunca guarde aqui segredos (chaves) nem dados pessoais reais.

## 1. Contas (semana de 14 Set)

| Conta | Onde | Para quê | Prazo |
|---|---|---|---|
| GitHub Student Developer Pack | education.github.com/pack (com o email @ua.pt) | GitHub Pro, Copilot Student, Codespaces (180 core-horas/mês), Azure for Students | pedir a 14 Set; aprovação em 2-3 dias, por vezes semanas |
| Azure for Students | azure.microsoft.com/free/students | 100 USD/ano, sem cartão; VM e Azure OpenAI (opção a) | 14 Set; se falhar até 25 Set, a equipa usa a opção b |
| Base Odoo Online educativa | odoo.com/trial?edu — nome da base a começar por `edu-` (ex.: `edu-sge26-eq01`) | Odoo Enterprise gratuito durante 24 meses; é a base «de produção» do cliente | criar na 1.ª aula; abrir pelo menos uma vez cada 3 meses |
| Google AI Studio | aistudio.google.com | chave gratuita para o Gemini (opção b do agente); só dados sintéticos | 18 Set |
| O'Reilly Learning | learning.oreilly.com (entrar com o email @ua.pt) | bibliografia da UC | 18 Set |

## 2. Escolher o ambiente (até 25 Set)

- **a) Azure (recomendado se a activação correr bem)**: um elemento «anfitrião» cria a VM com `scripts/azure_vm.sh`; os outros dois recebem acesso *Contributor* ao grupo de recursos (Access control (IAM)). A VM desliga-se sozinha às 20:00; ligue-a no portal ou com `az vm start` antes das aulas. Crie um *budget* de 30 USD com alertas a 50 % e 80 % e registe o saldo todas as semanas. No Azure OpenAI (Foundry) crie duas implementações: `gpt-5-nano` para chat e `text-embedding-3-small` para o RAG; os nomes vão para `LLM_MODEL` e `EMBED_MODEL`.
- **b) GitHub Codespaces**: abra o repositório em «Code → Codespaces → Create codespace». O `.devcontainer` instala o Docker e arranca o Odoo. Limite: 90 h/mês numa máquina de 2 cores; o codespace pára ao fim de 30 min sem uso e é apagado após 30 dias parado — faça `./scripts/backup.sh` e guarde o `.dump` no repositório (se tiver menos de 100 MB) todas as semanas.
- **c) Local (último recurso)**: Docker Desktop no portátil (8 GB de RAM) e os mesmos comandos.

Em qualquer caso, a base **edu** (Odoo Online) é a que o cliente vê; a instalação Community serve para aprender self-hosting, cópias de segurança e API, e é o alvo do agente se a API da base edu não responder.

## 3. Arrancar o Odoo Community

```bash
docker compose up -d          # arranca Odoo e PostgreSQL
./scripts/init_db.sh          # cria a base "odoo" com CRM, Vendas, Compras, Inventário, Facturação, eCommerce, Projecto, Email Marketing (com dados de demonstração; DEMO=0 para base limpa)
```
Abra http://localhost:8069 (na VM: http://IP:8069), entre com `admin` / `admin` e mude a senha. Mude também a senha mestre em `config/odoo.conf` antes de expor a VM à Internet.

## 4. Chave API e ficheiro .env

No Odoo: avatar → Preferências → Segurança da conta → Nova chave API (dê-lhe um nome e uma data de expiração). Copie `.env.example` para `.env` e preencha `ODOO_URL`, `ODOO_DB` e `ODOO_API_KEY`. Para a base edu: `ODOO_URL=https://edu-sge26-eq01.odoo.com` e `ODOO_DB=edu-sge26-eq01`. Escolha o fornecedor de IA (`LLM_PROVIDER=azure` ou `gemini`) e a chave respectiva.

## 5. Teste ponta a ponta

```bash
pip install -r requirements.txt
python scripts/smoke_test.py            # Odoo: ler, criar e apagar um lead; LLM: pergunta e embeddings
```
Todas as linhas devem dizer `[OK]`. Se a base edu responder com erro 403/404 na API, aponte o `.env` para a instalação Community (a API JSON-2 está garantida aí).

## 6. Cópias de segurança e restauro (obrigatório semanalmente)

```bash
./scripts/backup.sh                                   # gera backups/odoo_<data>.dump e backups/odoo_<data>_filestore.tgz
./scripts/restore.sh backups/odoo_<data>.dump backups/odoo_<data>_filestore.tgz   # noutro ambiente (VM ↔ Codespaces ↔ local)
```
Na sessão de 30 Out cada equipa demonstra um restauro completo noutra conta.

## 7. Agente de qualificação de leads

```bash
python -m agent.lead_agent --limit 5           # ensaio: mostra prioridade, razão e próximo passo por lead; não escreve
python -m agent.lead_agent --limit 5 --apply   # escreve a prioridade e uma nota no chatter de cada lead
```
O agente usa chamada de funções (`qualify_lead`) e o cliente `agent/odoo_client.py`. Adapte os critérios no `SYSTEM` de `agent/lead_agent.py` ao negócio do cliente; no hackathon de 9 Nov acrescente uma segunda ferramenta (por exemplo, criar uma actividade ou redigir um email de seguimento).

## 8. Assistente RAG sobre os documentos do cliente

```bash
python -m agent.rag build docs/                # indexa os .md/.txt em docs/ (SOP, brief, regras) em rag_index.json
python -m agent.rag ask "Como se regista uma devolução?"
```

## 9. Regras da UC

1. Só dados sintéticos: nenhum nome, email ou telefone de pessoas reais, nem no Odoo nem nos prompts (Referencial IA da UA, 3.5).
2. Segredos só no `.env`; se uma chave for exposta, revogue-a no mesmo dia.
3. Custos: VM desligada fora das aulas; budget com alertas; modelos pequenos (gpt-5-nano, gemini flash).
4. Uso de IA declarado em M1, M3 e no portefólio: ferramenta, tarefas, o que foi aceite ou rejeitado e como foi verificado.
5. Cópia de segurança semanal guardada fora da VM.

## 10. Problemas frequentes

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `HTTP 404` no smoke test com a base edu | API JSON-2 não disponível no plano da base | `ODOO_API=jsonrpc` no `.env`; se também falhar, aponte para a instalação Community |
| `Autenticação JSON-RPC falhou` | `ODOO_DB` errado ou chave expirada | confirme o nome da base (subdomínio) e crie nova chave |
| `crm.lead` não existe | app CRM não instalada | instale a app CRM na base ou corra `./scripts/init_db.sh` |
| Odoo lento ou a reiniciar | RAM insuficiente (< 4 GB) | Codespace de 2 cores/8 GB ou VM B2als_v2; evite a B1s |
| `az vm create` recusa a região ou o tamanho | política da subscrição de estudante | veja Policy → Assignments; tente `LOC=westeurope` ou `SIZE=Standard_B2ts_v2` |
| Azure OpenAI recusa criar o recurso | limitação em subscrições de estudante | peça ao docente acesso ao recurso partilhado ou use `LLM_PROVIDER=gemini` |
| `DeploymentNotFound` ao criar embeddings | o recurso Azure OpenAI só tem a implementação do modelo de chat | crie a implementação `text-embedding-3-small` (Foundry → Deployments; em várias regiões só existe com SKU GlobalStandard) ou ponha em `EMBED_MODEL` o nome de uma implementação de embeddings existente |
| «O modelo não chamou a ferramenta (finish_reason=length)» | modelos de raciocínio (gpt-5-nano, gpt-5-mini) gastam o limite de saída a pensar | o adaptador já multiplica o limite por 4 e usa `REASONING_EFFORT=low`; para lotes grandes reduza `--limit` ou aumente `max_tokens` em `agent/llm.py` |
| Codespace apagado | 30 dias sem uso | restaure a última cópia com `./scripts/restore.sh` |
