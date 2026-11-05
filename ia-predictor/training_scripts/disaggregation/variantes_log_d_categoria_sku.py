"""Transformacao e diferenciacao nas series de categoria e de SKU: 3 variantes x 6 series.

Pergunta
--------
No L1 da loja, `log1p` + d = 1 venceu (doc 04). Mas a serie da loja e densa e tem nivel que
anda; uma categoria tem menos volume e mais zero, e um SKU e ruidoso e volta a media. As
duas escolhas do L1 valem um nivel abaixo, ou cada serie pede uma configuracao?

Alvo: fluxo diario (SEM encomendas)
-----------------------------------
Toda serie aqui e o fluxo diario: a venda cujo documento passa de `LIMIAR_QTD_VENDA`
(2.000 unidades no documento inteiro) sai da serie, pela mesma regra de
`preprocessing/remove_encomendas_06.py` — e a marcacao vale para o documento inteiro, nao
para a linha. E a mesma base dos treinos C e D de Itabirito e dos experimentos de SKU em
`sku_regular_vs_desagregacao.py`, o que torna os numeros comparaveis com eles.

O tamanho do documento e calculado DEPOIS de tirar `Servico e taxa`, na ordem de
`sku_regular_vs_desagregacao.carregar_fluxo`.

Series avaliadas (Itabirito, fluxo diario)
------------------------------------------
  * as 4 categorias do negocio: Grama, Plantas diversas, Produtos de jardim, Flores de corte;
  * os 2 SKUs mais regulares da categoria Grama, pelo ADI (dias de loja aberta no span /
    dias com venda) calculado so com dados anteriores a primeira origem — o mesmo ADI de
    `sku_regular_vs_desagregacao.py`.

A `categoria` vem de `categoria_fina` -> `CATEGORIA_NEGOCIO` (taxonomy), nao da coluna
`categoria` da `BaseClassificada03.csv`: aquele CSV foi gerado antes do corte atual da
taxonomia e traz so 3 categorias (Plantas diversas estava dentro de Produtos de jardim).

Variantes comparadas (a serie e as exogenas sao as mesmas; muda so o que o titulo diz)
--------------------------------------------------------------------------------------
  * `log1p|d1`   — alvo em log1p, d = 1 (a configuracao do L1 escolhido, doc 04);
  * `sem_log|d1` — alvo cru, d = 1;
  * `sem_log|d0` — alvo cru, d = 0 (com constante, `trend="c"`).

D = 0 e m = 7 em todas: o ciclo semanal entra pelas 6 dummies de dia da semana, como no L1.
As exogenas sao as 8 do L1 (dia da semana + `loja_fechada` + `abertura_excepcional`); os
indices de data comemorativa por categoria NAO entram aqui de proposito, para que a unica
diferenca entre as variantes seja a transformacao e o d.

AIC
---
Para cada (serie, variante) a ordem (p,q em 0..2; P,Q em 0..1) e escolhida por AIC com os
dados anteriores a primeira origem, **na escala que aquela variante de fato ajusta** (log1p
ou cru). O JSON guarda o AIC da ordem vencedora e as 5 melhores do grid.

Leitura obrigatoria do AIC: ele compara ordens dentro de uma mesma serie, mesma escala e
mesmo d. Entre as 3 variantes ele NAO compara — `log1p` muda a unidade da verossimilhanca e
d muda o numero de observacoes efetivas. Quem compara variante com variante e o
walk-forward.

Protocolo
---------
Walk-forward igual ao da loja (`sarimax_itabirito_core`): janela expansiva, a origem anda de
1 em 1 dia a partir de 2025-03-02 e cada ajuste preve os 14 dias seguintes — toda data
prevista aparece em ate 14 janelas, uma por horizonte h = 1..14. Nada olha o futuro: ordem,
ADI e escala do MASE saem so de dados anteriores a origem.

As metricas que decidem sao as dos dias de loja aberta. Domingo e feriado (venda 0, previsao
~0) baixam o MASE e sobem a cobertura sem dizer nada sobre a previsao.

Execucao em processos independentes (um por serie)
--------------------------------------------------
Cada serie roda no seu proprio processo, sequencialmente, e grava um `_previsoes.csv`
parcial; `--consolidar` junta tudo e calcula as metricas. Nao ha `ProcessPoolExecutor`: num
ambiente proot/Termux o pool quebra em runs longos ("futex facility returned an unexpected
error code") e derruba o experimento inteiro depois de meia hora de CPU. Processos
independentes, paralelizados pelo shell, nao compartilham futex e sobrevivem.

O grid de AIC (fase 1) fica em cache no `_grid_aic.csv`: se o arquivo ja cobre a
(serie, variante), as 36 ordens nao sao reajustadas. `--refazer-aic` ignora o cache.

Uso (a partir de `ia-predictor/`):
    # as 6 series, uma por processo, em paralelo
    python -m training_scripts.disaggregation.variantes_log_d_categoria_sku --listar-series
    for s in ...; do python -m ...variantes_log_d_categoria_sku --serie "$s" & done; wait
    python -m training_scripts.disaggregation.variantes_log_d_categoria_sku --consolidar
"""
from __future__ import annotations

