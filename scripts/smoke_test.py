#!/usr/bin/env python3
"""Teste de fumo de todo o ambiente da equipa: máquina, GitHub, Odoo (edu e Community), Azure e LLM.

Uso:
  python scripts/smoke_test.py                  # tudo o que estiver configurado
  python scripts/smoke_test.py --no-llm         # tudo menos o modelo de IA
  python scripts/smoke_test.py --so odoo,github # só algumas partes: maquina, github, odoo, azure, llm
  python scripts/smoke_test.py --debug          # mostra o erro completo

Cada linha sai com um de quatro estados:
  [OK]    funciona
  [ERRO]  não funciona e tem de ser resolvido (o script termina com código 1)
  [AVISO] funciona, mas há um risco ou uma regra da UC por cumprir
  [--]    não se aplica a esta equipa (por exemplo Azure numa equipa em Codespaces)

Lê o .env. Além das variáveis do .env.example, usa (todas opcionais):
  EQUIPA=eq01            por omissão, deduzida de ODOO_DB ou do nome do repositório
  AMBIENTE=azure         azure | codespaces | local; por omissão, deduzido
  ODOO_CE_URL, ODOO_CE_DB, ODOO_CE_USER, ODOO_CE_API_KEY, ODOO_CE_API
                         a instalação Community, quando o alvo do agente (ODOO_*) é a base edu
Nunca imprime chaves.
"""
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import traceback
from datetime import date

sys.path.insert(0, ".")
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

DOCENTE = "dpolonia@ua.pt"
PARTES = ["maquina", "github", "odoo", "azure", "llm"]
DEBUG = "--debug" in sys.argv
contagem = {"OK": 0, "ERRO": 0, "AVISO": 0, "--": 0}
folha = {}  # o que a equipa copia para a folha partilhada


def mostrar(estado, titulo, texto=""):
    contagem[estado] += 1
    print(f"[{estado}]".ljust(8) + f"{titulo}" + (f": {texto}" if texto != "" else ""))


def step(titulo, fn):
    """Corre fn(). Devolve o resultado; uma exceção é [ERRO]. fn pode devolver ("AVISO", texto) ou ("--", texto)."""
    try:
        out = fn()
        if isinstance(out, tuple) and len(out) == 2 and out[0] in ("AVISO", "--", "ERRO"):
            mostrar(out[0], titulo, out[1])
            return None
        mostrar("OK", titulo, out)
        return out
    except Exception as e:
        mostrar("ERRO", titulo, e)
        if DEBUG:
            traceback.print_exc()
        return None


def cabecalho(nome):
    print(f"\n== {nome} ".ljust(78, "="))


