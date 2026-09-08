"""Base de dados da aplicação externa. SQLite, da biblioteca-padrão: nenhuma dependência nova.

A aplicação externa tem a SUA base de dados. Não escreve directamente no Odoo — grava localmente e
só depois `sync.py` leva os registos para o CRM. É essa fronteira que torna a integração real: há
dois sistemas, dois repositórios de dados, e alguém tem de decidir qual é o mestre de cada entidade.

Se a equipa quiser aproximar-se de outro stack (MySQL, PostgreSQL), muda-se aqui a ligação; o resto
do código não sabe qual é a base.
"""
import os
import sqlite3
from datetime import datetime, timezone

CAMINHO = os.environ.get("FRONTEND_DB", os.path.join(os.path.dirname(__file__), "submissoes.db"))

ESQUEMA = """
CREATE TABLE IF NOT EXISTS submissao (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT NOT NULL,
    empresa    TEXT,
    email      TEXT NOT NULL,
    telefone   TEXT,
    mensagem   TEXT,
    criado_em  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sincronizacao (
    submissao_id INTEGER PRIMARY KEY REFERENCES submissao(id),
    odoo_id      INTEGER,
    estado       TEXT NOT NULL,          -- sincronizada | duplicada | erro
    tentado_em   TEXT NOT NULL,
    erro         TEXT
);
"""


def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def conectar():
    ligacao = sqlite3.connect(CAMINHO)
    ligacao.row_factory = sqlite3.Row
    ligacao.executescript(ESQUEMA)
    return ligacao


def inserir_submissao(dados):
    """Grava uma submissão e devolve o id local."""
    with conectar() as l:
        cur = l.execute(
            "INSERT INTO submissao (nome, empresa, email, telefone, mensagem, criado_em)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (dados["nome"], dados.get("empresa"), dados["email"],
             dados.get("telefone"), dados.get("mensagem"), agora()))
        return cur.lastrowid


def por_sincronizar():
    """Submissões que ainda não foram levadas ao Odoo com sucesso.

    É esta consulta que dá a idempotência: uma submissão com estado 'sincronizada' nunca mais é
    enviada, mesmo que o sync corra dez vezes.
    """
    with conectar() as l:
        return [dict(r) for r in l.execute(
            "SELECT s.* FROM submissao s"
            " LEFT JOIN sincronizacao x ON x.submissao_id = s.id"
            " WHERE x.submissao_id IS NULL OR x.estado = 'erro'"
            " ORDER BY s.id")]


def registar_sincronizacao(submissao_id, estado, odoo_id=None, erro=None):
    with conectar() as l:
        l.execute(
            "INSERT INTO sincronizacao (submissao_id, odoo_id, estado, tentado_em, erro)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(submissao_id) DO UPDATE SET"
            "   odoo_id = excluded.odoo_id, estado = excluded.estado,"
            "   tentado_em = excluded.tentado_em, erro = excluded.erro",
            (submissao_id, odoo_id, estado, agora(), erro))


def listar(limite=50):
    with conectar() as l:
        return [dict(r) for r in l.execute(
            "SELECT s.*, x.estado, x.odoo_id FROM submissao s"
            " LEFT JOIN sincronizacao x ON x.submissao_id = s.id"
            " ORDER BY s.id DESC LIMIT ?", (limite,))]
