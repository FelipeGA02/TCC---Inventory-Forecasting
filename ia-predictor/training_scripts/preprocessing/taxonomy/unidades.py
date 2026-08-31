"""De/para `empresa` (entidade juridica no XLSX) -> `unidade` operacional.

`empresa` tem 3 valores nos dados reais, que sao entidades juridicas (LTDA) e NAO
necessariamente as 3 lojas fisicas do artigo (Nova Lima / Jardim Canada + Itabirito).

A CONFIRMAR com a entidade parceira (tasks.md T000d):
  - As 3 LTDAs correspondem 1:1 as 3 unidades operacionais?
  - Alguns nomes de vendedor trazem "(ITABIRITO)" / "(CANADA)"; se `empresa` nao separar
    as lojas, a unidade tera de vir de outro campo.
"""

# Mojibake ja observado em algumas exportacoes do sistema de origem (nao na rodada atual).
# Mantido por seguranca — normaliza antes do de/para.
NORMALIZE_EMPRESA = {
    "FLORICULTURA VERDE PERTO CANAD� LTDA": "FLORICULTURA VERDE PERTO CANADÁ LTDA",
}

UNIDADE_POR_EMPRESA = {
    "FLORICULTURA VERDE PERTO CANADÁ LTDA": "Jardim Canadá",
    "GARDEN CENTER VERDE PERTO LTDA":            "Garden Center",
    "VERDE PERTO JARDINAGEM LTDA":               "Itabirito",
}

UNIDADE_DEFAULT = "Desconhecida"


def map_unidade(empresa) -> str:
    """Retorna o rotulo de unidade para um valor de `empresa` (tolerante a None/vazio)."""
    if not empresa or not str(empresa).strip():
        return UNIDADE_DEFAULT
    e = str(empresa).strip()
    e = NORMALIZE_EMPRESA.get(e, e)
    return UNIDADE_POR_EMPRESA.get(e, UNIDADE_DEFAULT)
