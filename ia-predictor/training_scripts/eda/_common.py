"""Infraestrutura compartilhada dos dois EDAs (T000b).

Carrega as bases, normaliza rótulos/tipos, define o calendário de datas
comemorativas e a identidade visual dos gráficos. Nenhuma análise mora aqui —
só o que `eda_source.py` e `eda_series.py` precisam em comum.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.eda.eda_source
    python -m training_scripts.eda.eda_series
    python -m training_scripts.eda.run_all
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

# Console do Windows costuma ser cp1252 — força UTF-8 p/ os prints com acento/·/→.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# --------------------------------------------------------------------------- #
# Caminhos
# --------------------------------------------------------------------------- #
_EDA_DIR = os.path.dirname(os.path.abspath(__file__))
_TRAINING_SCRIPTS_DIR = os.path.dirname(_EDA_DIR)
_IA_PREDICTOR_ROOT = os.path.dirname(_TRAINING_SCRIPTS_DIR)
REPO_ROOT = os.path.dirname(_IA_PREDICTOR_ROOT)

# Base transacional canônica de produção (20 colunas) — usada pelo EDA 1.
CONSOLIDATED_CSV = os.path.join(
    _IA_PREDICTOR_ROOT, "data", "processed", "contas_a_receber.csv"
)
# Saída da Etapa 3 do pré-processamento (12 colunas: + unidade/categoria/categoria_fina).
TAXONOMY_CSV = os.path.join(
    _TRAINING_SCRIPTS_DIR, "output", "contas_a_receber_taxonomia.csv"
)

PLOTS_DIR = os.path.join(_TRAINING_SCRIPTS_DIR, "results", "plots", "eda")
METRICS_DIR = os.path.join(_TRAINING_SCRIPTS_DIR, "results", "metrics")

# --------------------------------------------------------------------------- #
# Rótulos canônicos (defesa contra o mojibake de encoding — ver §Qualidade do
# relatório: o CSV da Etapa 3 é gravado em cp1252 neste ambiente Windows).
# --------------------------------------------------------------------------- #
UNIDADES = ["Jardim Canadá", "Itabirito", "Garden Center"]
CATEGORIAS_L1 = ["Grama", "Plantas de corte", "Produtos de jardim"]
NAO_PRODUTO = "Servico e taxa"

_UNIDADE_FIX = {
    "jardim canada": "Jardim Canadá",
    "jardim canadá": "Jardim Canadá",
    "itabirito": "Itabirito",
    "garden center": "Garden Center",
}
_CATEGORIA_FIX = {
    "grama": "Grama",
    "plantas de corte": "Plantas de corte",
    "produtos de jardim": "Produtos de jardim",
    "servico e taxa": "Servico e taxa",
    "serviço e taxa": "Servico e taxa",
}


def _canon(series: pd.Series, table: dict, name: str) -> pd.Series:
    key = series.astype(str).str.strip().str.lower()
    out = key.map(table)
    if out.isna().any():
        bad = sorted(series[out.isna()].astype(str).unique())[:5]
        raise ValueError(f"[{name}] valores fora do dicionário canônico: {bad}")
    return out


# --------------------------------------------------------------------------- #
# MG / Brasil — datas comemorativas fortes para floricultura + feriados fixos
# --------------------------------------------------------------------------- #
def _segundo_domingo_maio(ano: int) -> date:
    d = date(ano, 5, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)  # 1º domingo
    return d + timedelta(days=7)               # 2º domingo


def _dia_dos_pais(ano: int) -> date:
    """2º domingo de agosto."""
    d = date(ano, 8, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(days=7)


def datas_comemorativas(anos) -> pd.DataFrame:
    """Datas que puxam demanda de flor/planta, uma linha por (evento, ano)."""
    linhas = []
    for ano in anos:
        linhas += [
            ("Dia das Mães", _segundo_domingo_maio(ano)),
            ("Dia dos Namorados", date(ano, 6, 12)),
            ("Finados", date(ano, 11, 2)),
            ("Natal", date(ano, 12, 25)),
            ("Dia da Mulher", date(ano, 3, 8)),
            ("Dia dos Pais", _dia_dos_pais(ano)),
        ]
    df = pd.DataFrame(linhas, columns=["evento", "data"])
    df["data"] = pd.to_datetime(df["data"])
    return df


FERIADOS_FIXOS_BR = [  # (mês, dia) — nacionais fixos + relevantes p/ comércio MG
    (1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25),
]


def feriados_fixos(anos) -> pd.DatetimeIndex:
    out = [pd.Timestamp(a, m, d) for a in anos for (m, d) in FERIADOS_FIXOS_BR]
    return pd.DatetimeIndex(sorted(out))


# --------------------------------------------------------------------------- #
# Carregamento
# --------------------------------------------------------------------------- #
def _read_csv_resiliente(path: str, **kw) -> pd.DataFrame:
    """Lê tolerando o encoding inconsistente das saídas do pré-processamento."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return pd.read_csv(path, sep=";", dtype=str, low_memory=False,
                               encoding=enc, **kw)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return pd.read_csv(path, sep=";", dtype=str, low_memory=False,
                       encoding="latin-1", encoding_errors="replace", **kw)


