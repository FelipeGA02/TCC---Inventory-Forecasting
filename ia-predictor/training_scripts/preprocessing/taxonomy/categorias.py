"""De/para `produto` -> `categoria`.

Tres niveis:

  * `categoria_fina` (~10 rotulos) — classificacao detalhada por regras, util para EDA e
    para a desagregacao L2. Produzida por `map_categoria()`.
  * `categoria` (nivel L1 do modelo) — 3 categorias de demanda + 1 rotulo de nao-produto
    (ver docs/prediction/01-pre_processing.md §5 e ADR-011). Produzida por
    `map_categoria_l1()` colapsando a fina via `CATEGORIA_L1`.
  * `grupo` de produto — vocabulario do cliente (Grama, Flores de corte, Plantas diversas,
    Insumos e acessorios) para apresentar a previsao. Produzido por `map_grupo()`
    colapsando a fina via `GRUPO_PRODUTO`. NAO e unidade de modelagem: os numeros de um
    grupo vem da desagregacao L2 (a EDA de granularidade, `eda/eda_grupos.py`, mostra que
    modelar cada grupo direto nao erra menos do que repartir a previsao do L1).

O negocio se organiza em Grama, Flores de corte (as que compoem arranjos e buques) e
Plantas diversas (todas as plantas, exceto flores de corte e arvores). Plantas e insumos
formam o L1 "Produtos de jardim". `shelf_life_dias` foi REMOVIDO: a recomendacao de
reposicao (camada L3) saiu de escopo — o entregavel e a previsao de demanda diaria, a loja
decide a compra (ADR-011).

Cascata da `categoria_fina` (primeira que casar vence):
  1. CATEGORIA_POR_SKU  — de/para explicito por produto_cod (curadoria, alta confianca)
  2. CATEGORIA_REGRAS   — regex sobre produto_nome (ordem importa)
  3. CATEGORIA_DEFAULT  — "Outros"
"""
import re

# 1. De/para explicito por produto_cod. Vence sempre — use para SKUs de alto volume que
# as regras nao classificam bem (nome so com a especie, sem formato/tamanho) ou que elas
# classificariam errado. Curadoria da cauda de "Outros" (2026-08-30); PROVISORIO ate a
# validacao com a parceira (tasks.md T000d).
CATEGORIA_POR_SKU: dict[str, str] = {
    # Frutiferas envasadas (citricas e afins) — arvore jovem formada, vendida em vaso/bag.
    "369": "Arbusto e planta formada",       # LARANJA BAHIA
    "860": "Arbusto e planta formada",       # LARANJA PERA RIO
    "1054": "Arbusto e planta formada",      # LARANJA (CITRICAS) DIVERSAS MAIOR
    "00040370": "Arbusto e planta formada",  # LARANJA (CITRICAS) DIVERSAS MENOR
    "00040220": "Arbusto e planta formada",  # LARANJA SERRA D'AGUA MENOR
    "800": "Arbusto e planta formada",       # LIMAO CAPETA / CRAVO / ROSA PEQ
    "405": "Arbusto e planta formada",       # LIMAO THAITI
    "2057": "Arbusto e planta formada",      # LIMAO TAHITI (TAITI) GDE
    "854": "Arbusto e planta formada",       # LIMAO SICILIANO PEQ
    "6": "Arbusto e planta formada",         # ACEROLA
    "1047": "Arbusto e planta formada",      # PITANGA PEQUENA
    "364": "Arbusto e planta formada",       # MARACUJA AZEDO (altura sem unidade CM/M)
    # Arbustos / plantas formadas de folhagem ou floracao.
    "209": "Arbusto e planta formada",       # JASMIM REX 60 CM
    "16": "Arbusto e planta formada",        # OITI MEDIO
    "00020807": "Arbusto e planta formada",  # ACALIFA
    "2836": "Arbusto e planta formada",      # CAMARAO AMARELO (Pachystachys)
    "00021065": "Arbusto e planta formada",  # FORMIO VERDE (Phormium)
    # Folhagens / palmeiras envasadas.
    "2822": "Planta em vaso",                # TUMBERGIA TREPADEIRA AZUL
    "224": "Planta em vaso",                 # RAPHIS (RAFIS) HASTE
    "00020248": "Planta em vaso",            # CURCULIGO
    "00020321": "Planta em vaso",            # FILODENDRO ONDULATO 50 CM
    "00020014": "Planta em vaso",            # FILODENDRO ONDULATO 30CM
    "1394": "Planta em vaso",                # ALPINEA ZERUMBET VARIEGATA
    "1393": "Planta em vaso",                # ALPINEA ZERUMBET 40CM
    "1319": "Planta em vaso",                # DRACENA TRICOLOR
    "136NL": "Planta em vaso",               # CLIVIA POTE
    # Touceiras / forracao / epifitas vendidas como muda.
    "00021142": "Muda e forracao",           # MOREIA BRANCA ITO
    "3302": "Muda e forracao",               # ASYSTACIA
    "201": "Muda e forracao",                # STRELITZIA 2 A 3 BULBOS 80 CM
    "00020893": "Muda e forracao",           # STRELITZIA DE SEMENTE 2 A 3 BULBOS
    "00020175": "Muda e forracao",           # BARBA DE VELHO (TILLANDSIA USNEOIDES)
    # Recipientes vazios e defensivos.
    "1525": "Insumo e acessorio",            # VASO ROMANO VR-03 CERAMICA
    "00030040": "Insumo e acessorio",        # OLEO DE ANDIROBA 50ML (repelente)
    # Comestiveis.
    "00140066": "Hortalica e erva",          # PIMENTAO
}