def correr(args, timeout=60, env=None):
    exe = shutil.which(args[0])
    if not exe:
        raise FileNotFoundError(f"«{args[0]}» não está instalado ou não está no PATH")
    r = subprocess.run([exe] + args[1:], capture_output=True, text=True, timeout=timeout,
                       env={**os.environ, **(env or {})}, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def partes_pedidas():
    if "--so" in sys.argv:
        i = sys.argv.index("--so")
        pedidas = [p.strip() for p in sys.argv[i + 1].split(",")] if i + 1 < len(sys.argv) else []
        desconhecidas = [p for p in pedidas if p not in PARTES]
        if desconhecidas:
            sys.exit(f"Partes desconhecidas: {desconhecidas}. Use: {', '.join(PARTES)}")
        return [p for p in PARTES if p in pedidas]
    return [p for p in PARTES if not (p == "llm" and "--no-llm" in sys.argv)]


# ---------------------------------------------------------------- máquina
def testar_maquina():
    cabecalho("Máquina e ferramentas")

    def python():
        v = sys.version_info
        if v < (3, 11):
            raise RuntimeError(f"Python {v.major}.{v.minor}; é preciso 3.11 ou mais recente")
        return f"Python {v.major}.{v.minor}.{v.micro} em {platform.system()}"
    step("Python", python)

    def pacotes():
        em_falta = []
        for mod in ("requests", "dotenv", "openai", "numpy"):
            try:
                __import__(mod)
            except ImportError:
                em_falta.append(mod)
        if em_falta:
            raise RuntimeError(f"faltam {em_falta}: ative o .venv e corra pip install -r requirements.txt")
        return "requests, python-dotenv, openai, numpy"
    step("Pacotes Python", pacotes)

    def ficheiro_env():
        if not os.path.exists(".env"):
            if os.path.exists(".env.txt"):
                raise RuntimeError("existe .env.txt em vez de .env: ren .env.txt .env")
            if os.environ.get("ODOO_URL"):
                return ("AVISO", "não há .env; as variáveis vêm do ambiente da sessão")
            raise RuntimeError("não há .env: copie .env.example para .env e preencha-o")
        return ".env encontrado"
    step("Ficheiro .env", ficheiro_env)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    step("Git", lambda: correr(["git", "--version"])[1])

    def docker():
        amb = ambiente()
        if not shutil.which("docker"):
            if amb == "local" and platform.system() == "Windows":
                return ("--", "sem Docker neste portátil; o Odoo Community corre na VM ou no Codespace")
            raise RuntimeError("Docker não instalado: é preciso para o Odoo Community")
        rc, out, err = correr(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=30)
        if rc != 0:
            raise RuntimeError(f"o Docker está instalado mas o serviço não responde ({err[:120]})")
        return f"Docker {out}"
    step("Docker", docker)

    def memoria():
        if not os.path.exists("/proc/meminfo"):
            return ("--", "só se mede em Linux (VM ou Codespace)")
        kb = int(re.search(r"MemTotal:\s+(\d+)", open("/proc/meminfo").read()).group(1))
        gb = kb / 1024 / 1024
        texto = f"{gb:.1f} GB de RAM, {os.cpu_count()} CPU"
        if gb < 3.5:
            return ("AVISO", texto + " — o Odoo com PostgreSQL precisa de 4 GB; evite a B1s")
        return texto
    step("Memória", memoria)

    folha["Ambiente"] = {"azure": "Azure VM", "codespaces": "Codespaces", "local": "local"}[ambiente()]
    step("Ambiente da equipa", lambda: folha["Ambiente"] + (" (de AMBIENTE no .env)" if os.environ.get("AMBIENTE") else " (deduzido)"))


_ambiente = None


def ambiente():
    global _ambiente
    if _ambiente is None:
        a = os.environ.get("AMBIENTE", "").lower()
        if a in ("azure", "codespaces", "local"):
            _ambiente = a
        elif os.environ.get("CODESPACES") == "true":
            _ambiente = "codespaces"
        elif _vm_azure():
            _ambiente = "azure"
        else:
            _ambiente = "local"
    return _ambiente


def _vm_azure():
    try:
        return "microsoft" in open("/sys/class/dmi/id/sys_vendor").read().lower() and os.path.exists("/var/lib/waagent")
    except OSError:
        return False


def equipa():
    if os.environ.get("EQUIPA"):
        return os.environ["EQUIPA"]
    for fonte in (os.environ.get("ODOO_DB", ""), os.environ.get("ODOO_URL", ""), repositorio()[1] or ""):
        m = re.search(r"eq\d\d", fonte)
        if m:
            return m.group(0)
    return None


# ---------------------------------------------------------------- GitHub
def repositorio():
    try:
        rc, url, _ = correr(["git", "remote", "get-url", "origin"], timeout=15)
    except Exception:
        return None, None
    m = re.search(r"github\.com[:/]([^/]+)/([^/\s]+?)(?:\.git)?$", url) if rc == 0 else None
    return (m.group(1), m.group(2)) if m else (None, None)


def testar_github():
    cabecalho("GitHub")
    rc, _, _ = correr(["git", "rev-parse", "--is-inside-work-tree"], timeout=15)
    if rc != 0:
        mostrar("ERRO", "Repositório", "esta pasta não é um repositório git: corra o teste dentro da pasta clonada")
        return
    dono, nome = repositorio()
    if not dono:
        mostrar("ERRO", "Remoto origin", "o origin não aponta para o github.com")
        return
    folha["Repositório GitHub"] = f"https://github.com/{dono}/{nome}"
    mostrar("OK", "Remoto origin", folha["Repositório GitHub"])

    def acesso():
        rc, out, err = correr(["git", "ls-remote", "origin", "HEAD"], timeout=60, env={"GIT_TERMINAL_PROMPT": "0"})
        if rc != 0:
            raise RuntimeError(f"sem acesso ao repositório ({err.splitlines()[-1] if err else rc}); "
                               "peçam ao dono que vos convide como colaboradores")
        return "leitura no GitHub com as vossas credenciais"
    acesso_ok = step("Acesso ao repositório", acesso)

    def visibilidade():
        import requests
        r = requests.get(f"https://api.github.com/repos/{dono}/{nome}", timeout=20)
        if r.status_code == 200 and not r.json().get("private"):
            raise RuntimeError("o repositório é PÚBLICO: Settings → General → Danger Zone → Change visibility → Private")
        if r.status_code == 404:
            return "privado" if acesso_ok else ("AVISO", "não se vê de fora e não houve acesso: privado ou inexistente")
        if r.status_code == 403:
            return ("AVISO", "limite de pedidos da API do GitHub; tente daqui a uma hora")
        return f"HTTP {r.status_code}"
    step("Visibilidade", visibilidade)

    def env_fora_do_git():
        if subprocess.run([shutil.which("git"), "ls-files", "--error-unmatch", ".env"], capture_output=True).returncode == 0:
            raise RuntimeError(".env está no git: git rm --cached .env, commit, e revoguem TODAS as chaves que lá estão")
        if subprocess.run([shutil.which("git"), "check-ignore", "-q", ".env"], capture_output=True).returncode != 0:
            return ("AVISO", ".env não está no .gitignore: acrescentem a linha .env")
        return ".env ignorado pelo git"
    step("Segredos: .env fora do git", env_fora_do_git)

    def chaves_no_repositorio():
        nomes = ["ODOO_API_KEY", "ODOO_CE_API_KEY", "AZURE_OPENAI_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"]
        valores = {n: os.environ.get(n, "") for n in nomes}
        valores = {n: v for n, v in valores.items() if len(v) >= 12 and "cole-aqui" not in v}
        if not valores:
            return ("--", "sem chaves no .env para procurar")
        expostas = []
        for n, v in valores.items():
            if subprocess.run([shutil.which("git"), "grep", "-q", "-F", v], capture_output=True).returncode == 0:
                expostas.append(f"{n} (ficheiros atuais)")
            elif correr(["git", "log", "--all", "-S", v, "--oneline"], timeout=120)[1]:
                expostas.append(f"{n} (histórico)")
        if expostas:
            raise RuntimeError(f"chave no repositório: {expostas}. Revoguem-na e criem outra; apagar o ficheiro não chega")
        return f"nenhuma das {len(valores)} chaves do .env aparece no repositório nem no histórico"
    step("Segredos: chaves no repositório", chaves_no_repositorio)

    def sincronizado():
        rc, out, _ = correr(["git", "status", "-sb"], timeout=30)
        linha = out.splitlines()[0] if out else ""
        if "ahead" in linha or "à frente" in linha:
            return ("AVISO", f"há commits por enviar: git push ({linha})")
        rc, quando, _ = correr(["git", "log", "-1", "--format=%cd", "--date=short"], timeout=15)
        return f"sem commits por enviar; último commit {quando}"
    step("Sincronização", sincronizado)

    def codespaces():
        if ambiente() != "codespaces":
            return ("--", "a equipa não trabalha em Codespaces")
        return f"Codespace {os.environ.get('CODESPACE_NAME', '?')}"
    step("Codespace", codespaces)


# ---------------------------------------------------------------- Odoo
def alvos_odoo():
    alvos = []
    if os.environ.get("ODOO_URL"):
        alvos.append(("ODOO", os.environ["ODOO_URL"], os.environ.get("ODOO_DB"), os.environ.get("ODOO_USER", "admin"),
                      os.environ.get("ODOO_API_KEY", ""), os.environ.get("ODOO_API")))
    ce = os.environ.get("ODOO_CE_URL")
    if ce and ce.rstrip("/") != os.environ.get("ODOO_URL", "").rstrip("/"):
        alvos.append(("ODOO_CE", ce, os.environ.get("ODOO_CE_DB", "odoo"), os.environ.get("ODOO_CE_USER", "admin"),
                      os.environ.get("ODOO_CE_API_KEY", ""), os.environ.get("ODOO_CE_API")))
    return alvos


def rpc_publico(url, rota, params=None, timeout=20):
    import requests
    r = requests.post(url.rstrip("/") + rota, json={"jsonrpc": "2.0", "method": "call", "params": params or {}}, timeout=timeout)
    r.raise_for_status()
    dados = r.json()
    if "error" in dados:
        raise RuntimeError(dados["error"].get("data", {}).get("message") or dados["error"].get("message"))
    return dados["result"]


def testar_odoo():
    alvos = alvos_odoo()
    if not alvos:
        cabecalho("Odoo")
        mostrar("ERRO", "Configuração", "ODOO_URL não está no .env")
        return
    tem_ce = any("odoo.com" not in a[1] for a in alvos)
    for prefixo, url, db, user, chave, transporte in alvos:
        edu = "odoo.com" in url
        cabecalho(f"Odoo {'edu (Odoo Online)' if edu else 'Community'} — {url}  [{prefixo}_*]")
        testar_um_odoo(url, db, user, chave, edu, prefixo, transporte)
    if not tem_ce:
        cabecalho("Odoo Community")
        mostrar("AVISO", "Instalação Community", "não configurada: ponham ODOO_CE_URL, ODOO_CE_DB e ODOO_CE_API_KEY no .env "
                "depois da aula 5, para o teste a incluir")


def testar_um_odoo(url, db, user, chave, edu, prefixo, transporte=None):
    from agent.odoo_client import OdooClient

    def versao():
        info = rpc_publico(url, "/web/webclient/version_info")
        serie, vi = info.get("server_serie"), info.get("server_version_info", [])
        edicao = "Enterprise" if (vi and vi[-1] == "e") else "Community"
        if not edu and edicao == "Enterprise":
            return ("AVISO", f"Odoo {serie} {edicao}: esperava-se Community")
        return f"Odoo {serie} {edicao}"
    step("Servidor responde", versao)

    odoo = OdooClient(url=url, db=db, api_key=chave, user=user, transport=transporte)
    quem = step("Chave API aceite (utilizador)", lambda: odoo.whoami())
    if quem is None:
        return
    step("Transporte usado", lambda: odoo.transport)
    step("Ler contactos", lambda: [p["name"] for p in odoo.search_read("res.partner", [], ["name"], limit=3)])

    def lead():
        lid = odoo.create("crm.lead", {"name": "SMOKE TEST — apagar", "contact_name": "Teste", "email_from": "teste@exemplo.pt"})
        odoo.unlink("crm.lead", [lid])
        return f"lead {lid} criado e apagado"
    escreveu = step("Criar e apagar um lead (app CRM instalada?)", lead)

    def apps():
        pedidas = ["crm", "contacts", "sale_management", "stock", "account"]
        inst = {m["name"] for m in odoo.search_read("ir.module.module", [["name", "in", pedidas], ["state", "=", "installed"]], ["name"], limit=20)}
        falta = [m for m in pedidas if m not in inst]
        return ("AVISO", f"instaladas {sorted(inst)}; por instalar {falta}") if falta else f"{', '.join(pedidas)}"
    step("Apps de gestão", apps)

    def idioma():
        ativos = [l["code"] for l in odoo.search_read("res.lang", [["active", "=", True]], ["code"], limit=20)]
        u = odoo.search_read("res.users", [["login", "=", user]], ["lang"], limit=1)
        lang = u[0].get("lang") if u else None
        if "pt_PT" not in ativos:
            return ("AVISO", f"português (Portugal) não está ativo (ativos: {ativos}): Definições → Idiomas")
        if lang and lang != "pt_PT":
            return ("AVISO", f"pt_PT ativo, mas o utilizador da chave está em {lang}: Minhas preferências → Idioma")
        return "pt_PT ativo e em uso"
    step("Idioma", idioma)

    if edu:
        def docente():
            u = odoo.search_read("res.users", [["login", "=", DOCENTE]], ["id", "name", "share"], limit=1)
            if not u:
                raise RuntimeError(f"{DOCENTE} não é utilizador da base: Definições → Utilizadores → Convidar")
            if u[0].get("share"):
                raise RuntimeError(f"{DOCENTE} é utilizador portal; tem de ser interno")
            try:
                admin = odoo.call("res.users", "has_group", ids=[u[0]["id"]], group_ext_id="base.group_system")
            except Exception:
                return ("AVISO", f"{DOCENTE} é interno; não foi possível confirmar Administração → Definições")
            if not admin:
                raise RuntimeError(f"{DOCENTE} é interno mas sem Administração → Definições")
            return f"{DOCENTE} interno, com Administração → Definições"
        step("Acesso do docente", docente)

        def registo_livre():
            try:
                v = odoo.search_read("ir.config_parameter", [["key", "=", "auth_signup.invitation_scope"]], ["value"], limit=1)
            except Exception:
                return ("--", "não foi possível ler o parâmetro")
            if v and v[0]["value"] == "b2c":
                return ("AVISO", "registo livre aberto: Definições → Website → Customer Account → On invitation")
            return "só por convite"
        step("Registo de clientes", registo_livre)
        folha["URL da base Odoo edu"] = url.rstrip("/")
        if escreveu:
            folha["Chave API Odoo criada?"] = "S"
    else:
        def admin_por_omissao():
            try:
                uid = rpc_publico(url, "/jsonrpc", {"service": "common", "method": "authenticate", "args": [db, "admin", "admin", {}]})
            except Exception:
                uid = False
            if uid:
                raise RuntimeError("o utilizador admin ainda tem a senha admin: mudem-na já (Minhas preferências → Segurança da conta)")
            return "admin sem a senha por omissão"
        step("Senha do admin", admin_por_omissao)

        def senha_mestre():
            if not os.path.exists("config/odoo.conf"):
                return ("--", "config/odoo.conf não está nesta pasta")
            conf = open("config/odoo.conf", encoding="utf-8").read()
            if "mude-esta-senha-mestre" in conf:
                local = re.search(r"//(localhost|127\.0\.0\.1)", url)
                msg = "senha mestre por omissão em config/odoo.conf (admin_passwd)"
                if local and ambiente() != "azure":
                    return ("AVISO", msg + ": mudem-na antes de expor o Odoo")
                raise RuntimeError(msg + ": com o Odoo exposto, qualquer pessoa pode apagar a base")
            return "senha mestre alterada"
        step("Senha mestre", senha_mestre)

        def contentores():
            if not shutil.which("docker") or not os.path.exists("docker-compose.yml"):
                return ("--", "sem Docker ou sem docker-compose.yml nesta máquina")
            rc, out, err = correr(["docker", "compose", "ps", "--format", "json"], timeout=30)
            if rc != 0:
                return ("--", "docker compose ps falhou nesta máquina")
            linhas = [json.loads(l) for l in out.splitlines() if l.strip().startswith("{")] or \
                     (json.loads(out) if out.strip().startswith("[") else [])
            estado = {c.get("Service"): c.get("State") for c in linhas}
            if estado.get("web") != "running" or estado.get("db") != "running":
                return ("AVISO", f"contentores: {estado or 'nenhum'}; docker compose up -d")
            return "web e db a correr"
        step("Contentores Docker", contentores)

        def copias():
            dumps = sorted(glob.glob("backups/*.dump"), key=os.path.getmtime)
            if not dumps:
                return ("AVISO", "nenhuma cópia em backups/: ./scripts/backup.sh (obrigatório todas as semanas)")
            dias = (time.time() - os.path.getmtime(dumps[-1])) / 86400
            if dias > 7:
                return ("AVISO", f"a última cópia tem {dias:.0f} dias: ./scripts/backup.sh")
            return f"{os.path.basename(dumps[-1])} ({dias:.1f} dias)"
        step("Cópia de segurança", copias)
        folha["URL do Odoo Community"] = url.rstrip("/")
    if prefixo == "ODOO":
        folha["Alvo do agente"] = "edu" if edu else "community"


# ---------------------------------------------------------------- Azure
def testar_azure():
    cabecalho("Azure")
    usa_vm = ambiente() == "azure"
    usa_openai = os.environ.get("LLM_PROVIDER", "").lower() == "azure"
    if not usa_vm and not usa_openai:
        mostrar("--", "Azure", f"a equipa trabalha em {ambiente()} e o LLM não é Azure OpenAI")
        return
    if not shutil.which("az"):
        estado = "ERRO" if usa_vm else "--"
        dica = "winget install -e --id Microsoft.AzureCLI" if platform.system() == "Windows" else \
               "curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
        mostrar(estado, "Azure CLI", f"não instalado: {dica}")
        return

    conta = {}

    def sessao():
        rc, out, err = correr(["az", "account", "show", "-o", "json"], timeout=60)
        if rc != 0:
            raise RuntimeError("sem sessão: corra az login (numa VM ou Codespace: az login --use-device-code)")
        conta.update(json.loads(out))
        if conta.get("state") != "Enabled":
            raise RuntimeError(f"subscrição {conta.get('name')} em estado {conta.get('state')}: o crédito pode ter acabado")
        return f"{conta.get('user', {}).get('name')} em «{conta.get('name')}»"
    if step("Sessão e subscrição", sessao) is None:
        return
    eq = equipa()
    if usa_vm:
        if not eq:
            mostrar("ERRO", "Equipa", "não consegui deduzir a equipa: ponha EQUIPA=eqNN no .env")
            return
        rg, vm = f"rg-sge-{eq}", f"vm-sge-{eq}"

        def grupo():
            rc, out, err = correr(["az", "group", "show", "-n", rg, "--query", "location", "-o", "tsv"], timeout=60)
            if rc != 0:
                raise RuntimeError(f"o grupo {rg} não existe nesta subscrição (ou não têm acesso Contributor)")
            return f"{rg} em {out}"
        if step("Grupo de recursos", grupo) is None:
            return

        ip = {}

        def maquina():
            rc, out, err = correr(["az", "vm", "show", "-d", "-g", rg, "-n", vm, "--query",
                                   "{estado:powerState,ip:publicIps,tamanho:hardwareProfile.vmSize}", "-o", "json"], timeout=90)
            if rc != 0:
                raise RuntimeError(f"a VM {vm} não existe ({err[:120]})")
            d = json.loads(out)
            ip["ip"] = d.get("ip")
            if d.get("estado") != "VM running":
                return ("AVISO", f"{vm} {d.get('tamanho')}: {d.get('estado')}; ligue-a com az vm start -g {rg} -n {vm}")
            return f"{vm} {d.get('tamanho')}, a correr, IP {d.get('ip')}"
        step("Máquina virtual", maquina)

        def desligar():
            sub = conta["id"]
            rc, out, err = correr(["az", "resource", "show", "--ids",
                                   f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.DevTestLab/schedules/shutdown-computevm-{vm}",
                                   "--query", "{estado:properties.status,hora:properties.dailyRecurrence.time}", "-o", "json"], timeout=60)
            if rc != 0:
                return ("AVISO", "sem auto-desligar: az vm auto-shutdown (ver scripts/azure_vm.sh); sem ele o crédito acaba")
            d = json.loads(out)
            if d.get("estado") != "Enabled":
                return ("AVISO", f"auto-desligar {d.get('estado')}")
            return f"auto-desligar às {d.get('hora')} UTC"
        step("Auto-desligar", desligar)

        def orcamento():
            rc, out, err = correr(["az", "consumption", "budget", "list", "--resource-group", rg, "-o", "json"], timeout=60)
            if rc != 0:
                return ("AVISO", "não foi possível ler os budgets; confirmem no portal: Cost Management → Budgets")
            b = json.loads(out or "[]")
            if not b:
                return ("AVISO", f"sem budget no grupo {rg}: Cost Management → Budgets, 30 USD, alertas a 50 % e 80 %")
            return ", ".join(f"{x['name']} {x['amount']} {x.get('timeGrain', '')}" for x in b)
        step("Budget", orcamento)

        def odoo_na_vm():
            if not ip.get("ip"):
                return ("--", "VM sem IP público ou desligada")
            import requests
            r = requests.get(f"http://{ip['ip']}:8069/web/login", timeout=15)
            return f"http://{ip['ip']}:8069 responde (HTTP {r.status_code})"
        step("Odoo na VM, de fora", odoo_na_vm)
    else:
        mostrar("--", "Máquina virtual", f"a equipa trabalha em {ambiente()}")

    mostrar("AVISO", "Crédito restante", "o CLI não o mostra: leiam-no em https://www.microsoftazuresponsorships.com/Balance "
            "e registem-no na folha com a data")


# ---------------------------------------------------------------- LLM
def testar_llm():
    from agent import llm
    cabecalho(f"Modelo de IA — {llm.PROVIDER}")
    folha["Fornecedor de LLM"] = llm.PROVIDER
    step(f"Chat ({llm.model()})", lambda: llm.ask("Numa frase: o que é um ERP?")[:120])
    step(f"Embeddings ({llm.embed_model()})", lambda: f"{len(llm.embed(['ERP', 'CRM'])[0])} dimensões")

    def ferramentas():
        tool = {"type": "function", "function": {"name": "qualify_lead", "description": "Classifica um lead",
                "parameters": {"type": "object", "properties": {"prioridade": {"type": "string", "enum": ["alta", "media", "baixa"]}},
                               "required": ["prioridade"]}}}
        r = llm.chat([{"role": "user", "content": "Classifica: cliente pede orçamento para 40 equipamentos esta semana. Usa a ferramenta."}],
                     tools=[tool])
        chamadas = r.choices[0].message.tool_calls or []
        if not chamadas:
            raise RuntimeError("o modelo respondeu sem chamar a ferramenta: o agente não vai funcionar com este modelo")
        return f"{chamadas[0].function.name}({chamadas[0].function.arguments})"
    step("Chamada de ferramentas (o agente precisa)", ferramentas)


# ---------------------------------------------------------------- resumo
def main():
    pedidas = partes_pedidas()
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    print(f"Teste de fumo SGE 2026-27 — {date.today():%d/%m/%Y} — equipa {equipa() or '?'} — partes: {', '.join(pedidas)}")
    for p in pedidas:
        try:
            {"maquina": testar_maquina, "github": testar_github, "odoo": testar_odoo, "azure": testar_azure, "llm": testar_llm}[p]()
        except Exception as e:
            mostrar("ERRO", p, e)
            if DEBUG:
                traceback.print_exc()

    print("\n" + "=" * 78)
    print(f"OK {contagem['OK']} · ERRO {contagem['ERRO']} · AVISO {contagem['AVISO']} · não se aplica {contagem['--']}")
    if "URL da base Odoo edu" in folha:
        folha["Smoke test OK?"] = date.today().strftime("%d/%m/%Y") if contagem["ERRO"] == 0 else "ainda não: há erros"
    if folha:
        print("\nPara a folha partilhada (na linha de quem correu o teste):")
        for k, v in folha.items():
            print(f"  {k}: {v}")
    print("\nRESULTADO:", "tudo OK" if contagem["ERRO"] == 0 else
          "há erros — veja as dicas no README (secção Problemas frequentes) ou no guia do teste de fumo")
    sys.exit(0 if contagem["ERRO"] == 0 else 1)


if __name__ == "__main__":
    main()
