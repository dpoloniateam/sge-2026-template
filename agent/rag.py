"""Assistente de consulta por RAG (retrieval-augmented generation) sobre os documentos do cliente.

  python -m agent.rag build docs/            # indexa .md e .txt (SOP, brief, procedimentos) em rag_index.json
  python -m agent.rag ask "Como se cria uma factura de fornecedor?"
Funciona com qualquer fornecedor de agent/llm.py. Os embeddings ficam num JSON local (sem base de dados).
"""
import json
import sys
from pathlib import Path
import numpy as np
from agent import llm

INDEX = Path("rag_index.json")


def chunk(text, size=800, overlap=150):
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + size])
        i += size - overlap
    return [c.strip() for c in out if c.strip()]


def build(folder):
    docs = []
    for p in sorted(Path(folder).rglob("*")):
        if p.suffix.lower() in (".md", ".txt"):
            for j, c in enumerate(chunk(p.read_text(encoding="utf-8", errors="ignore"))):
                docs.append({"source": str(p), "chunk": j, "text": c})
    if not docs:
        sys.exit(f"Sem ficheiros .md/.txt em {folder}")
    vectors = []
    for i in range(0, len(docs), 32):                     # lotes de 32 para respeitar limites da API
        vectors += llm.embed([d["text"] for d in docs[i:i + 32]])
    for d, v in zip(docs, vectors):
        d["vector"] = v
    INDEX.write_text(json.dumps(docs, ensure_ascii=False))
    print(f"{len(docs)} excertos de {len({d['source'] for d in docs})} ficheiros indexados em {INDEX}")


def retrieve(question, k=4):
    docs = json.loads(INDEX.read_text())
    m = np.array([d["vector"] for d in docs], dtype=float)
    q = np.array(llm.embed([question])[0], dtype=float)
    sims = m @ q / (np.linalg.norm(m, axis=1) * np.linalg.norm(q) + 1e-9)
    top = np.argsort(-sims)[:k]
    return [(docs[i], float(sims[i])) for i in top]


def ask(question, k=4):
    hits = retrieve(question, k)
    context = "\n\n".join(f"[{h['source']} #{h['chunk']}]\n{h['text']}" for h, _ in hits)
    prompt = (f"Responde à pergunta usando apenas os excertos. Cita a fonte entre parênteses rectos. "
              f"Se os excertos não chegarem, diz que não há informação.\n\nExcertos:\n{context}\n\nPergunta: {question}")
    answer = llm.ask(prompt)
    print(answer)
    print("\nFontes:", ", ".join(f"{h['source']}#{h['chunk']} ({s:.2f})" for h, s in hits))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "build":
        build(sys.argv[2])
    elif len(sys.argv) >= 3 and sys.argv[1] == "ask":
        ask(" ".join(sys.argv[2:]))
    else:
        print(__doc__)
