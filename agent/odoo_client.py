"""Cliente mínimo para a API externa do Odoo.

Transporte principal: JSON-2 (Odoo 19): POST {ODOO_URL}/json/2/<modelo>/<método> com
"Authorization: bearer <chave API>" e "X-Odoo-Database: <base>". Fallback: JSON-RPC (/jsonrpc,
object.execute_kw), que existe em todas as versões mas tem remoção agendada.

Configuração por variáveis de ambiente (ver .env.example): ODOO_URL, ODOO_DB, ODOO_API_KEY,
ODOO_USER (só JSON-RPC), ODOO_API = json2 | jsonrpc | auto.

Exemplo:
    from agent.odoo_client import OdooClient
    odoo = OdooClient()
    for p in odoo.search_read("res.partner", [["is_company", "=", True]], ["name", "email"], limit=5):
        print(p)
    lead_id = odoo.create("crm.lead", {"name": "Pedido de orçamento — Loja X", "contact_name": "Ana", "email_from": "ana@exemplo.pt"})
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()


class OdooError(RuntimeError):
    pass


class OdooClient:
    def __init__(self, url=None, db=None, api_key=None, user=None, transport=None, timeout=60):
        self.url = (url or os.environ["ODOO_URL"]).rstrip("/")
        self.db = db or os.environ.get("ODOO_DB")
        self.api_key = api_key or os.environ["ODOO_API_KEY"]
        self.user = user or os.environ.get("ODOO_USER", "admin")
        self.transport = (transport or os.environ.get("ODOO_API", "auto")).lower()
        self.timeout = timeout
        self._uid = None
        self.session = requests.Session()

    # ---------- JSON-2 (Odoo 19) ----------
    def _json2(self, model, method, payload):
        headers = {"Authorization": f"bearer {self.api_key}", "Content-Type": "application/json"}
        if self.db:
            headers["X-Odoo-Database"] = self.db
        r = self.session.post(f"{self.url}/json/2/{model}/{method}", headers=headers, json=payload, timeout=self.timeout)
        if r.status_code == 404:
            raise NotImplementedError("JSON-2 indisponível neste servidor")
        if r.status_code >= 400:
            raise OdooError(f"JSON-2 {model}.{method}: HTTP {r.status_code} — {r.text[:400]}")
        return r.json()

    # ---------- JSON-RPC (compatibilidade) ----------
    def _rpc(self, service, method, *args):
        payload = {"jsonrpc": "2.0", "method": "call", "id": 1,
                   "params": {"service": service, "method": method, "args": list(args)}}
        r = self.session.post(f"{self.url}/jsonrpc", json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            err = data["error"]
            raise OdooError(f"JSON-RPC {service}.{method}: {err.get('data', {}).get('message') or err.get('message')}")
        return data["result"]

    def _uid_(self):
        if self._uid is None:
            self._uid = self._rpc("common", "authenticate", self.db, self.user, self.api_key, {})
            if not self._uid:
                raise OdooError("Autenticação JSON-RPC falhou: verifique ODOO_DB, ODOO_USER e a chave API")
        return self._uid

    def _jsonrpc(self, model, method, ids=None, **kwargs):
        args = [ids] if ids is not None else []
        if method == "create":
            args.append(kwargs.pop("vals_list"))
        elif method == "write":
            args.append(kwargs.pop("vals"))
        return self._rpc("object", "execute_kw", self.db, self._uid_(), self.api_key, model, method, args, kwargs)

    # ---------- interface ----------
    def call(self, model, method, ids=None, **kwargs):
        """Chama um método do ORM. Para métodos sobre registos, passe ids=[...]."""
        if self.transport in ("json2", "auto"):
            payload = dict(kwargs)
            if ids is not None:
                payload["ids"] = ids
            try:
                result = self._json2(model, method, payload)
                self.transport = "json2"
                return result
            except NotImplementedError:
                if self.transport == "json2":
                    raise
                self.transport = "jsonrpc"
        return self._jsonrpc(model, method, ids=ids, **kwargs)

    def search_read(self, model, domain=None, fields=None, limit=80, order=None):
        kw = {"domain": domain or [], "fields": fields or [], "limit": limit}
        if order:
            kw["order"] = order
        return self.call(model, "search_read", **kw)

    def read(self, model, ids, fields=None):
        return self.call(model, "read", ids=ids, fields=fields or [])

    def create(self, model, vals):
        res = self.call(model, "create", vals_list=[vals])
        return res[0] if isinstance(res, list) else res

    def write(self, model, ids, vals):
        return self.call(model, "write", ids=ids, vals=vals)

    def unlink(self, model, ids):
        return self.call(model, "unlink", ids=ids)

    def message_post(self, model, res_id, body):
        """Publica uma nota no chatter de um registo (visível na interface do Odoo)."""
        return self.call(model, "message_post", ids=[res_id], body=body)

    def whoami(self):
        """Devolve o utilizador da chave API (teste de ligação)."""
        users = self.search_read("res.users", [["login", "=", self.user]], ["name", "login"], limit=1)
        return users[0] if users else {"login": self.user}
