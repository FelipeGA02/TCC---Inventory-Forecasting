"""De/para `produto` -> `categoria`, e `shelf_life_dias` por categoria.

A amostra dos produtos de maior volume mostra que a Verde Perto opera como
GARDEN CENTER / JARDINAGEM, nao como floricultura de flor de corte: o carro-chefe e
GRAMA plantada (esmeralda, sao carlos, amendoim), seguida de mudas em saquinho (SAQ),
plantas em vaso (PT NN), terra/adubo (BIOPLANT, TERRA VEGETAL) e insumos de jardim
(manta bidim, separador de grama). Flor de corte (ROSA EM CABO, ALSTROEMERIA) e fatia
pequena. As categorias e regras abaixo refletem isso.

Aplicacao em CASCATA (primeira que casar vence):
  1. CATEGORIA_POR_SKU  — de/para explicito (Top-N + curadoria manual, alta confianca)
  2. CATEGORIA_REGRAS   — regex sobre produto_nome (ordem importa)
  3. CATEGORIA_DEFAULT  — "Outros"

Valores de TRABALHO — validar com a parceira (tasks.md T000d) o mapa produto->categoria
(ao menos do Top-N) e o `shelf_life_dias` real. Ver ADR-009 secao 8.
"""
import re

# 1. De/para explicito. Preencher na curadoria do Top-N (produto_cod -> categoria).
CATEGORIA_POR_SKU: dict[str, str] = {
    # "147": "Grama",                # GRAMA AMENDOIM UNID. BDJA
    # "3":   "Grama",                # GRAMA ESMERALDA
    # "00200512": "Insumo e acessorio",  # produto_nome literalmente "INSUMO"
}

# 2. Regras por palavra-chave sobre produto_nome. ORDEM IMPORTA (primeira que casar vence).
CATEGORIA_REGRAS: list[tuple[re.Pattern, str]] = [
    # Flor de corte e arranjos montados — fatia pequena, mas a mais pericivel.
    (re.compile(r"\b(FLOR\s+DE\s+CORTE|ROSA\s+EM\s+CABO|ALSTROEMERIA|ASTROMELIA|"
                r"BUQU[EÊ]|ARRANJO|COROA|GERBERA|CRISANTEMO|TANGO|LIRIO\s+CORTE)\b", re.I),
     "Flor de corte e arranjo"),

    # Hortalicas e ervas.
    (re.compile(r"\b(ERVAS?\s+AROMATICAS|TEMPEROS?|HORTALIC[AÇ]AS?|HORTALI[ÇC]A|HORTA)\b", re.I),
     "Hortalica e erva"),

    # Substrato, terra, adubo, condicionador de solo.
    (re.compile(r"\b(TERRA|ADUBO|SUBSTRATO|COMPOSTO\s+ORGANICO|HUMUS|BIOPLANT|"
                r"CASCA\s+DE\s+PINUS|FERTILIZANTE|CALCARIO|VERMICULITA|TURFA|PERLITA|"
                r"CONDICIONADOR)\b", re.I),
     "Substrato e adubo"),

    # Insumos e acessorios de jardinagem (nao vivos).
    (re.compile(r"\b(MANTA|BIDIM|SEPARADOR\s+DE\s+GRAMA|TUTOR|REGADOR|FERRAMENTA|"
                r"VASO\s+PL[AÁ]STICO|VASO\s+PL\b|CACHEPOT|CACHEP[OÔ]|PEDRA|SEIXO|"
                r"PASTILHA|TELA|GRAMPO|ESTACA|MANGUEIRA|PULVERIZADOR|LUVA|SACO\s+PARA)\b", re.I),
     "Insumo e acessorio"),

    # "Grama preta" / "pelo de urso" e forracao (Ophiopogon) — vendida como muda, NAO e
    # grama de plantio. Checar ANTES da regra de GRAMA.
    (re.compile(r"\b(GRAMA\s+PRETA|PELO\s+D[EO]?\s*URSO)\b", re.I),
     "Muda e forracao"),

    # Grama de plantio (esmeralda, sao carlos, amendoim, batatais, coreana...).
    (re.compile(r"\bGRAMA\b", re.I),
     "Grama"),

    # Arbusto / planta ja formada — nome traz medida de altura (ex.: "0,20 A 0,30CM",
    # "50 A 60 CM", "0,40 A 0,60 CM").
    (re.compile(r"\d+[.,]?\d*\s*(A|À)\s*\d+[.,]?\d*\s*(CM|M)\b", re.I),
     "Arbusto e planta formada"),

    # Planta em vaso — codigo de vaso "PT 11", "PT13", "PT 14".
    (re.compile(r"\bPT\s?\d{1,2}\b", re.I),
     "Planta em vaso"),

    # Muda / forracao em saquinho, bandeja ou touceira.
    (re.compile(r"\b(SAQ|SQ|MUDA|BANDEJA|BDJA|BDJ|TOUCEIRA|SUNPATIENS|BEIJO)\b", re.I),
     "Muda e forracao"),

    # Produto cujo nome e literalmente "INSUMO".
    (re.compile(r"^\s*INSUMO\s*$", re.I),
     "Insumo e acessorio"),
]

CATEGORIA_DEFAULT = "Outros"

# `shelf_life_dias` por categoria — dias que o produto aguenta na loja antes de perder
# valor de venda. Valores de TRABALHO (ADR-009 secao 8), a confirmar com a parceira.
SHELF_LIFE_DIAS: dict[str, int] = {
    "Grama":                     3,    # grama plantada resseca em poucos dias
    "Flor de corte e arranjo":   4,
    "Hortalica e erva":          7,
    "Muda e forracao":          20,
    "Planta em vaso":           30,
    "Arbusto e planta formada": 45,
    "Substrato e adubo":       180,
    "Insumo e acessorio":      365,
    "Outros":                    7,
}


def map_categoria(produto_cod, produto_nome) -> str:
    """Categoria de um produto pela cascata SKU -> regras -> default."""
    cod = "" if produto_cod is None else str(produto_cod).strip()
    if cod in CATEGORIA_POR_SKU:
        return CATEGORIA_POR_SKU[cod]
    nome = "" if produto_nome is None else str(produto_nome).strip()
    for rx, cat in CATEGORIA_REGRAS:
        if rx.search(nome):
            return cat
    return CATEGORIA_DEFAULT


def shelf_life(categoria: str) -> int:
    """`shelf_life_dias` da categoria (cai no default se a categoria for desconhecida)."""
    return SHELF_LIFE_DIAS.get(categoria, SHELF_LIFE_DIAS[CATEGORIA_DEFAULT])