import argparse
import ast
import itertools
import json
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import time  # noqa: E402
import warnings  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from statsmodels.tsa.statespace.sarimax import SARIMAX  # noqa: E402

from training_scripts.baseline.sarimax_itabirito_core import (  # noqa: E402
    ALPHA, CALENDARIO, GRID_PQ, GRID_SPQ, HORIZONTE, M, MAXITER, METRICS_DIR,
    PRIMEIRA_ORIGEM,
)
from training_scripts.disaggregation.sku_regular_vs_desagregacao import (  # noqa: E402
    ADI_CORTE, MIN_SPAN_DIAS, UNIDADES, exogenas, fechados_da_unidade,
)
from training_scripts.preprocessing.classificacao_03 import CLASSIFIED_CSV  # noqa: E402
from training_scripts.preprocessing.remove_encomendas_06 import (  # noqa: E402
    LIMIAR_QTD_VENDA, marcar_encomendas,
)
from training_scripts.preprocessing.taxonomy.categorias import (  # noqa: E402
    CATEGORIA_NEGOCIO, CATEGORIA_NEGOCIO_DEFAULT, CATEGORIAS_NEGOCIO,
)

warnings.filterwarnings("ignore")

PASSO = 1                  # a origem anda 1 dia -> janelas dia a dia, sobrepostas
D_SAZONAL = 0

# Janela de treino: None = expansiva (tudo antes da origem); um inteiro = deslizante desse
# tamanho. Importa para o teste de `d`: com `d = 0` o modelo leva `trend="c"`, e numa janela
# expansiva de 2 anos essa constante e a media de 2 anos — a previsao reverte para um nivel
# velho. Com janela deslizante a constante passa a ser a media recente, que e o conserto
# correto para media que anda devagar numa serie estacionaria (diferenciar nao e).
JANELA_TREINO: int | None = None
N_SKUS_GRAMA = 2
CATEGORIA_SKUS = "Grama"
CATEGORIA_NAO_PRODUTO = "Servico e taxa"

# (nome, usar_log1p, d). A ordem de insercao e a ordem dos relatorios.
VARIANTES: dict[str, dict] = {
    "log1p|d1":   {"log": True,  "d": 1},
    "sem_log|d1": {"log": False, "d": 1},
    "sem_log|d0": {"log": False, "d": 0},
}


# --------------------------------------------------------------------------- #
# Series
# --------------------------------------------------------------------------- #
def carregar_linhas(unidade: str) -> tuple[pd.DataFrame, dict[str, str], dict]:
    """Linhas do FLUXO DIARIO da unidade (sem `Servico e taxa` e sem encomendas).

    `categoria` e recalculada de `categoria_fina` pela taxonomia atual (ver docstring do
    modulo). A encomenda e marcada por documento (`marcar_encomendas`, limiar de 2.000
    unidades na venda inteira) e sai com todas as suas linhas juntas.
    """
    cols = ["unidade", "emissao", "doc_tipo", "doc_numero", "produto_cod", "produto_nome", "qtdade",
            "categoria_fina"]
    df = pd.read_csv(CLASSIFIED_CSV, sep=";", usecols=cols, dtype=str, keep_default_na=False)
    df["qtdade"] = pd.to_numeric(df["qtdade"], errors="coerce").fillna(0.0)
    df["emissao"] = pd.to_datetime(df["emissao"], errors="coerce")
    df = df[(df["unidade"] == unidade) & df["emissao"].notna()].copy()
    df["categoria"] = (df["categoria_fina"].map(CATEGORIA_NEGOCIO)
                       .fillna(CATEGORIA_NEGOCIO_DEFAULT))
    df = df[df["categoria"] != CATEGORIA_NAO_PRODUTO]
    nomes = df.sort_values("emissao").groupby("produto_cod")["produto_nome"].last().to_dict()

    encomenda = marcar_encomendas(df, LIMIAR_QTD_VENDA)
    corte = {
        "limiar_qtd_venda": LIMIAR_QTD_VENDA,
        "linhas_total": int(len(df)),
        "linhas_encomenda_removidas": int(encomenda.sum()),
        "qtd_total": round(float(df["qtdade"].sum()), 1),
        "qtd_encomenda_removida": round(float(df.loc[encomenda, "qtdade"].sum()), 1),
        "qtd_encomenda_pct": round(float(df.loc[encomenda, "qtdade"].sum()
                                         / df["qtdade"].sum() * 100), 1),
        "qtd_encomenda_pct_por_categoria": {
            cat: round(float(g.loc[encomenda.reindex(g.index, fill_value=False), "qtdade"].sum()
                             / g["qtdade"].sum() * 100), 1)
            for cat, g in df.groupby("categoria")
        },
    }
    return df[~encomenda].copy(), nomes, corte


