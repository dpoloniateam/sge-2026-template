#!/usr/bin/env python3
"""Aplicação externa de demonstração: formulário → base de dados própria.

Serve o formulário, valida, grava em SQLite. NÃO fala com o Odoo — quem o faz é `sync.py`.
Usa `http.server` da biblioteca-padrão: nenhuma dependência nova, corre em qualquer máquina.

    python frontend/app.py            # http://localhost:8000
    python frontend/app.py --porta 9000

O que se espera que a equipa altere: os campos do formulário e do esquema (`db.py`), as regras de
negócio (`validacao.py`) e a página. O que se avalia é a integração e o contrato de dados, não o HTML.
"""
import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from frontend import db, validacao  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))


def pagina(ficheiro, aviso=""):
    with open(os.path.join(BASE, ficheiro), encoding="utf-8") as f:
        return f.read().replace("{{aviso}}", aviso)


class Handler(BaseHTTPRequestHandler):
    def _responder(self, corpo, codigo=200, tipo="text/html; charset=utf-8"):
        dados = corpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._responder(pagina("index.html"))
        if self.path == "/submissoes":
            return self._responder(json.dumps(db.listar(), ensure_ascii=False, indent=2),
                                   tipo="application/json; charset=utf-8")
        self._responder("<h1>404</h1>", 404)

    def do_POST(self):
        if self.path != "/submeter":
            return self._responder("<h1>404</h1>", 404)
        tamanho = int(self.headers.get("Content-Length") or 0)
        campos = parse_qs(self.rfile.read(tamanho).decode("utf-8"))
        dados = validacao.normalizar({k: v[0] for k, v in campos.items()})
        erros = validacao.validar(dados)
        if erros:
            aviso = "<div class='erro'><strong>Não foi possível registar:</strong><ul>" + \
                    "".join(f"<li>{e}</li>" for e in erros) + "</ul></div>"
            return self._responder(pagina("index.html", aviso), 400)
        sid = db.inserir_submissao(dados)
        aviso = (f"<div class='ok'>Pedido registado com o número <strong>{sid}</strong>. "
                 "Está guardado nesta aplicação e ainda não chegou ao sistema de gestão — "
                 "vai na próxima sincronização.</div>")
        self._responder(pagina("index.html", aviso))

    def log_message(self, formato, *args):
        sys.stderr.write("%s — %s\n" % (self.address_string(), formato % args))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--porta", type=int, default=int(os.environ.get("FRONTEND_PORT", 8000)))
    args = p.parse_args()
    db.conectar().close()
    print(f"Aplicação externa em http://localhost:{args.porta}  (base: {db.CAMINHO})")
    print("Depois de submeter, corra:  python frontend/sync.py")
    ThreadingHTTPServer(("0.0.0.0", args.porta), Handler).serve_forever()


if __name__ == "__main__":
    main()
