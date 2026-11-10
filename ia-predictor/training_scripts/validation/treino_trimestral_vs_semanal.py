"""Treino toda semana × treino a cada 3 meses: quanto erra a previsão de um modelo velho.

Pergunta
--------
Se o sistema previsse 3 meses (91 dias) e a loja treinasse só a cada 3 meses, quanto pioraria
em relação a treinar toda semana (a planilha chega toda semana) e usar só os 7 primeiros dias
de cada previsão?

Protocolo
---------
Receita de produção (`ConfigTreino()`, ADR-017/018/019): em cada treino, ordem por AIC na
janela de 365 dias antes da 1ª origem do walk-forward, ajuste final nos últimos 365 dias até o
corte, previsão com o fator das datas comemorativas calculado só com a venda até o corte. O
walk-forward não roda: ele só dá o status e não muda a previsão
(`holdout_vs_walk_forward.py`).

Ano de teste: 02/03/2025 a 28/02/2026. Treinos a cada 7 dias, de 01/03/2025 a 21/02/2026 (52);
cada um prevê até 91 dias (ou até 28/02/2026). Daí saem:
  - **semanal**: cada dia previsto pelo treino mais recente antes dele (h = 1..7);
  - **trimestral**: cada dia previsto pelo treino de 01/03, 31/05, 30/08 ou 29/11/2025
    (a cada 91 = 13 × 7 dias, h = 1..91);
  - **idade do modelo**: o erro de cada dia previsto por todos os treinos que o alcançam, por
    h = 1..91 (curva do erro pela idade).
Métricas nos dias de loja aberta.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.validation.treino_trimestral_vs_semanal --rodar --workers 16
    python -m training_scripts.validation.treino_trimestral_vs_semanal --consolidar
Saída: `training_scripts/results/metrics/treino_trimestral_vs_semanal/`.
"""
from __future__ import annotations

import argparse
import glob
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

from backend.domain.models.forecaster import ajustar, prever
from backend.domain.models.order_selection import NenhumaOrdemConvergiu, selecionar_ordem
from backend.domain.models.trainer import ConfigTreino, _ajustes_datas, _janela, motivo_inelegivel, origens_walk_forward

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA_DIR = os.path.join(_RAIZ, "results", "metrics", "treino_trimestral_vs_semanal")

H = 91
PRIMEIRO_CORTE = pd.Timestamp("2025-03-01")
FIM_TESTE = pd.Timestamp("2026-02-28")
PASSO_SEMANAL, PASSO_TRIMESTRAL = 7, 91
# as 4 categorias das 2 lojas e o produto de grama mais vendido de cada loja (as séries mais
# lentas primeiro: o pool termina mais cedo)
SERIES = [
    "jardim-canada:category:flores-de-corte", "jardim-canada:category:produtos-de-jardim",
    "itabirito:category:flores-de-corte", "itabirito:category:produtos-de-jardim",
    "jardim-canada:category:plantas-diversas", "itabirito:category:plantas-diversas",
    "jardim-canada:category:grama", "itabirito:category:grama",
    "jardim-canada:product:147", "itabirito:product:00013475",
]


def _nome(chave: str, corte: pd.Timestamp) -> str:
    return f"{chave.replace(':', '_')}_{corte:%Y%m%d}"


