"""Tratamentos da planilha na conferência da importação, item a item, para a loja corrigir.

A conferência (`upload_service.verificar`) devolvia só contagens ("19 linhas ignoradas").
Aqui cada problema vira um grupo com onde está (linha do Excel), os campos ligados a ele —
com o campo do problema marcado em `highlight` — e o que fazer. Dois níveis:

  * `corrigir` — interrompe: a venda fica de fora até a planilha ser corrigida (nota fora
                 do formato, campo obrigatório vazio, data inválida, número em texto);
  * `aviso`    — não interrompe: a planilha pode ser gravada assim (nota sem a linha do
                 cliente, dias de loja aberta sem venda, empresa sem loja, produto sem
                 categoria).

Campo vazio só gera alerta quando é obrigatório (`CAMPOS_OBRIGATORIOS` da Etapa 2: data de
emissão, código do produto e quantidade). Funções puras sobre DataFrames das Etapas 1–3
(`training_scripts/preprocessing`), sem I/O. A linha é a do Excel (1 = primeira linha).
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

MAX_ITENS = 100  # itens listados por grupo; a contagem continua sendo a de todos

NIVEIS = ("corrigir", "aviso")

ROTULOS = {
    "nota": "Nota",
    "emissao": "Data de emissão",
    "loja": "Loja",
    "empresa": "Empresa",
    "produto_cod": "Código do produto",
    "produto_nome": "Produto",
    "produto": "Produto",
    "qtdade": "Quantidade",
    "vl_unit": "Valor unitário",
    "vl_total": "Valor total",
    "vl_desconto": "Desconto",
    "tot_liq": "Total líquido",
    "icms_ret": "ICMS retido",
    "total_liquido_doc": "Total líquido da nota",
    "itens": "Itens",
    "cliente": "Cliente",
    "categoria": "Categoria",
    "esperado": "Falta a linha",
    "encontrado": "No lugar veio",
    "periodo": "Período",
    "dias": "Dias",
}

# A linha que faltou, como ela aparece no relatório
LINHAS_DO_RELATORIO = {"Produto": "Produto | Qtdade | Vl. Unit. | Vl. Total", "Cliente:": "Cliente: código - nome"}

_ESPERAVA = re.compile(r"Esperava '([^']+)' na linha (\d+), encontrado: '(.*)'", re.S)


@dataclass
class ItemTratamento:
    line: int | None                       # linha do Excel
    values: dict[str, str | None]          # chave da coluna → valor como está na planilha
    highlight: list[str] = field(default_factory=list)  # colunas com o problema


@dataclass
class ColunaTratamento:
    key: str
    label: str


@dataclass
class GrupoTratamento:
    kind: str
    level: str                             # NIVEIS
    title: str
    how_to_fix: str | None
    count: int                             # linhas, notas ou dias (`count_label`)
    count_label: str
    columns: list[ColunaTratamento]
    items: list[ItemTratamento] = field(default_factory=list)
    total_items: int = 0                   # itens antes do corte em MAX_ITENS


def _plural(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural or singular + 's')}"


def _grupo(kind, level, title, how_to_fix, count, count_label, chaves, itens) -> GrupoTratamento:
    itens = sorted(itens, key=lambda i: (i.line is None, i.line or 0))
    return GrupoTratamento(kind=kind, level=level, title=title, how_to_fix=how_to_fix, count=int(count),
                           count_label=count_label, columns=[ColunaTratamento(k, ROTULOS[k]) for k in chaves],
                           items=itens[:MAX_ITENS], total_items=len(itens))


def _int(valor) -> int | None:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


def _texto(valor) -> str | None:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    texto = " ".join(str(valor).split())
    return texto or None


def _data_br(valor) -> str | None:
    """Data já tratada ('2026-03-18', Timestamp) → '18/03/2026'; o resto fica como veio (é o
    que está na planilha)."""
    if isinstance(valor, (pd.Timestamp, date)) and not pd.isna(valor):
        return f"{valor:%d/%m/%Y}"
    texto = _texto(valor)
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?: 00:00:00)?", texto or "")
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else texto


def _nota(linha) -> str | None:
    return _texto(" ".join(x for x in (_texto(linha.get("doc_tipo")), _texto(linha.get("doc_numero"))) if x))


def _produto(linha) -> str | None:
    cod, nome = _texto(linha.get("produto_cod")), _texto(linha.get("produto_nome"))
    return f"{cod} - {nome}" if cod and nome else (nome or cod)


def _por_nota(df: pd.DataFrame) -> list[tuple[pd.Series, pd.DataFrame]]:
    """(primeira linha, linhas) de cada nota: o erro da nota se corrige num lugar só."""
    chaves = [c for c in ("doc_tipo", "doc_numero", "emissao", "empresa") if c in df.columns]
    return [(g.iloc[0], g) for _, g in df.groupby(chaves, sort=False, dropna=False)]


# --------------------------------------------------------------------------- #
# corrigir: a venda fica de fora
# --------------------------------------------------------------------------- #

def notas_fora_do_formato(puladas: list[dict], loja_de: Callable[[str], str | None]) -> GrupoTratamento | None:
    """Notas que a Etapa 1 não conseguiu ler (`parse_xlsx`, `skipped`)."""
    if not puladas:
        return None
    itens = []
    for p in puladas:
        m = _ESPERAVA.search(str(p.get("reason", "")))
        esperado, linha, encontrado = (LINHAS_DO_RELATORIO.get(m.group(1), m.group(1)), int(m.group(2)),
                                       _texto(m.group(3)) or "linha em branco") \
            if m else ("uma linha do relatório", _int(p.get("line")), None)
        empresa = _texto(p.get("empresa"))
        itens.append(ItemTratamento(line=linha, highlight=["esperado"], values={
            "nota": _texto(str(p.get("content", "")).replace("Documento:", "")),
            "emissao": _texto(p.get("emissao")), "loja": loja_de(empresa or "") if empresa else None,
            "esperado": esperado, "encontrado": encontrado}))
    return _grupo("nota_fora_do_formato", "corrigir", "Nota com linha faltando",
                  "Sem essa linha o sistema não consegue ler a nota, e ela inteira fica de fora. "
                  "Devolva a linha na nota ou exporte o relatório de novo.",
                  len(puladas), _plural(len(puladas), "nota"),
                  ["nota", "emissao", "loja", "esperado", "encontrado"], itens)


def linhas_removidas(removidas: pd.DataFrame, loja_de: Callable[[str], str | None]) -> list[GrupoTratamento]:
    """Linhas que a limpeza (Etapa 2) tirou, com o motivo (`tratar_dados(removidas_csv=...)`)."""
    if removidas is None or removidas.empty:
        return []
    loja = lambda r: loja_de(_texto(r.get("empresa")) or "")  # noqa: E731
    return [g for g in (_campo_vazio(removidas[removidas["motivo"] == "campo_obrigatorio_vazio"], loja),
                        _data_invalida(removidas[removidas["motivo"] == "data_invalida"], loja),
                        _numero_em_texto(removidas[removidas["motivo"] == "valor_nao_numerico"], loja))
            if g is not None]


def _campo_vazio(df: pd.DataFrame, loja) -> GrupoTratamento | None:
    """Data de emissão, código do produto ou quantidade vazios. A data vazia vale para a nota
    inteira (fica na linha do `Documento:`): vira um item só, com o número de itens."""
    if df.empty:
        return None
    itens = []
    data_vazia = df["campo"].str.split(",").map(lambda cs: [c.strip() for c in cs] == ["emissao"])
    for r, g in _por_nota(df[data_vazia]):
        itens.append(ItemTratamento(line=_int(r.get("linha_documento")), highlight=["emissao"], values={
            "nota": _nota(r), "loja": loja(r), "emissao": None, "produto_cod": None,
            "produto_nome": _plural(len(g), "item", "itens") + " da nota", "qtdade": None}))
    for _, r in df[~data_vazia].iterrows():
        vazios = [c.strip() for c in str(r["campo"]).split(",") if c.strip()]
        itens.append(ItemTratamento(line=_int(r.get("linha_planilha")), highlight=vazios, values={
            "nota": _nota(r), "loja": loja(r), "emissao": _texto(r.get("emissao")),
            "produto_cod": _texto(r.get("produto_cod")), "produto_nome": _texto(r.get("produto_nome")),
            "qtdade": _texto(r.get("qtdade"))}))
    return _grupo("campo_vazio", "corrigir", "Campo obrigatório vazio", "Preencha o campo na linha indicada.",
                  len(df), _plural(len(df), "linha"),
                  ["nota", "loja", "emissao", "produto_cod", "produto_nome", "qtdade"], itens)


def _data_invalida(df: pd.DataFrame, loja) -> GrupoTratamento | None:
    if df.empty:
        return None
    itens = [ItemTratamento(line=_int(r.get("linha_documento")), highlight=["emissao"], values={
                "nota": _nota(r), "loja": loja(r), "emissao": _texto(r.get("valor")),
                "itens": _plural(len(g), "item", "itens")})
             for r, g in _por_nota(df)]
    return _grupo("data_invalida", "corrigir", "Data inválida", "Escreva a data como dd/mm/aaaa (ex.: 20/03/2026).",
                  len(df), _plural(len(df), "linha"), ["nota", "loja", "emissao", "itens"], itens)


def _numero_em_texto(df: pd.DataFrame, loja) -> GrupoTratamento | None:
    if df.empty:
        return None
    chaves = ["nota", "loja", "produto", "qtdade", "vl_unit", "vl_total"]
    extras = [c for c in df["campo"].unique() if c not in chaves]  # desconto, total líquido...
    itens = [ItemTratamento(line=_int(r.get("linha_planilha")), highlight=[r["campo"]], values={
                "nota": _nota(r), "loja": loja(r), "produto": _produto(r),
                **{c: _texto(r.get(c)) for c in ["qtdade", "vl_unit", "vl_total", *extras]}})
             for _, r in df.iterrows()]
    return _grupo("valor_nao_numerico", "corrigir", "Quantidade ou valor em texto",
                  "Escreva só o número (ex.: 10 ou 12,50).", len(df), _plural(len(df), "linha"),
                  chaves + extras, itens)


# --------------------------------------------------------------------------- #
# aviso: não impede gravar
# --------------------------------------------------------------------------- #

def sem_linha_cliente(df: pd.DataFrame, loja: Callable[[pd.Series], str | None]) -> GrupoTratamento | None:
    """Notas sem a linha `Cliente:`: entram com o cliente vazio (o cliente não é obrigatório)."""
    if df is None or df.empty or "sem_linha_cliente" not in df.columns:
        return None
    df = df[df["sem_linha_cliente"].astype(str) == "True"]
    if df.empty:
        return None
    itens = [ItemTratamento(line=_int(r.get("linha_documento")) + 1 if _int(r.get("linha_documento")) else None,
                            highlight=["cliente"], values={
                                "nota": _nota(r), "loja": loja(r), "emissao": _data_br(r.get("emissao")),
                                "cliente": None, "itens": _plural(len(g), "item", "itens")})
             for r, g in _por_nota(df)]
    return _grupo("sem_linha_cliente", "aviso", "Nota sem a linha “Cliente:”",
                  "A venda entra sem o cliente. Para registrar o cliente, devolva a linha abaixo do “Documento:”.",
                  len(itens), _plural(len(itens), "nota"), ["nota", "loja", "emissao", "cliente", "itens"], itens)


def dias_sem_venda(faltando: list[dict]) -> GrupoTratamento | None:
    """Dias de loja aberta que ficariam sem venda (`domain.etl.cobertura`)."""
    if not faltando:
        return None
    itens = []
    for f in faltando:
        for intervalo in f["ranges"]:
            a, b = intervalo["start"], intervalo["end"]
            itens.append(ItemTratamento(line=None, highlight=["periodo"], values={
                "loja": f["unit_name"],
                "periodo": f"{a:%d/%m/%Y}" if a == b else f"{a:%d/%m/%Y} a {b:%d/%m/%Y}",
                "dias": str((b - a).days + 1)}))
    total = sum(f["days"] for f in faltando)
    return _grupo("dias_sem_venda", "aviso", "Dias de loja aberta sem venda",
                  "Se a loja abriu nesses dias, envie a planilha deles antes de treinar.",
                  total, _plural(total, "dia"), ["loja", "periodo", "dias"], itens)


def empresas_sem_loja(df: pd.DataFrame) -> GrupoTratamento | None:
    """Linhas de empresa que não é de nenhuma loja cadastrada (Etapa 3: unidade desconhecida)."""
    if df is None or df.empty:
        return None
    itens = [ItemTratamento(line=_int(g["linha_documento"].min()) if "linha_documento" in g else None,
                            highlight=["empresa"], values={
                                "nota": _nota(r), "emissao": _data_br(r.get("emissao")),
                                "empresa": _texto(r.get("empresa")), "itens": _plural(len(g), "item", "itens")})
             for r, g in _por_nota(df)]
    return _grupo("empresa_sem_loja", "aviso", "Empresa sem loja cadastrada",
                  "As vendas dessa empresa não entram. Se for de uma das lojas, avise a equipe do projeto.",
                  len(df), _plural(len(df), "linha"), ["nota", "emissao", "empresa", "itens"], itens)


def categoria_desconhecida(df: pd.DataFrame, loja: Callable[[pd.Series], str | None]) -> GrupoTratamento | None:
    if df is None or df.empty:
        return None
    itens = [ItemTratamento(line=_int(r.get("linha_planilha")), highlight=["categoria"], values={
                "nota": _nota(r), "loja": loja(r), "produto": _produto(r), "categoria": _texto(r.get("categoria"))})
             for _, r in df.iterrows()]
    return _grupo("categoria_desconhecida", "aviso", "Produto sem categoria",
                  "Essas vendas não entram. Avise a equipe do projeto.",
                  len(df), _plural(len(df), "linha"), ["nota", "loja", "produto", "categoria"], itens)


def ordenar(grupos: list[GrupoTratamento | None]) -> list[GrupoTratamento]:
    """Tira os vazios e ordena por nível: primeiro o que interrompe, depois os avisos."""
    return sorted((g for g in grupos if g is not None), key=lambda g: NIVEIS.index(g.level))