def dias_abertos(unidade: str) -> pd.Series:
    """1 em dia de loja aberta, indexado por data (calendario da Etapa 6)."""
    cal = pd.read_csv(CALENDARIO, sep=";", parse_dates=["data"])
    cal = cal[cal["unidade"] == unidade].set_index("data").sort_index()
    return (cal["loja_fechada"] == 0).astype(int)


def _diaria(linhas: pd.DataFrame, fim: pd.Timestamp, inicio: pd.Timestamp | None = None) -> pd.Series:
    """Soma por dia, reindexada no calendario cheio (dia sem venda vira 0)."""
    s = linhas.groupby("emissao")["qtdade"].sum().sort_index()
    ini = inicio if inicio is not None else s.index.min()
    s = s.reindex(pd.date_range(ini, fim, freq="D"), fill_value=0.0).astype(float)
    s.index.name = "data"
    return s


def escolher_skus(linhas: pd.DataFrame, aberta: pd.Series, n: int) -> pd.DataFrame:
    """Os `n` SKUs de menor ADI da categoria `CATEGORIA_SKUS`, so com dados pre-origem.

    ADI = dias de loja aberta do span / dias com venda, span da 1a venda a vespera da
    primeira origem — a definicao de `sku_regular_vs_desagregacao.skus_regulares`. A coluna
    `regular_criterio_projeto` diz se o SKU passaria no corte do projeto (ADI < 1,32 e span
    >= 180 dias); escolher "os 2 mais regulares" nao garante que os 2 passem.
    """
    pre = linhas[(linhas["categoria"] == CATEGORIA_SKUS) & (linhas["emissao"] < PRIMEIRA_ORIGEM)]
    vespera = PRIMEIRA_ORIGEM - pd.Timedelta(days=1)
    reg = []
    for cod, d in pre.groupby("produto_cod"):
        dias_venda = int(d["emissao"].nunique())
        if dias_venda < 2:
            continue
        primeira = d["emissao"].min()
        span = int((vespera - primeira).days) + 1
        abertos = int(aberta.loc[primeira:vespera].sum())
        reg.append({
            "sku": cod, "dias_com_venda": dias_venda, "span_dias": span,
            "dias_abertos_no_span": abertos, "adi": round(abertos / dias_venda, 3),
            "qtd_pre_origem": round(float(d["qtdade"].sum()), 1),
            "regular_criterio_projeto": bool(abertos / dias_venda < ADI_CORTE
                                             and span >= MIN_SPAN_DIAS),
        })
    return pd.DataFrame(reg).sort_values(["adi", "dias_com_venda"],
                                         ascending=[True, False]).head(n).reset_index(drop=True)


def montar_series(unidade: str) -> tuple[dict[str, pd.Series], pd.DataFrame, dict]:
    """As 6 series do experimento + a tabela de escolha dos SKUs + metadados."""
    linhas, nomes, corte = carregar_linhas(unidade)
    aberta = dias_abertos(unidade)
    fim = linhas["emissao"].max()

    series: dict[str, pd.Series] = {}
    for cat in CATEGORIAS_NEGOCIO:
        d = linhas[linhas["categoria"] == cat]
        if d.empty:
            continue
        # Categoria comeca no 1o dia da base (todas vendem desde o inicio), para que as 4
        # series tenham o mesmo historico.
        series[f"cat:{cat}"] = _diaria(d, fim, inicio=linhas["emissao"].min())

    escolhidos = escolher_skus(linhas, aberta, N_SKUS_GRAMA)
    for _, r in escolhidos.iterrows():
        d = linhas[linhas["produto_cod"] == r["sku"]]
        # SKU comeca na propria 1a venda: dia anterior a existir no catalogo nao e zero de
        # demanda, e ausencia de produto.
        series[f"sku:{r['sku']}"] = _diaria(d, fim)

    meta = {
        "unidade": unidade,
        "fim_da_base": str(fim.date()),
        "corte_de_encomendas": corte,
        "skus_grama": [
            {**r, "nome": nomes.get(r["sku"], "")} for r in escolhidos.to_dict("records")
        ],
    }
    return series, escolhidos, meta