def rodar_caso(args) -> str:
    chave, nivel, y, X, aberta, com_fator, com_queda, corte = args
    cfg = ConfigTreino()
    nome = _nome(chave, corte)
    y_c = y[y.index <= corte]
    if motivo_inelegivel(y_c, cfg, nivel):
        open(os.path.join(SAIDA_DIR, nome + ".pulado"), "w").close()
        return nome + " (pulado)"
    pre = _janela(y_c, origens_walk_forward(corte, cfg)[0], cfg.janela_dias)
    try:
        esc = selecionar_ordem(pre, X.loc[pre.index], d=cfg.d, D=cfg.D, m=cfg.m, grade_pq=cfg.grade_pq,
                               grade_PQ=cfg.grade_PQ, maxiter=cfg.maxiter)
    except NenhumaOrdemConvergiu:
        open(os.path.join(SAIDA_DIR, nome + ".pulado"), "w").close()
        return nome + " (nenhuma ordem)"
    janela = y_c.iloc[-cfg.janela_dias:]
    dias = pd.date_range(corte + pd.Timedelta(days=1), min(corte + pd.Timedelta(days=H), FIM_TESTE), freq="D")
    res = ajustar(janela, X.loc[janela.index], esc.ordem, esc.ordem_sazonal, cfg.maxiter)
    prev, inf, sup = prever(res, X.loc[dias], cfg.alpha)
    fator, _ = _ajustes_datas(y_c, X, dias[0], dias, cfg, com_fator, com_queda)
    naive = np.array([janela.values[-cfg.m:][i % cfg.m] for i in range(len(dias))])
    pd.DataFrame({"serie": chave, "corte": corte, "data": dias, "h": np.arange(1, len(dias) + 1),
                  "ordem": str((esc.ordem, esc.ordem_sazonal)), "real": y.loc[dias].values,
                  "previsto": prev * fator, "ic_inf": inf * fator, "ic_sup": sup * fator, "naive": naive,
                  "aberta": aberta.loc[dias].values}).to_csv(os.path.join(SAIDA_DIR, nome + ".csv"), index=False, sep=";")
    return nome


def rodar(workers: int) -> None:
    from training_scripts.validation.holdout_vs_walk_forward import carregar_series
    os.makedirs(SAIDA_DIR, exist_ok=True)
    series = carregar_series()
    cortes = list(pd.date_range(PRIMEIRO_CORTE, FIM_TESTE - pd.Timedelta(days=PASSO_SEMANAL), freq=f"{PASSO_SEMANAL}D"))
    tarefas = [(k, series[k].nivel, series[k].y, series[k].X, series[k].aberta, series[k].com_fator,
                series[k].com_queda, c) for k in SERIES for c in cortes
               if not glob.glob(os.path.join(SAIDA_DIR, _nome(k, c) + ".*"))]
    print(f"{len(cortes)} treinos por série ({cortes[0]:%d/%m/%Y} a {cortes[-1]:%d/%m/%Y}), "
          f"{len(tarefas)} tarefas em {workers} processos", flush=True)
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"
    t = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, f in enumerate(as_completed([pool.submit(rodar_caso, a) for a in tarefas]), 1):
            print(f"[{i}/{len(tarefas)}] {f.result()}  {time.time() - t:.0f}s", flush=True)


def _met(d: pd.DataFrame) -> dict:
    e, en = (d["real"] - d["previsto"]).abs(), (d["real"] - d["naive"]).abs()
    return {"dias": len(d), "mae": e.mean(), "erro_rel_naive": e.sum() / en.sum() if en.sum() else np.nan,
            "cobertura_ic95": ((d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])).mean() * 100,
            "previsto_sobre_real": d["previsto"].sum() / d["real"].sum() * 100}


