"""De/para `empresa` (entidade juridica no XLSX) -> `unidade` operacional.

`empresa` tem 3 valores nos dados reais, um por CNPJ, mas a rede tem 2 unidades
operacionais (Jardim Canada e Itabirito). CONFIRMADO com o cliente: as vendas do
Garden Center pertencem a unidade Jardim Canada. O de/para abaixo e definitivo.
"""

# Mojibake ja observado em algumas exportacoes do sistema de origem (nao na rodada atual).
# Mantido por seguranca — normaliza antes do de/para.
NORMALIZE_EMPRESA = {
    "FLORICULTURA VERDE PERTO CANAD� LTDA": "FLORICULTURA VERDE PERTO CANADÁ LTDA",
}

UNIDADE_POR_EMPRESA = {
    "FLORICULTURA VERDE PERTO CANADÁ LTDA": "Jardim Canadá",
    "GARDEN CENTER VERDE PERTO LTDA":            "Jardim Canadá",
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
