#!/usr/bin/env python3
"""E6 — a API a partir de Python: lê dados mestre e cria um ORÇAMENTO EM RASCUNHO. Nunca confirma.

    python3 scripts/e6_orcamento.py --cliente C001 --artigo ART-001 --qtd 2 --pedido E6-C001-001
    python3 scripts/e6_orcamento.py --cliente C001 --artigo ART-001 --qtd 2 --pedido E6-C001-001 --criar

Sem --criar, mostra o que faria. Com --criar, cria o orçamento e deixa uma nota no histórico.

As três regras (são as do criar_encomenda do caso 21):
  1. só cria rascunhos — o botão «Confirmar» é de uma pessoa;
  2. verifica antes de criar (o cliente existe, o artigo existe, há stock) e, se não der, não cria e diz porquê;
  3. não duplica: a referência do pedido (--pedido) identifica-o, e a segunda execução não cria outro.

Ponto de partida comum da turma (SGE 2026-27, aula 11). Cada grupo troca o «cliente», o «artigo» e a verificação
pelos do seu caso (tutorial do grupo, linha E6).
"""
import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from agent.odoo_client import OdooClient  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cliente", required=True, help="referência do cliente (res.partner, campo ref)")
    ap.add_argument("--artigo", required=True, help="referência interna do artigo (product.product, default_code)")
    ap.add_argument("--qtd", type=float, default=1, help="quantidade (por omissão, 1)")
    ap.add_argument("--pedido", required=True, help="referência do pedido; identifica-o e impede duplicados")
    ap.add_argument("--criar", action="store_true", help="cria o orçamento em rascunho; sem isto, só mostra")
    args = ap.parse_args()

    odoo = OdooClient()

    # 1. Ler os dados mestre
    cliente = odoo.search_read("res.partner", [["ref", "=", args.cliente]], ["id", "name"], limit=1)
    if not cliente:
        print(f"Cliente {args.cliente} não existe (res.partner, campo ref). Nada foi criado.")
        sys.exit(2)
    cliente = cliente[0]
    artigo = odoo.search_read("product.product", [["default_code", "=", args.artigo]],
                              ["id", "name", "list_price", "is_storable", "qty_available"], limit=1)
    if not artigo:
        print(f"Artigo {args.artigo} não existe no catálogo (product.product, default_code). Nada foi criado.")
        sys.exit(2)
    artigo = artigo[0]
    print(f"Cliente: {cliente['name']} ({args.cliente})")
    print(f"Artigo:  {artigo['name']} — {artigo['list_price']:.2f} € s/ IVA — em stock: {artigo['qty_available']:.0f}")

    # 2. Verificar antes de criar (aqui, o stock; no vosso caso pode ser a capacidade, a agenda, os lugares)
    if artigo["is_storable"] and artigo["qty_available"] < args.qtd:
        print(f"Sem stock: pedido {args.qtd:g}, disponível {artigo['qty_available']:g}. Nada foi criado.")
        sys.exit(2)

    # 3. Não duplicar
    ja = odoo.search_read("sale.order", [["client_order_ref", "=", args.pedido]], ["name", "state"], limit=1)
    if ja:
        print(f"Já existe {ja[0]['name']} ({ja[0]['state']}) com a referência {args.pedido}. Nada foi criado.")
        return
    if not args.criar:
        print(f"Ensaio: criaria um orçamento em rascunho com a referência {args.pedido}. Use --criar.")
        return

    # 4. Criar — só o rascunho. Nunca action_confirm.
    so_id = odoo.create("sale.order", {
        "partner_id": cliente["id"],
        "client_order_ref": args.pedido,
        "order_line": [[0, 0, {"product_id": artigo["id"], "product_uom_qty": args.qtd}]],
    })
    so = odoo.read("sale.order", [so_id], ["name", "state", "amount_untaxed", "amount_total"])[0]
    # texto simples: no Odoo 20, uma nota em HTML enviada pela API aparece com as etiquetas à vista
    odoo.message_post("sale.order", so_id, "Criado por scripts/e6_orcamento.py (E6), em rascunho. A confirmação é de uma pessoa.")
    print(f"Criado:  {so['name']} — estado {so['state']} — {so['amount_untaxed']:.2f} € + IVA = {so['amount_total']:.2f} €")


if __name__ == "__main__":
    main()