# 2. Regras por palavra-chave sobre produto_nome. ORDEM IMPORTA (primeira que casar vence).
CATEGORIA_REGRAS: list[tuple[re.Pattern, str]] = [
    # Linhas que NAO sao produto fisico — frete, taxa, mao de obra, locacao. Sem
    # perecibilidade nem demanda de reposicao; separadas para nao poluir as series L1.
    # Checadas ANTES de tudo (ex.: "FRETE" nunca deve virar outra coisa).
    (re.compile(r"\b(FRETE|TAXA\s+DE\s+|MAO\s+DE\s+OBRA|LOCA[CÇ][AÃ]O|ALUGUEL|"
                r"SERVI[CÇ]O\s+DE\s+PLANTIO|PROJETO\s+PAISAG|"
                r"PRESTA[CÇ][AÃ]O\s+DE\s+SERVI[CÇ]O)\b", re.I),
     "Servico e taxa"),

    # Flor de corte e arranjos montados — fatia pequena, mas a mais pericivel. Flor de
    # corte e a que compoe arranjos e buques. "MOLIO"/"MOLHO" = venda em maco de hastes
    # (aster, rosa spray) — sempre flor de corte. "COROA" so vale a de flores (funeral):
    # "COROA DE CRISTO" e planta.
    (re.compile(r"\b(FLOR\s+DE\s+CORTE|ROSA\s+EM\s+CABO|ALSTROEMERIA|ASTROMELIA|"
                r"BUQU[EÊ]|ARRANJO|COROA\s+DE\s+FLORES|LIRIO\s+CORTE|"
                r"MOLIO|MOLHO)\b", re.I),
     "Flor de corte e arranjo"),
    # Gerbera, crisantemo e tango soltos so sao flor de corte quando o nome NAO traz sinal
    # de embalagem: "GERBERA PT 15", "CRISANTEMO VB (VASO BARRO)" sao planta envasada e
    # seguem a cascata (PT/VB -> Planta em vaso; CACHEPO/VASO -> Insumo e acessorio).
    (re.compile(r"^(?!.*\b(PT\s?\d{1,2}|VB|POTE|SAQ\w*|SQ|CUIA|VASO|CACHEP\w*)\b)"
                r".*\b(GERBERA|CRISANTEMO|TANGO)\b", re.I),
     "Flor de corte e arranjo"),

    # Hortalicas, ervas e produce (mudas comestiveis / horta). `HORTALIC\w*` cobre o
    # plural "HORTALICAS" (o \b apos "...ICA" nao casava "...ICAS").
    (re.compile(r"\b(ERVAS?\s+AROMATICAS|TEMPEROS?|HORTALIC\w*|HORTALI[ÇC]AS?|HORTA|"
                r"JIL[OÓ]|QUIABO|MEXERICA|PONKAN|INHAME|MANDIOCA|COUVE|ALFACE|"
                r"CEBOLINHA|SALSINHA|PIMENTA\s+|MORANGO)\b", re.I),
     "Hortalica e erva"),

    # Substrato, terra, adubo, condicionador de solo, drenagem.
    # `ARGILA` sem sufixo cobre "ARGILA EXPANDIDA FRACIONADA" (o \b apos "EXP" nao casava
    # a palavra inteira). BIO BRICK / ECO CHIP = briquete de fibra de coco.
    (re.compile(r"\b(TERRA|ADUBO|SUBSTRATO|COMPOSTO\s+ORGANICO|HUMUS|BIOPLANT|"
                r"CASCA\s+DE\s+PINUS|FERTILIZANTE|CALCARIO|VERMICULITA|TURFA|PERLITA|"
                r"CONDICIONADOR|ARGILA|ESTERCO|MUSGO|FORTH|OSMOCOTE|NPK|GENESOLO|"
                r"BIO\s?BRICK|ECO\s?CHIP|FIBRA\s+DE\s+COCO|"
                r"TORTA\s+DE\s+MAMONA|BOKASHI|OSSO\s+MOIDO|FARINHA\s+DE\s+OSSO)\b", re.I),
     "Substrato e adubo"),

    # Insumos e acessorios de jardinagem (nao vivos): recipientes vazios, decoracao,
    # ferramentas. "POTE PRETO 06", "PRATO 21", "VASO PLAST.PAREDE", "VASOS CERAMICA".
    (re.compile(r"\b(MANTA|BIDIM|SEPARADOR\s+DE\s+GRAMA|TUTOR|REGADOR|FERRAMENTA|"
                r"VASO\s+PL[AÁ]STICO|VASO\s+PL\b|VASO\s+PLAST|VASOS?\s+(DE\s+)?CER[AÂ]MICA|"
                r"VASO\s+USADO|VASO\s+POLIET|VASO\s+BIG|VASO\s+TRANCADO|POLIET|CACHEPOT|"
                r"CACHEP[OÔ]|PEDRA|SEIXO|"
                r"PASTILHA|TELA|GRAMPO|ESTACA|MANGUEIRA|PULVERIZADOR|LUVA|SACO\s+PARA|"
                r"PRATO|POTE\s+(PRETO|PRPL|PLAST|BRANCO|BR\b)|ENFEITE|TRIP[EÉ]|"
                r"FLORAL\s+(MENOR|MAIOR|MEDIO|F\d)|F1000|SUPORTE|TREL[IÍ][CÇ]A|"
                r"BACIA|JARDINEIRA|CART[AÃ]O|ETIQUETA|PLAQUINHA|SUBSTITUI[CÇ][AÃ]O|"
                r"FORMICIDA|ISCA\s+PARA\s+FORMIGA|MIREX|INSETICIDA|FUNGICIDA|"
                r"DEFENSIVO|CUPINICIDA|HERBICIDA|BORAL|OLEO\s+DE\s+NEEM)\b", re.I),
     "Insumo e acessorio"),

    # "Grama preta" / "pelo de urso" e forracao (Ophiopogon) — vendida como muda, NAO e
    # grama de plantio. Checar ANTES da regra de GRAMA.
    (re.compile(r"\b(GRAMA\s+PRETA|PELO\s+D[EO]?\s*URSO)\b", re.I),
     "Muda e forracao"),

    # Grama de plantio (esmeralda, sao carlos, amendoim, batatais, coreana...).
    (re.compile(r"\bGRAMA\b", re.I),
     "Grama"),

    # --- Sinais de FORMATO/RECIPIENTE (fortes: dizem COMO o produto e vendido) ---

    # Arbusto / planta ja formada — nome traz FAIXA de altura ("0,20 A 0,30CM",
    # "50 A 60 CM", "0,80 A 1,20MT"). Faixa de porte = planta ja formada de campo/bag.
    (re.compile(r"\d+[.,]?\d*\s*(A|À)\s*\d+[.,]?\d*\s*(CM|MTS?|MT|M)\b", re.I),
     "Arbusto e planta formada"),

    # Planta em vaso — codigo de vaso "PT 11", "PT13", "VB" (vaso de barro); codigo/volume
    # de pote "P14", "3L", "8 L", "5 LITROS", "POTE PP". Recipiente rigido = planta envasada.
    (re.compile(r"\b(PT\s?\d{1,2}|VB)\b", re.I),
     "Planta em vaso"),
    (re.compile(r"(\bP\s?1\d\b|\b\d+\s?L(ITROS?)?\b|\bPOTE\s?(PP|PM|PG|\d{2})\b)", re.I),
     "Planta em vaso"),

    # Muda / forracao pelo FORMATO de venda: saquinho, sacola, cuia, bandeja, touceira,
    # pote pequeno codificado ("C21", "C 25"). Capim/forracao rasteira tambem entra aqui.
    # `SAQ\w*` cobre "SAQ", "SAQUINHO", "SAQUINHOS" (o \b apos "SAQ" nao casava o resto).
    (re.compile(r"\b(SAQ\w*|SQ|MUDAS?|BANDEJA|BDJA?|BDJ|TOUCEIRA|SUNPATIENS|BEIJO|"
                r"SACOL[AÃ]O?|CUIA|CUIETE|C\s?\d{2}\b|CX\s?\d{2}|CAPIM)\b", re.I),
     "Muda e forracao"),

    # --- Fallback por ESPECIE/TIPO (fracos: so o nome botanico, sem formato). Vem depois
    #     dos sinais de recipiente para que "IXORA PT 13" caia em "Planta em vaso". ---

    # Arbustos topiarios / plantas formadas tipicas vendidas por porte, sem faixa no nome.
    (re.compile(r"\b(BUXINHO|MURTA|PODOCARP[OU]S?|MANACA\s+DA\s+SERRA|"
                r"AZALEIA\s+TOPIARIA|CLUSIA|IXORA|PITTOSPORUM|PITOSPORO|"
                r"ESPONJINHA|CALIANDRA|BAMBU|BAMBUSA|EUCALIPTO|OLIVEIRA|"
                r"COROA\s+DE\s+CRISTO)\b", re.I),
     "Arbusto e planta formada"),

    # Bromelia, orquidea e arvore da felicidade sao sempre comercializadas envasadas.
    (re.compile(r"\b(BROM[EÉ]LIA|ORQU[IÍ]DEA|[AÁ]RVORE\s+DA\s+FELICIDADE)", re.I),
     "Planta em vaso"),

    # Produto cujo nome e literalmente "INSUMO".
    (re.compile(r"^\s*INSUMO\s*$", re.I),
     "Insumo e acessorio"),
]

