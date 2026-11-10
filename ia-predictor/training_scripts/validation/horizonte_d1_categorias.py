"""Previsão longa com d = 1 (ADR-020): o erro e a faixa de 95% pela distância do treino, d = 0 × d = 1.

O doc 09 §3.1 mediu a curva do erro pela distância do treino (1 a 16 semanas) só com d = 0. Com
d = 1 a previsão não volta à média do ano: fica no nível recente, e a faixa de 95% abre com o
horizonte. Este script mede as duas coisas, para o ADR-021 (previsão de 91 dias na tela).

Base: os 52 treinos semanais de `variantes_nivel_sazonal.py` (variante `d1`, cortes de 01/03/2025 a
21/02/2026), nas 8 categorias. Cada treino é refeito com a ordem que ele escolheu e prevê até 118
dias, como `horizonte_e_retreino_categorias.py --estender` fez para d = 0 (`previsoes_longas/`).
Mesmos dias-alvo para todas as distâncias (28/06/2025 a 28/02/2026, loja aberta), como no doc 09.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.validation.horizonte_d1_categorias --estender --workers 4
    python -m training_scripts.validation.horizonte_d1_categorias --consolidar
"""
from __future__ import annotations

import argparse
import glob
import os
import time
from ast import literal_eval
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace

import numpy as np
import pandas as pd

from backend.domain.models.trainer import ConfigTreino

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIANTES_DIR = os.path.join(_RAIZ, "results", "metrics", "variantes_nivel_sazonal")
D0_DIR = os.path.join(_RAIZ, "results", "metrics", "horizonte_e_retreino_categorias", "previsoes_longas")
SAIDA = os.path.join(_RAIZ, "results", "metrics", "horizonte_d1_categorias")
H_LONGO = 118
ALVO = (pd.Timestamp("2025-06-28"), pd.Timestamp("2026-02-28"))
SEMANAS = range(1, 17)


def estender(args) -> str:
    from backend.domain.models.forecaster import ajustar, prever
    from backend.domain.models.trainer import _ajustes_datas
    chave, y, X, aberta, com_fator, com_queda, corte, ordem = args
    cfg = replace(ConfigTreino(), d=1)
    o, os_ = literal_eval(ordem)
    y_c = y[y.index <= corte]
    janela = y_c.iloc[-cfg.janela_dias:]
    dias = pd.date_range(corte + pd.Timedelta(days=1), min(corte + pd.Timedelta(days=H_LONGO), y.index.max()))
    res = ajustar(janela, X.loc[janela.index], o, os_, cfg.maxiter)
    prev, inf, sup = prever(res, X.loc[dias], cfg.alpha)
    fator, _ = _ajustes_datas(y_c, X, dias[0], dias, cfg, com_fator, com_queda)
    nome = f"{chave.replace(':', '_')}_{corte:%Y%m%d}"
    pd.DataFrame({"serie": chave, "corte": corte, "data": dias, "h": np.arange(1, len(dias) + 1), "ordem": ordem,
                  "real": y.loc[dias].values, "previsto": prev * fator, "ic_inf": inf * fator, "ic_sup": sup * fator,
                  "aberta": aberta.loc[dias].values}).to_csv(os.path.join(SAIDA, nome + ".csv"), index=False, sep=";")
    return nome


def rodar_estender(workers: int) -> None:
    from training_scripts.validation.holdout_vs_walk_forward import carregar_series
    os.makedirs(SAIDA, exist_ok=True)
    series = carregar_series()
    tarefas = []
    for arq in sorted(glob.glob(os.path.join(VARIANTES_DIR, "d1_*_category_*_2*.csv"))):
        p = pd.read_csv(arq, sep=";", nrows=1, parse_dates=["corte"])
        s = series[p["serie"].iloc[0]]
        nome = f"{s.chave.replace(':', '_')}_{p['corte'].iloc[0]:%Y%m%d}.csv"
        if not os.path.exists(os.path.join(SAIDA, nome)):
            tarefas.append((s.chave, s.y, s.X, s.aberta, s.com_fator, s.com_queda, p["corte"].iloc[0], p["ordem"].iloc[0]))
    print(f"{len(tarefas)} treinos d = 1 a estender até h = {H_LONGO}", flush=True)
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"
    t = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, f in enumerate(as_completed([pool.submit(estender, a) for a in tarefas]), 1):
            if i % 50 == 0:
                print(f"[{i}/{len(tarefas)}] {f.result()} {time.time() - t:.0f}s", flush=True)