def consolidar() -> None:
    pd.set_option("display.width", 220)
    pts = pd.concat([pd.read_csv(f, sep=";", parse_dates=["corte", "data"]) for f in glob.glob(os.path.join(SAIDA_DIR, "*_2*.csv"))])
    pts = pts[pts["aberta"].astype(bool)]
    cortes_tri = pd.date_range(PRIMEIRO_CORTE, FIM_TESTE, freq=f"{PASSO_TRIMESTRAL}D")
    sem = pts[pts["h"] <= PASSO_SEMANAL].assign(rotina="semanal")
    tri = pts[pts["corte"].isin(cortes_tri) & (pts["h"] <= PASSO_TRIMESTRAL)].assign(rotina="trimestral")
    # só os dias que as duas rotinas preveem (série que entrou tarde fica só com o que tem nas duas)
    chave = ["serie", "data"]
    comuns = sem[chave].merge(tri[chave])
    sem, tri = sem.merge(comuns), tri.merge(comuns)
    linhas = []
    for serie in sorted(pts["serie"].unique()):
        s, t = sem[sem["serie"] == serie], tri[tri["serie"] == serie]
        ms, mt = _met(s), _met(t)
        linhas.append({"serie": serie, "dias": ms["dias"], "mae_semanal": ms["mae"], "mae_trimestral": mt["mae"],
                       "piora_pct": (mt["mae"] / ms["mae"] - 1) * 100,
                       "rel_naive_semanal": ms["erro_rel_naive"], "rel_naive_trimestral": mt["erro_rel_naive"],
                       "cob_semanal": ms["cobertura_ic95"], "cob_trimestral": mt["cobertura_ic95"],
                       "prev_real_semanal": ms["previsto_sobre_real"], "prev_real_trimestral": mt["previsto_sobre_real"]})
    res = pd.DataFrame(linhas).round(2)
    res.to_csv(os.path.join(SAIDA_DIR, "resumo_rotinas.csv"), index=False, sep=";")
    print(res.to_string(index=False))

    # piora da trimestral por mês do treino: o 1º, 2º e 3º mês depois do treino
    tri["mes_apos_treino"] = (tri["h"] - 1) // 30 + 1
    j = tri.merge(sem[chave + ["previsto"]], on=chave, suffixes=("", "_sem"))
    j["ae_tri"], j["ae_sem"] = (j["real"] - j["previsto"]).abs(), (j["real"] - j["previsto_sem"]).abs()
    por_mes = j.groupby(["serie", "mes_apos_treino"]).apply(lambda g: (g["ae_tri"].sum() / g["ae_sem"].sum() - 1) * 100,
                                                          include_groups=False).unstack().round(1)
    por_mes.to_csv(os.path.join(SAIDA_DIR, "resumo_piora_por_mes_apos_treino.csv"), sep=";")
    print("\npiora da trimestral sobre a semanal (%), pelo mês depois do treino:\n", por_mes)
    por_trim = j.groupby(["serie", "corte"]).apply(lambda g: (g["ae_tri"].sum() / g["ae_sem"].sum() - 1) * 100,
                                                  include_groups=False).unstack().round(1)
    por_trim.to_csv(os.path.join(SAIDA_DIR, "resumo_piora_por_trimestre.csv"), sep=";")
    print("\npiora por trimestre (treino em):\n", por_trim)

    # erro pela idade do modelo: todos os treinos semanais, por faixa de h, só nos dias a partir
    # de 91 dias depois do 1º treino — cada um desses dias é previsto em todas as faixas (um
    # treino por semana de idade), então as faixas comparam os mesmos dias
    idade = pts[pts["data"] > PRIMEIRO_CORTE + pd.Timedelta(days=H)].copy()
    idade["faixa_h"] = pd.cut(idade["h"], [0, 7, 14, 28, 42, 56, 70, 91],
                              labels=["1-7", "8-14", "15-28", "29-42", "43-56", "57-70", "71-91"])
    idade["ae"] = (idade["real"] - idade["previsto"]).abs()
    curva = idade.groupby(["serie", "faixa_h"], observed=True)["ae"].mean().unstack()
    curva = (curva.div(curva["1-7"], axis=0) * 100).round(1)
    curva.to_csv(os.path.join(SAIDA_DIR, "resumo_erro_por_idade.csv"), sep=";")
    print("\nerro médio por idade do modelo (h 1-7 = 100):\n", curva)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rodar", action="store_true")
    ap.add_argument("--consolidar", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    if a.rodar:
        rodar(a.workers)
    if a.consolidar:
        consolidar()


if __name__ == "__main__":
    main()
