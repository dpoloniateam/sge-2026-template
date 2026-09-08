"""Regras de validação da aplicação externa.

Estão num ficheiro próprio de propósito: são regras de negócio do cliente, e é aqui que a equipa
acrescenta as suas. O que o formulário aceita e o que o contrato de integração declara (T12) têm de
dizer a mesma coisa — se divergirem, o erro só aparece do lado do Odoo, e tarde.
"""
import re

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
OBRIGATORIOS = ("nome", "email")


def validar(dados):
    """Devolve a lista de erros. Lista vazia significa que a submissão é aceitável."""
    erros = []
    for campo in OBRIGATORIOS:
        if not (dados.get(campo) or "").strip():
            erros.append(f"{campo}: é obrigatório")
    email = (dados.get("email") or "").strip()
    if email and not EMAIL.match(email):
        erros.append("email: formato inválido")
    telefone = re.sub(r"\D", "", dados.get("telefone") or "")
    if telefone and len(telefone) != 9:
        erros.append("telefone: são esperados 9 dígitos")
    return erros


def normalizar(dados):
    """Uniformiza o que entra, para a chave de identificação ser estável."""
    return {
        "nome": (dados.get("nome") or "").strip(),
        "empresa": (dados.get("empresa") or "").strip() or None,
        "email": (dados.get("email") or "").strip().lower(),
        "telefone": re.sub(r"\D", "", dados.get("telefone") or "") or None,
        "mensagem": (dados.get("mensagem") or "").strip() or None,
    }
