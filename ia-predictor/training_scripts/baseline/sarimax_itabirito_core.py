"""Nucleo compartilhado dos dois treinos SARIMAX de Itabirito (com e sem `log1p`).

Os dois scripts de treino (`treino_itabirito_sem_log.py` e `treino_itabirito_log1p.py`)
importam este modulo e chamam `executar()` mudando um unico argumento: `usar_log1p`.
Tudo o mais — serie, exogenas, ordem do SARIMAX, protocolo de walk-forward, metricas —
vem daqui, para que a diferenca entre os dois experimentos seja **so** a transformacao.

Protocolo de validacao
----------------------
Walk-forward com janelas **sobrepostas**: a origem anda de 1 em 1 dia e cada ajuste preve
os 14 dias seguintes. Toda data prevista aparece, portanto, em ate 14 janelas, uma por
horizonte h = 1..14.

O horizonte h = 1 e o numero operacional: e a previsao feita com o modelo reajustado no
dia anterior, ou seja, "o melhor ajuste do modelo naquele momento". Os 14 horizontes sao
todos gravados em `*_previsoes.csv`, e `*_operacional.csv` isola a serie de h = 1.

A ordem (p,d,q)(P,D,Q)m e escolhida **uma vez**, por AIC, usando apenas dados anteriores a
primeira origem — depois disso nenhuma decisao olha o futuro. A mesma ordem vale para os
dois experimentos (requisito de "mesmos parametros"); a selecao roda na serie **crua**, e
o modulo tambem reporta, como diagnostico, qual ordem a escala `log1p` teria escolhido.
"""
from __future__ import annotations

import itertools
import json
import os
import time
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

# --------------------------------------------------------------------------- #
# Caminhos
# --------------------------------------------------------------------------- #
_AQUI = os.path.dirname(os.path.abspath(__file__))
_TRAINING_SCRIPTS = os.path.dirname(_AQUI)
OUTPUT_DIR = os.path.join(_TRAINING_SCRIPTS, "output")
METRICS_DIR = os.path.join(_TRAINING_SCRIPTS, "results", "metrics")

BASE_ITABIRITO = os.path.join(OUTPUT_DIR, "BaseTreino_itabirito.csv")
# Etapa 6 (ADR-013): a venda total partida em dois fluxos pelo tamanho da venda.
BASE_FLUXO_DIARIO = os.path.join(OUTPUT_DIR, "BaseTreino_itabirito_sem_encomendas.csv")
BASE_ENCOMENDAS = os.path.join(OUTPUT_DIR, "BaseTreino_itabirito_encomendas.csv")
CALENDARIO = os.path.join(OUTPUT_DIR, "calendario_diario.csv")
UNIDADE = "Itabirito"

# --------------------------------------------------------------------------- #
# Parametros do SARIMAX — IDENTICOS nos dois experimentos
# --------------------------------------------------------------------------- #
M = 7                      # sazonalidade semanal
D_REGULAR = 1              # d = 1: a previsao parte do nivel recente (doc 04)
D_SAZONAL = 0              # D = 0: o ciclo semanal entra pelas dummies de dia da semana
GRID_PQ = range(0, 3)      # p, q em 0..2
GRID_SPQ = range(0, 2)     # P, Q em 0..1
ALPHA = 0.05               # IC de 95%
MAXITER = 200

# Protocolo de walk-forward
HORIZONTE = 14             # dias previstos por janela
PASSO_ORIGEM = 1           # a origem anda 1 dia -> janelas sobrepostas
PRIMEIRA_ORIGEM = pd.Timestamp("2025-03-02")   # ~14 meses de treino antes da 1a origem

# Exogenas: 6 dummies de dia da semana (domingo = base) + calendario da loja
DIAS = ["seg", "ter", "qua", "qui", "sex", "sab"]
COLS_CALENDARIO = ["loja_fechada", "abertura_excepcional"]
COLS_EXOG = [f"dia_{d}" for d in DIAS] + COLS_CALENDARIO


