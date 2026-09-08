"""Validador mínimo de JSON Schema — o subconjunto que os contratos deste repositório usam.

Escrito à mão de propósito, por duas razões: não acrescenta dependências, e obriga a olhar para o
que um contrato de dados realmente garante. Suporta: type (incluindo listas de tipos), required,
additionalProperties, enum, pattern, minLength, maxLength, minimum.

Para um sistema real usar-se-ia a biblioteca `jsonschema`. O que não muda é a ideia: o contrato é um
ficheiro, versionado, e a validação corre antes de qualquer escrita no sistema de gestão.
"""
import re

TIPOS = {"string": str, "number": (int, float), "integer": int, "boolean": bool,
         "object": dict, "array": list, "null": type(None)}


def _tipo_ok(valor, esperado):
    nomes = esperado if isinstance(esperado, list) else [esperado]
    if isinstance(valor, bool) and "boolean" not in nomes:
        return False
    return any(isinstance(valor, TIPOS[n]) for n in nomes if n in TIPOS)


def validar(registo, esquema):
    """Devolve a lista de erros do registo face ao esquema. Lista vazia = válido."""
    erros = []
    if not isinstance(registo, dict):
        return ["o registo não é um objecto"]
    props = esquema.get("properties", {})
    for campo in esquema.get("required", []):
        if registo.get(campo) in (None, ""):
            erros.append(f"{campo}: em falta")
    if esquema.get("additionalProperties") is False:
        for campo in registo:
            if campo not in props:
                erros.append(f"{campo}: campo desconhecido")
    for campo, regra in props.items():
        if campo not in registo:
            continue
        valor = registo[campo]
        if valor is None:
            # Ausente é ausente: se era obrigatório já foi assinalado acima; se não era, nada a validar.
            continue
        if "type" in regra and not _tipo_ok(valor, regra["type"]):
            erros.append(f"{campo}: tipo inválido (esperado {regra['type']})")
            continue
        if "enum" in regra and valor not in regra["enum"]:
            erros.append(f"{campo}: valor fora do domínio {regra['enum']}")
        if isinstance(valor, str):
            if "pattern" in regra and not re.match(regra["pattern"], valor):
                erros.append(f"{campo}: não corresponde ao formato exigido")
            if "minLength" in regra and len(valor) < regra["minLength"]:
                erros.append(f"{campo}: demasiado curto")
            if "maxLength" in regra and len(valor) > regra["maxLength"]:
                erros.append(f"{campo}: demasiado longo")
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            if "minimum" in regra and valor < regra["minimum"]:
                erros.append(f"{campo}: abaixo do mínimo {regra['minimum']}")
    return erros