# --------------------------------------------------------------------------- #
# Modelo
# --------------------------------------------------------------------------- #
def _treino(y: pd.Series, origem: pd.Timestamp) -> pd.Series:
    """Dados de treino de uma origem, honrando `JANELA_TREINO`."""
    tr = y[y.index < origem]
    return tr if JANELA_TREINO is None else tr.iloc[-JANELA_TREINO:]


def _z(y: pd.Series, log: bool) -> pd.Series:
    return np.log1p(y.clip(lower=0)) if log else y


def _volta(v: np.ndarray, log: bool) -> np.ndarray:
    """De volta a unidade. Com log1p, `expm1` da a MEDIANA (doc 04 §2)."""
    return np.clip(np.expm1(v) if log else v, 0, None)


def _ajustar(z: pd.Series, X: pd.DataFrame, order, sorder):
    # Com d = 1 a diferenciacao ja tira o nivel: constante viraria tendencia linear.
    return SARIMAX(z, exog=X, order=order, seasonal_order=sorder,
                   trend="c" if order[1] == 0 else "n",
                   enforce_stationarity=False, enforce_invertibility=False
                   ).fit(disp=False, maxiter=MAXITER)


_G: dict = {}


def _init(series, X):
    _G["series"], _G["X"] = series, X


def _aic_de_uma_ordem(args) -> dict | None:
    """Um ponto do grid de AIC, com os dados anteriores a primeira origem."""
    nome, var, p, q, P, Q = args
    cfg = VARIANTES[var]
    y = _G["series"][nome]
    pre = _treino(y, PRIMEIRA_ORIGEM)          # mesma janela que o walk-forward usara
    order, sorder = (p, cfg["d"], q), (P, D_SAZONAL, Q, M)
    try:
        res = _ajustar(_z(pre, cfg["log"]), _G["X"].loc[pre.index], order, sorder)
    except Exception:                          # noqa: BLE001 — ordem que nao converge
        return None
    if not np.isfinite(res.aic):
        return None
    return {"serie": nome, "variante": var, "order": list(order),
            "seasonal_order": list(sorder), "aic": float(res.aic)}


def _rodada(args) -> list[dict]:
    """Um ajuste: treina com tudo antes da origem e preve os 14 dias seguintes."""
    nome, var, origem, order, sorder = args
    cfg = VARIANTES[var]
    y, X = _G["series"][nome], _G["X"]
    origem = pd.Timestamp(origem)
    treino = _treino(y, origem)
    futuro = pd.date_range(origem, periods=HORIZONTE, freq="D")
    try:
        res = _ajustar(_z(treino, cfg["log"]), X.loc[treino.index], tuple(order), tuple(sorder))
        fc = res.get_forecast(HORIZONTE, exog=X.loc[futuro])
        mu = np.asarray(fc.predicted_mean)
        ic = np.asarray(fc.conf_int(alpha=ALPHA))
    except Exception:                          # noqa: BLE001
        return []

    prev, lo, hi = _volta(mu, cfg["log"]), _volta(ic[:, 0], cfg["log"]), _volta(ic[:, 1], cfg["log"])
    ult7 = treino.values[-M:]                  # naive sazonal: repete a ultima semana
    escala = float(np.mean(np.abs(treino.values[M:] - treino.values[:-M])))

    return [{
        "serie": nome, "variante": var, "origem": origem, "data": futuro[h],
        "horizonte": h + 1, "previsto": prev[h], "ic_inf": lo[h], "ic_sup": hi[h],
        "real": float(y.get(futuro[h], np.nan)),
        "naive": float(ult7[h % M]), "escala": escala,
    } for h in range(HORIZONTE)]