# --------------------------------------------------------------------------- #
# Dados
# --------------------------------------------------------------------------- #
def serie_diaria(caminho: str = BASE_ITABIRITO,
                 calendario: pd.DatetimeIndex | None = None) -> pd.Series:
    """Venda diaria de Itabirito, somada por dia e reindexada no calendario cheio.

    Dia sem venda vira 0 — quase todos sao domingo/feriado, o que a exogena
    `loja_fechada` explica para o modelo. `calendario` permite forcar o mesmo indice de
    outra serie (necessario para somar fluxo diario + encomendas, que tem dias distintos).
    """
    df = pd.read_csv(caminho, sep=";", decimal=".")
    df["emissao"] = pd.to_datetime(df["emissao"])
    s = df.groupby("emissao")["qtdade"].sum().sort_index()
    idx = calendario if calendario is not None else pd.date_range(s.index.min(),
                                                                 s.index.max(), freq="D")
    s = s.reindex(idx, fill_value=0.0).astype(float)
    s.index.name = "data"
    s.name = "qtdade"
    return s


def exogenas(idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Matriz de exogenas para as datas de `idx` (serve passado e futuro)."""
    cal = pd.read_csv(CALENDARIO, sep=";")
    cal = cal[cal["unidade"] == UNIDADE].copy()
    cal["data"] = pd.to_datetime(cal["data"])
    cal = cal.set_index("data")[COLS_CALENDARIO].astype(float)

    faltando = idx.difference(cal.index)
    if len(faltando):
        raise ValueError(f"calendario nao cobre {len(faltando)} data(s), ex.: {faltando[0].date()}")

    X = pd.DataFrame(index=idx)
    for i, nome in enumerate(DIAS):          # 0=seg .. 5=sab; domingo (6) e a base
        X[f"dia_{nome}"] = (idx.weekday == i).astype(float)
    X[COLS_CALENDARIO] = cal.reindex(idx)[COLS_CALENDARIO]
    return X[COLS_EXOG]


# --------------------------------------------------------------------------- #
# Transformacao — o unico ponto em que os dois experimentos diferem
# --------------------------------------------------------------------------- #
def transformar(y: pd.Series, usar_log1p: bool) -> pd.Series:
    return np.log1p(y.clip(lower=0)) if usar_log1p else y


def destransformar(v: np.ndarray, usar_log1p: bool) -> np.ndarray:
    """Volta para unidades. Com log1p, `expm1` da a MEDIANA (nao a media)."""
    return np.expm1(v) if usar_log1p else v


# --------------------------------------------------------------------------- #
# Ajuste e selecao de ordem
# --------------------------------------------------------------------------- #
def ajustar(z: pd.Series, X: pd.DataFrame, order, seasonal_order):
    # Com d = 1 a diferenciacao ja remove o nivel: constante viraria tendencia linear.
    modelo = SARIMAX(z, exog=X, order=order, seasonal_order=seasonal_order,
                     trend="c" if order[1] == 0 else "n",
                     enforce_stationarity=False, enforce_invertibility=False)
    return modelo.fit(disp=False, maxiter=MAXITER)


def selecionar_ordem(z: pd.Series, X: pd.DataFrame) -> dict:
    """Melhor (p,d,q)(P,D,Q)m por AIC no grid, com d e D fixos."""
    melhor, avaliados = None, []
    for p, q, P, Q in itertools.product(GRID_PQ, GRID_PQ, GRID_SPQ, GRID_SPQ):
        order = (p, D_REGULAR, q)
        sorder = (P, D_SAZONAL, Q, M)
        try:
            res = ajustar(z, X, order, sorder)
        except Exception:                      # noqa: BLE001 — ordem que nao converge
            continue
        if not np.isfinite(res.aic):
            continue
        avaliados.append({"order": order, "seasonal_order": sorder, "aic": float(res.aic)})
        if melhor is None or res.aic < melhor["aic"]:
            melhor = avaliados[-1]
    if melhor is None:
        raise RuntimeError("nenhuma ordem convergiu na selecao")
    melhor["avaliados"] = sorted(avaliados, key=lambda d: d["aic"])[:5]
    return melhor


# --------------------------------------------------------------------------- #
# Walk-forward
# --------------------------------------------------------------------------- #
def origens(y: pd.Series) -> list[pd.Timestamp]:
    """Origens possiveis: precisam de HORIZONTE dias de realizado a frente."""
    ultima = y.index.max() - pd.Timedelta(days=HORIZONTE - 1)
    return list(pd.date_range(PRIMEIRA_ORIGEM, ultima, freq=f"{PASSO_ORIGEM}D"))


def walk_forward(y: pd.Series, X: pd.DataFrame, ordem: dict, usar_log1p: bool,
                 verbose: bool = True) -> pd.DataFrame:
    """Uma linha por (origem, data prevista). Reajusta o modelo em cada origem."""
    linhas, falhas = [], 0
    lista_origens = origens(y)
    t0 = time.time()

    for n, origem in enumerate(lista_origens, start=1):
        treino = y[y.index < origem]
        futuro = pd.date_range(origem, periods=HORIZONTE, freq="D")
        z = transformar(treino, usar_log1p)

        try:
            res = ajustar(z, X.loc[treino.index], ordem["order"], ordem["seasonal_order"])
            fc = res.get_forecast(HORIZONTE, exog=X.loc[futuro])
            mu = np.asarray(fc.predicted_mean)
            ic = np.asarray(fc.conf_int(alpha=ALPHA))
        except Exception:                      # noqa: BLE001
            falhas += 1
            continue

        prev = np.clip(destransformar(mu, usar_log1p), 0, None)
        lo = np.clip(destransformar(ic[:, 0], usar_log1p), 0, None)
        hi = np.clip(destransformar(ic[:, 1], usar_log1p), 0, None)

        # Naive sazonal da janela: repete os ultimos 7 dias observados em ciclo.
        ultimos7 = treino.values[-M:]
        naive = np.array([ultimos7[i % M] for i in range(HORIZONTE)])
        # Escala do MASE: erro da naive sazonal DENTRO do treino desta origem.
        escala = float(np.mean(np.abs(treino.values[M:] - treino.values[:-M])))

        for h in range(HORIZONTE):
            data = futuro[h]
            linhas.append({
                "origem": origem, "data": data, "horizonte": h + 1,
                "previsto": prev[h], "ic_inf": lo[h], "ic_sup": hi[h],
                "real": float(y.get(data, np.nan)),
                "naive": naive[h], "escala_mase": escala,
            })

        if verbose and (n % 25 == 0 or n == len(lista_origens)):
            dec = time.time() - t0
            print(f"  [{n}/{len(lista_origens)}] origem {origem.date()} "
                  f"· {dec:.0f}s · {dec / n:.2f}s/ajuste", flush=True)

    if falhas and verbose:
        print(f"  [aviso] {falhas} origem(ns) sem convergencia, puladas")
    return pd.DataFrame(linhas)


# --------------------------------------------------------------------------- #
# Metricas
# --------------------------------------------------------------------------- #
def _bloco(d: pd.DataFrame) -> dict:
    erro = (d["real"] - d["previsto"]).abs()
    erro_naive = (d["real"] - d["naive"]).abs()
    dentro = (d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])
    return {
        "n": int(len(d)),
        "mae": float(erro.mean()),
        "rmse": float(np.sqrt(((d["real"] - d["previsto"]) ** 2).mean())),
        "mase": float((erro / d["escala_mase"]).mean()),
        "mae_relativo_naive": float(erro.sum() / erro_naive.sum()) if erro_naive.sum() else np.nan,
        "cobertura_ic95_pct": float(dentro.mean() * 100),
        "largura_ic95": float((d["ic_sup"] - d["ic_inf"]).mean()),
        "vies_previsto_sobre_real_pct": float(d["previsto"].sum() / d["real"].sum() * 100)
        if d["real"].sum() else np.nan,
    }


def metricas(prev: pd.DataFrame) -> dict:
    d = prev.dropna(subset=["real"])
    return {
        "geral_todos_horizontes": _bloco(d),
        "operacional_h1": _bloco(d[d["horizonte"] == 1]),
        "por_horizonte": {int(h): _bloco(g) for h, g in d.groupby("horizonte")},
    }


# --------------------------------------------------------------------------- #
# Execucao
# --------------------------------------------------------------------------- #
def executar(nome: str, usar_log1p: bool, base_csv: str = BASE_ITABIRITO,
             encomendas_csv: str | None = None) -> dict:
    """Roda um experimento completo.

    `base_csv` e o alvo do SARIMAX: a venda total (padrao) ou so o fluxo diario, quando as
    encomendas foram separadas pela Etapa 6 (ADR-013).

    `encomendas_csv`, quando dado, acrescenta um bloco extra de metricas: a previsao do
    fluxo **somada as encomendas realmente ocorridas no dia**, avaliada contra a venda
    total. Isso mede o entregavel de verdade no cenario que a separacao pressupoe — a loja
    conhece a encomenda com antecedencia, porque ela mesma a encomendou do fornecedor. Sem
    esse bloco, os experimentos com e sem separacao nao seriam comparaveis: prevem series
    diferentes.
    """
    os.makedirs(METRICS_DIR, exist_ok=True)
    print(f"=== {nome} === (log1p={usar_log1p})", flush=True)

    y = serie_diaria(base_csv)
    X = exogenas(pd.date_range(y.index.min(), y.index.max() + pd.Timedelta(days=HORIZONTE),
                               freq="D"))
    lista_origens = origens(y)
    print(f"[serie] {y.index.min().date()} -> {y.index.max().date()} · {len(y)} dias · "
          f"CV {y.std() / y.mean():.2f}", flush=True)
    print(f"[walk-forward] {len(lista_origens)} origens ({lista_origens[0].date()} -> "
          f"{lista_origens[-1].date()}) · h={HORIZONTE} · passo={PASSO_ORIGEM}d", flush=True)

    # Selecao de ordem: so com dados anteriores a 1a origem (sem vazamento).
    pre = y[y.index < PRIMEIRA_ORIGEM]
    t0 = time.time()
    ordem = selecionar_ordem(transformar(pre, False), X.loc[pre.index])   # sempre na serie crua
    ordem_log = selecionar_ordem(transformar(pre, True), X.loc[pre.index])  # so diagnostico
    print(f"[ordem] escolhida na serie crua: {ordem['order']}{ordem['seasonal_order']} "
          f"AIC {ordem['aic']:.1f} ({time.time() - t0:.0f}s)", flush=True)
    print(f"[ordem] (diagnostico) a escala log1p teria escolhido "
          f"{ordem_log['order']}{ordem_log['seasonal_order']}", flush=True)

    prev = walk_forward(y, X, ordem, usar_log1p)
    met = metricas(prev)

    # Bloco extra: previsao do fluxo + encomendas conhecidas, contra a venda total.
    if encomendas_csv:
        enc = serie_diaria(encomendas_csv, calendario=y.index)
        total = y + enc
        soma = prev.copy()
        acrescimo = soma["data"].map(enc)
        for col in ("previsto", "ic_inf", "ic_sup"):
            soma[col] = soma[col] + acrescimo
        soma["real"] = soma["data"].map(total)
        # A naive e a escala do MASE passam a ser as do total, para bater com o novo alvo.
        naive_por_origem, escala_por_origem = {}, {}
        for origem in prev["origem"].unique():
            tr = total[total.index < origem]
            ult7 = tr.values[-M:]
            naive_por_origem[origem] = {h: ult7[(h - 1) % M] for h in range(1, HORIZONTE + 1)}
            escala_por_origem[origem] = float(np.mean(np.abs(tr.values[M:] - tr.values[:-M])))
        soma["naive"] = [naive_por_origem[o][h] for o, h in zip(soma["origem"], soma["horizonte"])]
        soma["escala_mase"] = soma["origem"].map(escala_por_origem)
        met["total_com_encomendas_conhecidas"] = {
            "geral_todos_horizontes": _bloco(soma.dropna(subset=["real"])),
            "operacional_h1": _bloco(soma[(soma["horizonte"] == 1)].dropna(subset=["real"])),
        }
        soma.to_csv(os.path.join(METRICS_DIR, f"{nome}_total_com_encomendas.csv"),
                    sep=";", index=False, decimal=".")

    csv_prev = os.path.join(METRICS_DIR, f"{nome}_previsoes.csv")
    prev.to_csv(csv_prev, sep=";", index=False, decimal=".")
    oper = prev[prev["horizonte"] == 1][["data", "origem", "previsto", "ic_inf", "ic_sup", "real"]]
    csv_oper = os.path.join(METRICS_DIR, f"{nome}_operacional.csv")
    oper.to_csv(csv_oper, sep=";", index=False, decimal=".")

    saida = {
        "nome": nome,
        "usar_log1p": usar_log1p,
        "unidade": UNIDADE,
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "config": {
            "base_csv": base_csv,
            "encomendas_separadas": bool(encomendas_csv),
            "encomendas_csv": encomendas_csv,
            "m": M, "d": D_REGULAR, "D": D_SAZONAL,
            "grid_pq": [min(GRID_PQ), max(GRID_PQ)], "grid_PQ": [min(GRID_SPQ), max(GRID_SPQ)],
            "horizonte_dias": HORIZONTE, "passo_origem_dias": PASSO_ORIGEM,
            "primeira_origem": str(PRIMEIRA_ORIGEM.date()),
            "n_origens": len(lista_origens),
            "exogenas": COLS_EXOG,
            "alpha_ic": ALPHA,
            "ordem_usada": {"order": list(ordem["order"]),
                            "seasonal_order": list(ordem["seasonal_order"]),
                            "aic_na_serie_crua": ordem["aic"],
                            "selecionada_em": "serie crua, dados < primeira_origem"},
            "ordem_que_log1p_escolheria": {"order": list(ordem_log["order"]),
                                           "seasonal_order": list(ordem_log["seasonal_order"]),
                                           "aic": ordem_log["aic"]},
        },
        "metricas": met,
        "arquivos": {"previsoes": csv_prev, "operacional": csv_oper},
    }
    with open(os.path.join(METRICS_DIR, f"{nome}.json"), "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2)

    g, h1 = met["geral_todos_horizontes"], met["operacional_h1"]
    print(f"[resultado] todos os horizontes: MAE {g['mae']:.0f} · MASE {g['mase']:.3f} · "
          f"vs naive {g['mae_relativo_naive']:.3f} · IC95 {g['cobertura_ic95_pct']:.1f}%", flush=True)
    print(f"[resultado] operacional (h=1):   MAE {h1['mae']:.0f} · MASE {h1['mase']:.3f} · "
          f"vs naive {h1['mae_relativo_naive']:.3f} · IC95 {h1['cobertura_ic95_pct']:.1f}%", flush=True)
    if "total_com_encomendas_conhecidas" in met:
        t = met["total_com_encomendas_conhecidas"]["operacional_h1"]
        print(f"[resultado] fluxo + encomendas conhecidas, contra a venda TOTAL (h=1): "
              f"MAE {t['mae']:.0f} · MASE {t['mase']:.3f} · vs naive "
              f"{t['mae_relativo_naive']:.3f} · IC95 {t['cobertura_ic95_pct']:.1f}%", flush=True)
    print(f"[arquivos] {csv_prev}\n[arquivos] {csv_oper}", flush=True)
    return saida