CATEGORIA_DEFAULT = "Outros"

# Colapso `categoria_fina` (~10) -> `categoria` L1 (3 de demanda + 1 nao-produto).
# Grama e Flores de corte diferem em dinamica (calendario comemorativo, perfil semanal) e
# ganham serie L1 (o teste de separacao, eda_separacao.py, nao mostra ganho de acuracia); plantas e insumos sao o par de grupos mais proximo e modelar cada um
# direto nao erra menos do que repartir a previsao de "Produtos de jardim" (ADR-011,
# eda_grupos.py), entao formam uma serie L1 so. "Servico e taxa" (frete, mao de obra) NAO
# e produto — fica com rotulo proprio para ser excluido da serie de demanda L1.
CATEGORIA_L1: dict[str, str] = {
    "Grama":                    "Grama",
    "Flor de corte e arranjo":  "Flores de corte",
    "Hortalica e erva":         "Produtos de jardim",
    "Muda e forracao":          "Produtos de jardim",
    "Planta em vaso":           "Produtos de jardim",
    "Arbusto e planta formada": "Produtos de jardim",
    "Substrato e adubo":        "Produtos de jardim",
    "Insumo e acessorio":       "Produtos de jardim",
    "Outros":                   "Produtos de jardim",
    "Servico e taxa":           "Servico e taxa",
}