# --------------------------------------------------------------------------- #
# Metricas
# --------------------------------------------------------------------------- #
def _bloco(d: pd.DataFrame, janela_completa: bool = True) -> dict:
    """Metricas de um recorte de previsoes de UMA serie e UMA variante."""
    if d.empty:
        return {"n_dias": 0}
    ae = (d["real"] - d["previsto"]).abs()
    ae_n = (d["real"] - d["naive"]).abs()
    dentro = (d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])
    com_escala = d["escala"] > 0
    # Por rodada: soma dos 14 dias previstos (o numero que a loja usaria para o periodo).
    q = d.assign(ae=ae, ae_n=ae_n).groupby("origem").agg(
        prev=("previsto", "sum"), real=("real", "sum"), ae=("ae", "sum"), ae_n=("ae_n", "sum"))
    cob = float(dentro.mean() * 100)
    mase = float((ae[com_escala] / d.loc[com_escala, "escala"]).mean()) if com_escala.any() else np.nan
    b = {
        "n_dias": int(len(d)), "n_rodadas": int(d["origem"].nunique()),
        "mae": round(float(ae.mean()), 2),
        "rmse": round(float(np.sqrt(((d["real"] - d["previsto"]) ** 2).mean())), 2),
        "mase": round(mase, 3),
        "erro_relativo_naive": round(float(ae.sum() / ae_n.sum()), 3) if ae_n.sum() else None,
        "vence_naive_pct": round(float((q["ae"] < q["ae_n"]).mean() * 100), 1),
        "cobertura_ic95_pct": round(cob, 1),
        "largura_ic95": round(float((d["ic_sup"] - d["ic_inf"]).mean()), 2),
        "previsto_sobre_real_pct": round(float(d["previsto"].sum() / d["real"].sum() * 100), 1)
        if d["real"].sum() else None,
        "passa_criterio_diario": bool(np.isfinite(mase) and mase < 1.0 and 90.0 <= cob <= 98.0),
    }
    if janela_completa and q["real"].sum():
        b["erro_total_14d_pct"] = round(float((q["prev"] - q["real"]).abs().sum()
                                              / q["real"].sum() * 100), 1)
    return b


def _blocos(d: pd.DataFrame) -> dict:
    return {
        "geral_todos_horizontes": _bloco(d),
        "operacional_h1": _bloco(d[d["horizonte"] == 1], janela_completa=False),
        "por_horizonte": {int(h): _bloco(g, janela_completa=False)
                          for h, g in d.groupby("horizonte")},
    }


def metricas(prev: pd.DataFrame, fechados: set) -> dict:
    out: dict = {}
    for (serie, var), d in prev.groupby(["serie", "variante"]):
        out.setdefault(serie, {})[var] = {
            "dias_abertos": _blocos(d[~d["data"].isin(fechados)]),
            "todos_os_dias": _blocos(d),
        }
    return out


def tabela(met: dict, ordens: dict, series: dict[str, pd.Series]) -> pd.DataFrame:
    """Uma linha por (serie, variante): AIC + metricas dos dias de loja aberta."""
    linhas = []
    for serie in series:
        y = series[serie]
        pre = y[y.index < PRIMEIRA_ORIGEM]
        for var in VARIANTES:
            o = ordens.get(serie, {}).get(var) or {}
            for recorte, rotulo in (("operacional_h1", "h1"), ("geral_todos_horizontes", "h1_14")):
                b = met.get(serie, {}).get(var, {}).get("dias_abertos", {}).get(recorte, {})
                if not b.get("n_dias"):
                    continue
                linhas.append({
                    "serie": serie, "variante": var, "recorte": rotulo,
                    "dias_pre_origem": len(pre),
                    "zeros_pre_origem_pct": round(float((pre == 0).mean() * 100), 1),
                    "cv_pre_origem": round(float(pre.std() / pre.mean()), 2) if pre.mean() else None,
                    "order": str(tuple(o.get("order", []))),
                    "seasonal_order": str(tuple(o.get("seasonal_order", []))),
                    "aic": round(o["aic"], 1) if o.get("aic") is not None else None,
                    "mae": b["mae"], "mase": b["mase"],
                    "erro_relativo_naive": b["erro_relativo_naive"],
                    "vence_naive_pct": b["vence_naive_pct"],
                    "cobertura_ic95_pct": b["cobertura_ic95_pct"],
                    "largura_ic95": b["largura_ic95"],
                    "previsto_sobre_real_pct": b["previsto_sobre_real_pct"],
                    "passa_criterio_diario": b["passa_criterio_diario"],
                })
    return pd.DataFrame(linhas)


# --------------------------------------------------------------------------- #
# Execucao
# --------------------------------------------------------------------------- #
def origens(series: dict[str, pd.Series]) -> list[pd.Timestamp]:
    """As origens do walk-forward, iguais para todas as series (comparabilidade)."""
    fim = min(y.index.max() for y in series.values())
    return list(pd.date_range(PRIMEIRA_ORIGEM, fim - pd.Timedelta(days=HORIZONTE - 1),
                              freq=f"{PASSO}D"))


def _slug(nome: str) -> str:
    return nome.replace(":", "_").replace(" ", "_").lower()


