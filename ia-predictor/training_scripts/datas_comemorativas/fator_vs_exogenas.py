"""Datas comemorativas: fator multiplicativo (ADR-019) × exógenas de data dentro do SARIMAX.

Pergunta
--------
O sistema prevê a semana das datas comemorativas com o SARIMAX (dia da semana, `loja_fechada`,
`abertura_excepcional`) e multiplica o resultado pelo fator do ADR-019: alta em Flores de
corte, queda de fim de ano e do Dia do Trabalho nas outras categorias. Faz sentido tirar o
fator e pôr as datas como exógenas no próprio SARIMAX?

Variantes (receita de produção, `ConfigTreino()`; só muda o tratamento das datas)
--------------------------------------------------------------------------------
  prd          o sistema: 8 exógenas de calendário + fator (alta em Flores, queda nas outras)
  sem          8 exógenas de calendário, sem fator nem exógena de data (referência)
  exog_evento  8 exógenas + 1 dummy por data (Mulher, Mães, Namorados, Natal, Ano Novo,
               Dia do Trabalho), sem fator
  exog_grupo   8 exógenas + 1 dummy para as 4 datas de presente juntas (Mulher, Mães,
               Namorados, Natal: 4 ocorrências por janela de 365 dias) + Ano Novo + Dia do
               Trabalho, sem fator

As dummies valem 1 nos mesmos dias em que o fator entra (`datas_comemorativas.dias_da_janela`:
de 6 dias antes até a data, loja aberta, sem abertura excepcional). Todas as dummies entram em
todas as séries: o coeficiente de cada série decide o sentido. Dummy sem nenhum 1 na janela
de treino sai do ajuste e da previsão (não há como estimá-la).

Protocolo
---------
Séries: as 8 categorias, lidas do banco de `DATABASE_URL` como o treino as monta
(`servico_previsao._montar_series`, fluxo sem encomendas grandes). SARIMAX m = 7, d = 0, D = 0,
com constante, janela deslizante de 365 dias, h = 14, ordem por AIC (p, q ∈ 0..2; P, Q ∈ 0..1)
na janela antes da 1ª origem de cada bloco. Origens andando 1 dia, em 4 blocos:
  * as 20 origens de 19 dias antes até cada data de 2025 (protocolo do doc 08): Dia da Mulher;
    Dia do Trabalho + Dia das Mães; Dia dos Namorados;
  * Natal + Ano Novo de 2025 emendados nas 56 origens do treino de produção (22/12/2025 a
    15/02/2026), de 06/12/2025 a 15/02/2026.
O fator de `prd` usa só a venda antes de cada origem, como o sistema. Com a regra da queda
(≥ 2 ocorrências passadas), ela não dispara em 2025: a base começa em 01/2024.

Uso (a partir de `ia-predictor/`, com DATABASE_URL apontando para o banco local):
    python -m training_scripts.datas_comemorativas.fator_vs_exogenas --rodar --workers 14
    python -m training_scripts.datas_comemorativas.fator_vs_exogenas --consolidar
Saída: `training_scripts/results/metrics/fator_vs_exogenas/` (um CSV por série, variante e
bloco; ao consolidar, `resumo_*.csv`).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

from backend.domain.models import datas_comemorativas as dc
from backend.domain.models import evaluator
from backend.domain.models.forecaster import ajustar, prever
from backend.domain.models.order_selection import NenhumaOrdemConvergiu, selecionar_ordem
from backend.domain.models.trainer import ConfigTreino, _ajustes_datas

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA_DIR = os.path.join(_RAIZ, "results", "metrics", "fator_vs_exogenas")

VARIANTES = ("prd", "sem", "exog_evento", "exog_grupo")
EVENTOS = ("Dia da Mulher", "Dia das Mães", "Dia dos Namorados", "Natal", "Ano Novo", "Dia do Trabalho")
_SLUG_EV = {"Dia da Mulher": "mulher", "Dia das Mães": "maes", "Dia dos Namorados": "namorados",
            "Natal": "natal", "Ano Novo": "ano_novo", "Dia do Trabalho": "trabalho"}
D = pd.Timestamp
BLOCOS = {
    "mulher": (D("2025-02-17"), D("2025-03-08")),
    "trabalho_maes": (D("2025-04-12"), D("2025-05-11")),
    "namorados": (D("2025-05-24"), D("2025-06-12")),
    "natal_prd": (D("2025-12-06"), D("2026-02-15")),
}
# as 56 origens do treino de produção (última venda 28/02/2026): de 22/12/2025 a 15/02/2026
ORIGENS_PRD = (D("2025-12-22"), D("2026-02-15"))


def dummies(X: pd.DataFrame) -> pd.DataFrame:
    """Uma coluna por data: 1 nos dias em que o fator do ADR-019 entraria."""
    idx = X.index
    out = pd.DataFrame(0.0, index=idx, columns=[f"ev_{_SLUG_EV[e]}" for e in EVENTOS])
    for e in EVENTOS:
        for ano in range(idx.min().year, idx.max().year + 2):
            out.loc[dc.dias_da_janela(X, dc.data_do_evento(e, ano)), f"ev_{_SLUG_EV[e]}"] = 1.0
    return out


def matriz_variante(X: pd.DataFrame, variante: str) -> pd.DataFrame:
    if variante in ("prd", "sem"):
        return X
    ev = dummies(X)
    if variante == "exog_grupo":
        presente = ev[["ev_mulher", "ev_maes", "ev_namorados", "ev_natal"]].max(axis=1).rename("ev_presente")
        ev = pd.concat([presente, ev[["ev_ano_novo", "ev_trabalho"]]], axis=1)
    return pd.concat([X, ev], axis=1)


def _colunas(Xv: pd.DataFrame, idx_treino: pd.DatetimeIndex) -> list[str]:
    """Exógenas que entram no ajuste: as de calendário e as dummies com algum 1 no treino."""
    return [c for c in Xv.columns if not c.startswith("ev_") or Xv.loc[idx_treino, c].any()]


def rodar_caso(args) -> str:
    chave, y, X, aberta, com_fator, com_queda, variante, bloco = args
    cfg = ConfigTreino()
    nome = f"{chave.replace(':', '_')}__{variante}__{bloco}"
    t = time.time()
    Xv = matriz_variante(X, variante)
    ini, fim = BLOCOS[bloco]
    origens = pd.date_range(ini, fim, freq="D")

    pre = y[y.index < origens[0]].iloc[-cfg.janela_dias:]
    cols = _colunas(Xv, pre.index)
    try:
        escolha = selecionar_ordem(pre, Xv.loc[pre.index, cols], d=cfg.d, D=cfg.D, m=cfg.m, grade_pq=cfg.grade_pq,
                                   grade_PQ=cfg.grade_PQ, maxiter=cfg.maxiter)
    except NenhumaOrdemConvergiu:
        json.dump({"erro": "nenhuma ordem"}, open(os.path.join(SAIDA_DIR, nome + ".json"), "w"))
        return f"{nome} sem ordem"

    linhas, falhas = [], 0
    for origem in origens:
        treino = y[y.index < origem].iloc[-cfg.janela_dias:]
        futuro = pd.date_range(origem, periods=cfg.horizonte, freq="D")
        cols = _colunas(Xv, treino.index)
        try:
            res = ajustar(treino, Xv.loc[treino.index, cols], escolha.ordem, escolha.ordem_sazonal, cfg.maxiter)
            prev, inf, sup = prever(res, Xv.loc[futuro, cols], cfg.alpha)
        except Exception:  # noqa: BLE001 — origem que não ajusta: conta e segue, como o sistema
            falhas += 1
            continue
        if variante == "prd":
            fator, _ = _ajustes_datas(y, X, origem, futuro, cfg, com_fator, com_queda)
        else:
            fator = np.ones(len(futuro))
        ultima_semana = treino.values[-cfg.m:]
        escala = float(np.mean(np.abs(treino.values[cfg.m:] - treino.values[:-cfg.m])))
        for h, dia in enumerate(futuro):
            linhas.append({"origem": origem, "data": dia, "horizonte": h + 1, "previsto": prev[h] * fator[h],
                           "ic_inf": inf[h] * fator[h], "ic_sup": sup[h] * fator[h], "real": float(y.loc[dia]),
                           "naive": float(ultima_semana[h % cfg.m]), "escala": escala,
                           "aberta": bool(aberta.loc[dia]), "fator": float(fator[h])})
    pd.DataFrame(linhas).to_csv(os.path.join(SAIDA_DIR, nome + ".csv"), sep=";", index=False)
    json.dump({"serie": chave, "variante": variante, "bloco": bloco, "ordem": str((escolha.ordem, escolha.ordem_sazonal)),
               "aic": escolha.aic, "falhas": falhas, "segundos": round(time.time() - t)},
              open(os.path.join(SAIDA_DIR, nome + ".json"), "w"), ensure_ascii=False)
    return f"{nome} {escolha.ordem}{escolha.ordem_sazonal} falhas={falhas} {time.time() - t:.0f}s"


def carregar_series():
    from training_scripts.validation.holdout_vs_walk_forward import carregar_series as _c
    return {k: s for k, s in _c().items() if s.nivel == "category"}


def rodar(workers: int) -> None:
    os.makedirs(SAIDA_DIR, exist_ok=True)
    series = carregar_series()
    tarefas = []
    # o bloco longo primeiro: os curtos preenchem o fim
    for bloco in sorted(BLOCOS, key=lambda b: -(BLOCOS[b][1] - BLOCOS[b][0]).days):
        for chave, s in series.items():
            for v in VARIANTES:
                if not os.path.exists(os.path.join(SAIDA_DIR, f"{chave.replace(':', '_')}__{v}__{bloco}.json")):
                    tarefas.append((chave, s.y, s.X, s.aberta, s.com_fator, s.com_queda, v, bloco))
    print(f"{len(series)} séries × {len(VARIANTES)} variantes × {len(BLOCOS)} blocos: {len(tarefas)} tarefas "
          f"em {workers} processos", flush=True)
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"
    t = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, f in enumerate(as_completed([pool.submit(rodar_caso, a) for a in tarefas]), 1):
            print(f"[{i}/{len(tarefas)}] {f.result()}  {time.time() - t:.0f}s", flush=True)


# ---------------------------------------------------------------- consolidação

def _rotulo_evento(X: pd.DataFrame) -> pd.Series:
    """Data comemorativa de cada dia (os dias da dummy), ou None."""
    ev = dummies(X)
    nomes = {f"ev_{_SLUG_EV[e]}": e for e in EVENTOS}
    return ev.idxmax(axis=1).map(nomes).where(ev.max(axis=1) > 0)


def _met(d: pd.DataFrame) -> dict:
    d = d[d["aberta"]]
    if d.empty:
        return {}
    e = (d["real"] - d["previsto"]).abs()
    en = (d["real"] - d["naive"]).abs()
    return {"n": len(d), "mae": e.mean(), "rel_naive": e.sum() / en.sum() if en.sum() else np.nan,
            "mase": (e / d["escala"]).mean(), "cobertura": ((d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])).mean() * 100,
            "largura": (d["ic_sup"] - d["ic_inf"]).mean(), "prev_sobre_real": d["previsto"].sum() / d["real"].sum() * 100}


def consolidar() -> None:
    series = carregar_series()
    rot = {k: _rotulo_evento(s.X) for k, s in series.items()}
    arqs = sorted(glob.glob(os.path.join(SAIDA_DIR, "*__*__*.csv")))
    pts = []
    for a in arqs:
        chave_arq, variante, bloco = os.path.basename(a)[:-4].split("__")
        p = pd.read_csv(a, sep=";", parse_dates=["origem", "data"])
        chave = next(k for k in series if k.replace(":", "_") == chave_arq)
        p["serie"], p["variante"], p["bloco"] = chave, variante, bloco
        p["evento"] = rot[chave].reindex(p["data"]).values
        pts.append(p)
    pts = pd.concat(pts, ignore_index=True)
    pts["aberta"] = pts["aberta"].astype(bool)
    pts["serie"] = pts["serie"].str.replace(":category:", " · ")

    # 1. dias da semana de cada data, por série × variante × data
    ev = pts[pts["evento"].notna()]
    t1 = pd.DataFrame([{"serie": s, "evento": e, "variante": v, **_met(g)}
                       for (s, e, v), g in ev.groupby(["serie", "evento", "variante"])])
    # 2. erro do total da semana: origens de 13 a 6 dias antes da data (semana inteira à frente)
    linhas = []
    for (s, e, v), g in ev.groupby(["serie", "evento", "variante"]):
        g = g[g["aberta"]]
        for d_ev, ge in g.groupby(g["data"].dt.year if e != "Ano Novo" else (g["data"] + pd.Timedelta(days=7)).dt.year):
            data_ev = dc.data_do_evento(e, int(d_ev))
            ok = ge[(ge["origem"] >= data_ev - pd.Timedelta(days=13)) & (ge["origem"] <= data_ev - pd.Timedelta(days=6))]
            tot = ok.groupby("origem")[["previsto", "real"]].sum()
            tot = tot[tot["real"] > 0]
            if len(tot):
                linhas.append({"serie": s, "evento": e, "variante": v, "origens": len(tot),
                               "erro_semana_pct": ((tot["previsto"] - tot["real"]).abs() / tot["real"]).mean() * 100,
                               "prev_sobre_real_semana": tot["previsto"].sum() / tot["real"].sum() * 100})
    t2 = pd.DataFrame(linhas)
    # 3. dias sem data (efeito colateral), todas as origens
    t3 = pd.DataFrame([{"serie": s, "variante": v, **_met(g)}
                       for (s, v), g in pts[pts["evento"].isna()].groupby(["serie", "variante"])])
    # 4. as 56 origens do treino de produção: métricas como o sistema daria
    prd = pts[(pts["origem"] >= ORIGENS_PRD[0]) & (pts["origem"] <= ORIGENS_PRD[1])]
    linhas = []
    for (s, v), g in prd.groupby(["serie", "variante"]):
        m = evaluator.metricas_walk_forward(g)
        linhas.append({"serie": s, "variante": v, "mase": m["mase"], "cobertura": m["cobertura_ic95_pct"],
                       "rel_naive": m["erro_relativo_naive"], "largura": m["largura_ic95"]})
    t4 = pd.DataFrame(linhas)
    # 5. tudo junto (todas as origens, todos os dias)
    t5 = pd.DataFrame([{"serie": s, "variante": v, **_met(g)} for (s, v), g in pts.groupby(["serie", "variante"])])

    for nome, t in (("eventos_dias", t1), ("eventos_semana", t2), ("dias_sem_data", t3), ("metricas_prd", t4),
                    ("geral", t5)):
        t.to_csv(os.path.join(SAIDA_DIR, f"resumo_{nome}.csv"), sep=";", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    fmt = lambda t, val: t.pivot_table(index=[c for c in ("serie", "evento") if c in t], columns="variante",
                                       values=val).reindex(columns=list(VARIANTES)).round(2)
    print("== Semana da data: erro do total da semana (%), origens de 13 a 6 dias antes\n", fmt(t2, "erro_semana_pct"))
    print("\n== Semana da data: previsto ÷ vendido na semana (%)\n", fmt(t2, "prev_sobre_real_semana"))
    print("\n== Dias da semana da data: MAE\n", fmt(t1, "mae"))
    print("\n== Dias da semana da data: cobertura IC95 (%)\n", fmt(t1, "cobertura"))
    print("\n== Dias sem data: erro relativo à naïve\n", fmt(t3, "rel_naive"))
    print("\n== Dias sem data: cobertura IC95 (%)\n", fmt(t3, "cobertura"))
    print("\n== Todas as origens e dias: erro relativo à naïve\n", fmt(t5, "rel_naive"))
    print("\n== 56 origens do treino de produção: MASE\n", fmt(t4, "mase"))
    print("\n== 56 origens do treino de produção: cobertura\n", fmt(t4, "cobertura"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rodar", action="store_true")
    p.add_argument("--consolidar", action="store_true")
    p.add_argument("--workers", type=int, default=14)
    a = p.parse_args()
    if a.rodar:
        rodar(a.workers)
    if a.consolidar:
        consolidar()


if __name__ == "__main__":
    main()