CATEGORIA_L1_DEFAULT = "Produtos de jardim"

# Colapso `categoria_fina` -> grupo de produto (vocabulario do cliente). "Outros" (cauda
# de especies sem palavra-chave) e majoritariamente planta e vai para Plantas diversas.
# Arvores nao tem regra propria (a lista do grupo no ERP nao esta disponivel): ficam em
# Plantas diversas (~0,4% a 1,2% do volume por unidade, ver eda_grupos.py).
GRUPO_PRODUTO: dict[str, str] = {
    "Grama":                    "Grama",
    "Flor de corte e arranjo":  "Flores de corte",
    "Hortalica e erva":         "Plantas diversas",
    "Muda e forracao":          "Plantas diversas",
    "Planta em vaso":           "Plantas diversas",
    "Arbusto e planta formada": "Plantas diversas",
    "Outros":                   "Plantas diversas",
    "Substrato e adubo":        "Insumos e acessórios",
    "Insumo e acessorio":       "Insumos e acessórios",
    "Servico e taxa":           "Servico e taxa",
}

GRUPO_PRODUTO_DEFAULT = "Plantas diversas"


def map_categoria(produto_cod, produto_nome) -> str:
    """`categoria_fina` de um produto pela cascata SKU -> regras -> default."""
    cod = "" if produto_cod is None else str(produto_cod).strip()
    if cod in CATEGORIA_POR_SKU:
        return CATEGORIA_POR_SKU[cod]
    nome = "" if produto_nome is None else str(produto_nome).strip()
    for rx, cat in CATEGORIA_REGRAS:
        if rx.search(nome):
            return cat
    return CATEGORIA_DEFAULT


def map_categoria_l1(produto_cod, produto_nome) -> str:
    """`categoria` do nivel L1 do modelo (3 de demanda + "Servico e taxa")."""
    return CATEGORIA_L1.get(map_categoria(produto_cod, produto_nome), CATEGORIA_L1_DEFAULT)


def map_grupo(produto_cod, produto_nome) -> str:
    """Grupo de produto (vocabulario do cliente) — so para apresentacao, nao e serie L1."""
    return GRUPO_PRODUTO.get(map_categoria(produto_cod, produto_nome), GRUPO_PRODUTO_DEFAULT)