def _caminhos(slug: str, serie: str | None = None) -> dict[str, str]:
    base = os.path.join(METRICS_DIR, slug)
    if serie is None:
        return {"base": base, "grid_aic": f"{base}_grid_aic.csv",
                "previsoes": f"{base}_previsoes.csv", "operacional": f"{base}_operacional.csv",
                "resumo": f"{base}_resumo.csv", "json": f"{base}.json"}
    p = f"{base}__{_slug(serie)}"
    # Cache de AIC por serie: as 6 series rodam em processos paralelos e reescrever um
    # arquivo unico perderia linhas (cada processo le o arquivo todo e grava o arquivo todo).
    return {"previsoes": f"{p}_previsoes.csv", "ordens": f"{p}_ordens.json",
            "grid_aic": f"{p}_grid_aic.csv"}


def _barra(feitos: int, total: int, t0: float, rotulo: str) -> None:
    dec = time.time() - t0
    resta = dec / feitos * (total - feitos) if feitos else 0
    print(f"  [{rotulo}] {feitos}/{total} · {dec / 60:.1f}min · restam ~{resta / 60:.1f}min",
          flush=True)


def _contexto(unidade: str) -> tuple[dict[str, pd.Series], pd.DataFrame, dict, pd.DataFrame]:
    """Series, exogenas, metadados — montados igual em todo processo (sem aleatoriedade)."""
    series, escolhidos, meta = montar_series(unidade)
    ini = min(y.index.min() for y in series.values())
    fim = max(y.index.max() for y in series.values()) + pd.Timedelta(days=HORIZONTE)
    X = exogenas(unidade, pd.date_range(ini, fim, freq="D"))
    return series, X, meta, escolhidos


# --------------------------------------------------------------------------- #
# Fase 1 — AIC (com cache em disco)
# --------------------------------------------------------------------------- #
def _ler_cache_aic(caminho: str) -> pd.DataFrame:
    if not os.path.exists(caminho):
        return pd.DataFrame(columns=["serie", "variante", "order", "seasonal_order", "aic"])
    d = pd.read_csv(caminho, sep=";", decimal=".")
    for c in ("order", "seasonal_order"):
        d[c] = d[c].map(lambda v: list(ast.literal_eval(v)) if isinstance(v, str) else v)
    return d


def _melhor_ordem(d: pd.DataFrame) -> dict:
    d = d.sort_values("aic")
    m = d.iloc[0]
    return {"order": list(m["order"]), "seasonal_order": list(m["seasonal_order"]),
            "aic": float(m["aic"]), "n_ordens_convergidas": int(len(d)),
            "top5": d.head(5)[["order", "seasonal_order", "aic"]].to_dict("records")}


def grid_aic(slug: str, serie: str, refazer: bool) -> tuple[dict[str, dict], pd.DataFrame]:
    """Ordem por AIC de cada variante da serie. Reaproveita o `_grid_aic.csv` quando cobre."""
    caminho = _caminhos(slug, serie)["grid_aic"]
    cache = _ler_cache_aic(caminho)
    novo = []
    for var in VARIANTES:
        tem = cache[(cache["serie"] == serie) & (cache["variante"] == var)]
        if len(tem) and not refazer:
            print(f"  [fase 1] {serie} {var}: {len(tem)} ordens do cache", flush=True)
            continue
        grade = [(serie, var, p, q, P, Q)
                 for p, q, P, Q in itertools.product(GRID_PQ, GRID_PQ, GRID_SPQ, GRID_SPQ)]
        t0 = time.time()
        for n, args in enumerate(grade, start=1):
            r = _aic_de_uma_ordem(args)
            if r:
                novo.append(r)
            if n == len(grade):
                _barra(n, len(grade), t0, f"fase 1 {var}")
    if novo:
        cache = pd.concat([cache, pd.DataFrame(novo)], ignore_index=True)
        # `order` e `seasonal_order` sao listas (nao hashaveis): a chave do de-duplica vai
        # pela representacao em texto, que e tambem como as colunas vao para o CSV.
        chave = ["serie", "variante", "_order", "_sorder"]
        cache = (cache.assign(_order=cache["order"].map(str), _sorder=cache["seasonal_order"].map(str))
                      .drop_duplicates(chave, keep="last")
                      .drop(columns=["_order", "_sorder"]))
        cache.sort_values(["serie", "variante", "aic"]) \
             .to_csv(caminho, sep=";", index=False, decimal=".")

    d = cache[cache["serie"] == serie]
    ordens = {var: _melhor_ordem(g) for var, g in d.groupby("variante") if len(g)}
    for var in VARIANTES:
        if var not in ordens:
            print(f"  [aviso] nenhuma ordem convergiu para {serie} {var}", flush=True)
            continue
        o = ordens[var]
        print(f"  [ordem] {serie:30s} {var:11s} {tuple(o['order'])}"
              f"{tuple(o['seasonal_order'])} AIC {o['aic']:.1f}", flush=True)
    return ordens, d


