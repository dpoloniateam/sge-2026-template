"""Adaptadores de LLM com uma única interface (chat, ask, embed).

LLM_PROVIDER = azure | gemini | ollama | openai
  azure : AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_API_VERSION; LLM_MODEL = nome do deployment (gpt-5-nano)
  gemini: GEMINI_API_KEY (Google AI Studio, gratuito; só dados sintéticos); LLM_MODEL = gemini-3.6-flash (o 2.5 deixou de estar disponível para novas contas em 2026)
  ollama: OLLAMA_URL (http://localhost:11434/v1); LLM_MODEL = llama3.2 (modelo com suporte de ferramentas para o agente)
  openai: OPENAI_BASE_URL, OPENAI_API_KEY (qualquer endpoint compatível)
Os modelos de raciocínio da família gpt-5 não aceitam "temperature" nem "max_tokens"; usa-se "max_completion_tokens".
"""
import os
from dotenv import load_dotenv
from openai import OpenAI, AzureOpenAI

load_dotenv()

PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()
DEFAULTS = {
    "azure": ("gpt-5-nano", "text-embedding-3-small"),
    "gemini": ("gemini-3.6-flash", "gemini-embedding-001"),
    "ollama": ("llama3.2", "nomic-embed-text"),
    "openai": ("gpt-4o-mini", "text-embedding-3-small"),
}
SYSTEM = ("És um assistente de uma consultora júnior de sistemas de gestão empresarial. "
          "Responde em português europeu, de forma breve, concreta e verificável. "
          "Quando não tens dados suficientes, diz o que falta em vez de inventar.")


def model():
    return os.environ.get("LLM_MODEL") or DEFAULTS.get(PROVIDER, DEFAULTS["openai"])[0]


def embed_model():
    return os.environ.get("EMBED_MODEL") or DEFAULTS.get(PROVIDER, DEFAULTS["openai"])[1]


def client():
    if PROVIDER == "azure":
        return AzureOpenAI(api_key=os.environ["AZURE_OPENAI_KEY"], azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                           api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"))
    if PROVIDER == "gemini":
        return OpenAI(api_key=os.environ["GEMINI_API_KEY"], base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    if PROVIDER == "ollama":
        return OpenAI(api_key="ollama", base_url=os.environ.get("OLLAMA_URL", "http://localhost:11434/v1"))
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "none"), base_url=os.environ.get("OPENAI_BASE_URL") or None)


def reasoning_model(name=None):
    """gpt-5 e série o: os tokens de raciocínio contam para o limite de saída e não aceitam max_tokens."""
    return (name or model()).lower().startswith(("gpt-5", "o1", "o3", "o4"))


def chat(messages, tools=None, max_tokens=1200):
    kw = {"model": model(), "messages": messages}
    if tools:
        kw["tools"] = tools
    if reasoning_model():
        # folga para o raciocínio (senão a resposta vem vazia com finish_reason=length) e esforço baixo por defeito
        kw["max_completion_tokens"] = max_tokens * 4
        kw["reasoning_effort"] = os.environ.get("REASONING_EFFORT", "low")
    elif PROVIDER == "azure":
        kw["max_completion_tokens"] = max_tokens
    else:
        kw["max_tokens"] = max_tokens
    try:
        return client().chat.completions.create(**kw)
    except Exception as e:  # versões antigas da API Azure não conhecem reasoning_effort
        if "reasoning_effort" in kw and "reasoning_effort" in str(e):
            kw.pop("reasoning_effort")
            return client().chat.completions.create(**kw)
        raise


def ask(prompt, system=SYSTEM):
    r = chat([{"role": "system", "content": system}, {"role": "user", "content": prompt}])
    return (r.choices[0].message.content or "").strip()


def embed(texts):
    r = client().embeddings.create(model=embed_model(), input=texts)
    return [d.embedding for d in r.data]