def _ler(pasta: str, variante: str) -> pd.DataFrame:
    d = pd.concat(pd.read_csv(f, sep=";", parse_dates=["corte", "data"]) for f in glob.glob(os.path.join(pasta, "*_2*.csv")))
    d = d[d["aberta"].astype(bool) & d["data"].between(*ALVO)]
    d = d.assign(variante=variante, semana=(d["h"] - 1) // 7 + 1)
    return d[d["semana"].isin(SEMANAS)]


def consolidar() -> None:
    d0, d1 = _ler(D0_DIR, "d0"), _ler(SAIDA, "d1")
    d0 = d0[d0["corte"].isin(d1["corte"].unique())]
    chave = ["serie", "corte", "data"]
    comuns = d0[chave].merge(d1[chave], on=chave)
    pts = pd.concat([d0, d1]).merge(comuns, on=chave)
    # só os dias-alvo que todas as semanas e as 2 variantes cobrem, série a série
    n = pts.groupby(["serie", "data"])[["semana", "variante"]].nunique()
    completos = n[(n["semana"] == len(SEMANAS)) & (n["variante"] == 2)].index
    pts = pts.set_index(["serie", "data"]).loc[completos].reset_index()
    flores = pts["serie"].str.contains("flores")
    # receita do ADR-020: d = 1 menos Flores de corte
    receita = pd.concat([pts[(pts["variante"] == "d1") & ~flores], pts[(pts["variante"] == "d0") & flores]]).assign(variante="adr020")
    pts = pd.concat([pts, receita])
    pts = pts.assign(ae=(pts["real"] - pts["previsto"]).abs(),
                     dentro=((pts["real"] >= pts["ic_inf"]) & (pts["real"] <= pts["ic_sup"])).astype(float),
                     largura=pts["ic_sup"] - pts["ic_inf"])
    base = pts[(pts["variante"] == "d0") & (pts["semana"] == 1)]["ae"].sum()
    tab = pts.groupby(["variante", "semana"]).agg(ae=("ae", "sum"), cobertura=("dentro", "mean"), largura=("largura", "mean"),
                                                 prev=("previsto", "sum"), real=("real", "sum"))
    tab["erro_idx"] = tab["ae"] / base * 100
    tab["prev_real"] = tab["prev"] / tab["real"] * 100
    tab["cobertura"] *= 100
    os.makedirs(SAIDA, exist_ok=True)
    tab.round(2).to_csv(os.path.join(SAIDA, "curva_por_semana.csv"), sep=";")
    por_serie = pts[pts["variante"].isin(["d0", "d1"])].groupby(["serie", "variante", "semana"]).agg(
        ae=("ae", "sum"), cobertura=("dentro", "mean"))
    b = por_serie.xs(("d0", 1), level=("variante", "semana"))["ae"]
    por_serie["erro_idx"] = por_serie["ae"] / por_serie.index.get_level_values("serie").map(b).values * 100
    por_serie.round(3).to_csv(os.path.join(SAIDA, "curva_por_serie.csv"), sep=";")
    pd.set_option("display.width", 250)
    print(f"dias-alvo por série: {pts.groupby('serie')['data'].nunique().to_dict()}")
    print("\nerro diário (soma das 8 séries; d = 0 na 1ª semana = 100):")
    print(tab["erro_idx"].unstack("variante").round(1).to_string())
    print("\ncobertura do IC 95% (%):")
    print(tab["cobertura"].unstack("variante").round(1).to_string())
    print("\nlargura média do IC 95% (un.):")
    print(tab["largura"].unstack("variante").round(0).to_string())
    print("\nprevisto ÷ vendido (%):")
    print(tab["prev_real"].unstack("variante").round(1).to_string())
    print("\npor série, erro (d = 0 na 1ª semana da série = 100):")
    print(por_serie["erro_idx"].unstack("semana")[[1, 2, 4, 8, 13, 16]].round(0).to_string())
    print("\npor série, cobertura (%):")
    print((por_serie["cobertura"] * 100).unstack("semana")[[1, 2, 4, 8, 13, 16]].round(0).to_string())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--estender", action="store_true")
    ap.add_argument("--consolidar", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if a.estender:
        rodar_estender(a.workers)
    if a.consolidar:
        consolidar()


if __name__ == "__main__":
    main()