# --------------------------------------------------------------------------- #
# Fase 2 — walk-forward de UMA serie (um processo)
# --------------------------------------------------------------------------- #
def executar_serie(slug: str, unidade: str, serie: str, refazer_aic: bool = False) -> str:
    os.makedirs(METRICS_DIR, exist_ok=True)
    series, X, _, _ = _contexto(unidade)
    if serie not in series:
        raise SystemExit(f"serie '{serie}' nao existe. Use --listar-series.")
    _init(series, X)                           # preenche _G neste processo

    y = series[serie]
    lista_origens = origens(series)
    print(f"=== {slug} · {serie} ===", flush=True)
    print(f"  [serie] {y.index.min().date()} -> {y.index.max().date()} · {len(y)} dias · "
          f"{(y == 0).mean() * 100:.1f}% zeros · CV {y.std() / y.mean():.2f}", flush=True)

    ordens, _ = grid_aic(slug, serie, refazer_aic)

    tarefas = [(serie, var, o, ordens[var]["order"], ordens[var]["seasonal_order"])
               for var in VARIANTES if var in ordens for o in lista_origens]
    print(f"  [fase 2] walk-forward: {len(tarefas)} ajustes "
          f"({len(lista_origens)} origens x {len(ordens)} variantes)", flush=True)

    t0, linhas, falhas = time.time(), [], 0
    for n, args in enumerate(tarefas, start=1):
        r = _rodada(args)
        if r:
            linhas.extend(r)
        else:
            falhas += 1
        if n % 100 == 0 or n == len(tarefas):
            _barra(n, len(tarefas), t0, "fase 2")

    saida = _caminhos(slug, serie)
    pd.DataFrame(linhas).to_csv(saida["previsoes"], sep=";", index=False, decimal=".")
    with open(saida["ordens"], "w", encoding="utf-8") as fh:
        json.dump({"serie": serie, "ordens_por_aic": ordens,
                   "ajustes_sem_convergencia": falhas,
                   "n_origens": len(lista_origens)}, fh, ensure_ascii=False, indent=2,
                  default=str)
    print(f"  [ok] {serie}: {len(linhas)} linhas, {falhas} ajuste(s) sem convergencia\n"
          f"  [arquivo] {saida['previsoes']}", flush=True)
    return saida["previsoes"]