def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce",
    )


def load_transacoes() -> pd.DataFrame:
    """Base transacional (1 linha por documento×produto) já enriquecida com a
    taxonomia da Etapa 3. Colunas numéricas convertidas; `data` como datetime."""
    con = _read_csv_resiliente(CONSOLIDATED_CSV)
    tax = _read_csv_resiliente(
        TAXONOMY_CSV, usecols=["unidade", "categoria", "categoria_fina"]
    )
    if len(con) != len(tax):
        raise RuntimeError(
            f"CSV consolidado ({len(con)}) e taxonomia ({len(tax)}) desalinhados"
        )
    df = pd.concat([con.reset_index(drop=True), tax.reset_index(drop=True)], axis=1)

    df["unidade"] = _canon(df["unidade"], _UNIDADE_FIX, "unidade")
    df["categoria"] = _canon(df["categoria"], _CATEGORIA_FIX, "categoria")
    df["data"] = pd.to_datetime(df["emissao"], format="%d/%m/%Y", errors="coerce")
    for c in ["qtdade", "vl_unit", "vl_total", "vl_desconto", "tot_liq",
              "total_liquido_doc"]:
        df[c + "_n"] = _to_num(df[c])
    return df


def serie_diaria(df_trans: pd.DataFrame, unidade: str, categoria: str,
                 span: str = "par") -> pd.Series:
    """Reconstrói a série-alvo do L1: soma de `qtdade` por dia para o par
    (unidade, categoria), reindexada no range diário contínuo (dias sem venda = 0).

    span="par"    → primeiro ao último dia com venda do próprio par
    span="global" → primeiro ao último dia com venda em toda a base
    """
    m = (df_trans["unidade"] == unidade) & (df_trans["categoria"] == categoria)
    s = (df_trans.loc[m].dropna(subset=["data"])
         .groupby("data")["qtdade_n"].sum().sort_index())
    if s.empty:
        return s
    if span == "global":
        lo, hi = df_trans["data"].min(), df_trans["data"].max()
    else:
        lo, hi = s.index.min(), s.index.max()
    idx = pd.date_range(lo.normalize(), hi.normalize(), freq="D")
    return s.reindex(idx, fill_value=0.0).rename(f"{unidade} · {categoria}")


def pares_l1(df_trans: pd.DataFrame) -> list[tuple[str, str]]:
    d = df_trans[df_trans["categoria"] != NAO_PRODUTO]
    return sorted(map(tuple, d[["unidade", "categoria"]].drop_duplicates().values))


# --------------------------------------------------------------------------- #
# Gráficos + persistência
# --------------------------------------------------------------------------- #
def setup_plotting():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 130, "savefig.bbox": "tight",
        "font.size": 9, "axes.titlesize": 11, "axes.grid": True,
        "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "white", "axes.facecolor": "white",
    })
    return plt


PALETA = {
    "Grama": "#2E7D32",
    "Plantas de corte": "#C2185B",
    "Produtos de jardim": "#F9A825",
    "Servico e taxa": "#90A4AE",
    "Jardim Canadá": "#1565C0",
    "Itabirito": "#6A1B9A",
    "Garden Center": "#00838F",
}


def ensure_dirs():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(METRICS_DIR, exist_ok=True)


def savefig(fig, nome: str) -> str:
    ensure_dirs()
    path = os.path.join(PLOTS_DIR, nome)
    fig.savefig(path)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")


def dump_metrics(nome: str, obj: dict) -> str:
    ensure_dirs()
    path = os.path.join(METRICS_DIR, nome)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, default=_json_default)
    return os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.ndarray,)):
        return o.tolist()
    if isinstance(o, (pd.Timestamp, date)):
        return o.isoformat()[:10]
    raise TypeError(repr(o))


def fmt_int(n) -> str:
    return f"{int(n):,}".replace(",", ".")