# --------------------------------------------------------------------------- #
# Consolidacao
# --------------------------------------------------------------------------- #
def consolidar(slug: str, unidade: str) -> dict:
    series, X, meta, _ = _contexto(unidade)
    lista_origens = origens(series)
    fechados = fechados_da_unidade(unidade)
    cam = _caminhos(slug)

    partes, ordens, falhas, faltando = [], {}, 0, []
    for nome in series:
        p = _caminhos(slug, nome)
        if not (os.path.exists(p["previsoes"]) and os.path.exists(p["ordens"])):
            faltando.append(nome)
            continue
        d = pd.read_csv(p["previsoes"], sep=";", decimal=".",
                        parse_dates=["origem", "data"])
        partes.append(d)
        with open(p["ordens"], encoding="utf-8") as fh:
            j = json.load(fh)
        ordens[nome] = j["ordens_por_aic"]
        falhas += int(j.get("ajustes_sem_convergencia", 0))
    if faltando:
        print(f"[aviso] sem resultado (serie nao rodada ainda): {faltando}", flush=True)
    if not partes:
        raise SystemExit("nenhuma serie rodada — rode --serie antes de --consolidar")

    grids = [_ler_cache_aic(_caminhos(slug, n)["grid_aic"]) for n in ordens]
    grids = [g for g in grids if len(g)]
    if grids:
        pd.concat(grids, ignore_index=True).sort_values(["serie", "variante", "aic"]) \
          .to_csv(cam["grid_aic"], sep=";", index=False, decimal=".")

    prev = pd.concat(partes, ignore_index=True).dropna(subset=["real"])
    prev.to_csv(cam["previsoes"], sep=";", index=False, decimal=".")
    prev[prev["horizonte"] == 1].drop(columns="horizonte").to_csv(
        cam["operacional"], sep=";", index=False, decimal=".")

    met = metricas(prev, fechados)
    rodadas = {k: v for k, v in series.items() if k in ordens}
    tab = tabela(met, ordens, rodadas)
    tab.to_csv(cam["resumo"], sep=";", index=False, decimal=".")

    saida = {
        "slug": slug,
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "config": {
            **meta,
            "alvo": (f"fluxo diario por dia: venda com mais de {LIMIAR_QTD_VENDA} unidades "
                     f"no documento removida (encomenda, Etapa 6 / ADR-013)"),
            "series": {k: {"inicio": str(v.index.min().date()), "fim": str(v.index.max().date()),
                           "dias": len(v), "zeros_pct": round(float((v == 0).mean() * 100), 1),
                           "cv": round(float(v.std() / v.mean()), 2)}
                       for k, v in series.items()},
            "series_sem_resultado": faltando,
            "variantes": VARIANTES,
            "m": M, "D": D_SAZONAL,
            "grid_pq": [min(GRID_PQ), max(GRID_PQ)], "grid_PQ": [min(GRID_SPQ), max(GRID_SPQ)],
            "exogenas": list(X.columns),
            "horizonte_dias": HORIZONTE, "passo_origem_dias": PASSO,
            "primeira_origem": str(PRIMEIRA_ORIGEM.date()), "n_origens": len(lista_origens),
            "janela": "expansiva" if JANELA_TREINO is None else "deslizante",
            "janela_dias": JANELA_TREINO, "alpha_ic": ALPHA,
            "adi_corte_projeto": ADI_CORTE, "min_span_dias_projeto": MIN_SPAN_DIAS,
            "ajustes_sem_convergencia": falhas,
            "nota_aic": ("AIC compara ordens dentro da mesma serie, mesma escala e mesmo d. "
                         "NAO compara as 3 variantes entre si (log1p muda a unidade da "
                         "verossimilhanca; d muda as observacoes efetivas)."),
        },
        "ordens_por_aic": ordens,
        "metricas": met,
        "arquivos": cam,
    }
    with open(cam["json"], "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2, default=str)

    print("\n=== resumo (dias de loja aberta) ===")
    cols = ["serie", "variante", "recorte", "aic", "order", "mase", "erro_relativo_naive",
            "vence_naive_pct", "cobertura_ic95_pct", "largura_ic95", "mae",
            "previsto_sobre_real_pct", "passa_criterio_diario"]
    print(tab[cols].to_string(index=False), flush=True)
    print(f"\n[arquivos] {cam['json']} · {cam['resumo']} · {cam['previsoes']}")
    return saida


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unidade", default="itabirito", choices=sorted(UNIDADES))
    ap.add_argument("--serie", help="roda so esta serie (ex.: 'cat:Grama', 'sku:147')")
    ap.add_argument("--listar-series", action="store_true")
    ap.add_argument("--consolidar", action="store_true")
    ap.add_argument("--refazer-aic", action="store_true", help="ignora o cache do grid de AIC")
    ap.add_argument("--janela", type=int, default=None,
                    help="janela de treino deslizante em dias (omitido = expansiva)")
    ap.add_argument("--variantes", default=None,
                    help="subconjunto de variantes separado por virgula (ex.: 'sem_log|d0')")
    a = ap.parse_args()
    unidade = UNIDADES[a.unidade]
    global JANELA_TREINO, VARIANTES
    JANELA_TREINO = a.janela
    if a.variantes:
        escolhidas = [v.strip() for v in a.variantes.split(",")]
        faltam = [v for v in escolhidas if v not in VARIANTES]
        if faltam:
            ap.error(f"variante(s) desconhecida(s): {faltam}")
        VARIANTES = {v: VARIANTES[v] for v in escolhidas}
    # O slug carrega o alvo e a janela: cache de AIC de outra janela nao serve.
    slug = f"variantes_log_d_fluxo_{a.unidade.replace('-', '_')}"
    if JANELA_TREINO is not None:
        slug += f"_jan{JANELA_TREINO}"

    if a.listar_series:
        series, _, meta = montar_series(unidade)
        for nome, y in series.items():
            print(f"{nome}\t{len(y)} dias\t{(y == 0).mean() * 100:.1f}% zeros\t"
                  f"CV {y.std() / y.mean():.2f}")
        print(json.dumps({"corte_de_encomendas": meta["corte_de_encomendas"],
                          "skus_grama": meta["skus_grama"]}, ensure_ascii=False, indent=2))
    elif a.consolidar:
        consolidar(slug, unidade)
    elif a.serie:
        executar_serie(slug, unidade, a.serie, a.refazer_aic)
    else:
        ap.error("informe --serie, --consolidar ou --listar-series")


if __name__ == "__main__":
    main()
