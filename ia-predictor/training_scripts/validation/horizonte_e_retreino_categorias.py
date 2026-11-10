"""Horizonte da previsão e frequência do retreino, nas 4 categorias das 2 lojas.

Perguntas
---------
1. **Horizonte**: o treino de produção (`treinar_serie`, ADR-017/018/019) continua passando
   nos limiares (MASE < 1, cobertura do IC 95% em [90%, 98%]) se a previsão for de 21, 28, 35
   ou 42 dias em vez de 14? O walk-forward muda junto: 56 origens andando 1 dia, cada uma
   prevendo `horizonte` dias, e a ordem escolhida por AIC antes da 1ª origem.
2. **Retreino**: se a loja treinar a cada 7, 14, 28 ou 56 dias, quanto erra o que ela enxerga
   à frente (os próximos L = 7, 14 ou 28 dias) num dia qualquer? Usa os 52 treinos semanais
   de `treino_trimestral_vs_semanal.py` (cada um prevê até 91 dias): no dia t, vale o treino
   mais recente da rotina com corte ≤ t, e a janela t+1..t+L é prevista com h = (t − corte) + 1
   em diante. Cada rotina é medida em todas as fases possíveis (rotina mensal começando na
   1ª, 2ª, 3ª ou 4ª semana) e nos mesmos dias t, para que só a idade do modelo mude.

Métricas nos dias de loja aberta: erro diário (MAE), erro do total da janela
(|Σ previsto − Σ vendido| / Σ vendido, o que pesa numa compra para o período) e cobertura do
IC 95%.

Uso (a partir de `ia-predictor/`, com o banco local — ver memória do ambiente):
    python -m training_scripts.validation.horizonte_e_retreino_categorias --horizontes --workers 15
    python -m training_scripts.validation.horizonte_e_retreino_categorias --consolidar
Saída: `training_scripts/results/metrics/horizonte_e_retreino_categorias/`.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace

import numpy as np
import pandas as pd

from backend.domain.models.trainer import ConfigTreino, treinar_serie

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA_DIR = os.path.join(_RAIZ, "results", "metrics", "horizonte_e_retreino_categorias")
TRIMESTRAL_DIR = os.path.join(_RAIZ, "results", "metrics", "treino_trimestral_vs_semanal")

LONGAS_DIR = os.path.join(SAIDA_DIR, "previsoes_longas")

HORIZONTES = (14, 21, 28, 35, 42, 56, 91)
CADENCIAS = (7, 14, 28, 56, 91)
JANELAS_LOJA = (7, 14, 28)
# a rotina mais espaçada, no último dia antes do treino seguinte, precisa enxergar a maior
# janela da loja: h até 90 + 28 = 118
H_LONGO = max(CADENCIAS) - 1 + max(JANELAS_LOJA)
FAIXAS_H = [(1, 7), (8, 14), (15, 21), (22, 28), (29, 35), (36, 42)]


def _nome(chave: str, h: int) -> str:
    return f"{chave.replace(':', '_')}_h{h:02d}"


# ---------------------------------------------------------------- 1. horizonte no treino de produção

def rodar_caso(args) -> str:
    chave, nivel, y, X, aberta, com_fator, com_queda, h = args
    cfg = replace(ConfigTreino(), horizonte=h)
    t = time.time()
    r = treinar_serie(y, X, aberta, cfg, nivel, com_fator=com_fator, com_queda=com_queda)
    nome = _nome(chave, h)
    if r.backtest is not None:
        bt = r.backtest.assign(aberta=aberta.reindex(r.backtest["data"]).values)
        bt.to_csv(os.path.join(SAIDA_DIR, nome + ".csv"), index=False, sep=";")
    with open(os.path.join(SAIDA_DIR, nome + ".json"), "w", encoding="utf-8") as f:
        json.dump({"serie": chave, "horizonte": h, "status": r.status, "motivo": r.motivo,
                   "ordem": str((r.ordem, r.ordem_sazonal)), "metricas": r.metricas,
                   "segundos": round(time.time() - t)}, f, ensure_ascii=False, default=str)
    return f"{nome} {r.status}"


def rodar_horizontes(workers: int) -> None:
    from training_scripts.validation.holdout_vs_walk_forward import carregar_series
    os.makedirs(SAIDA_DIR, exist_ok=True)
    series = {k: s for k, s in carregar_series().items() if s.nivel == "category"}
    # os horizontes longos primeiro (mais ajustes no complemento)
    tarefas = [(k, s.nivel, s.y, s.X, s.aberta, s.com_fator, s.com_queda, h)
               for h in sorted(HORIZONTES, reverse=True) for k, s in series.items()
               if not os.path.exists(os.path.join(SAIDA_DIR, _nome(k, h) + ".json"))]
    print(f"{len(series)} séries × {len(HORIZONTES)} horizontes: {len(tarefas)} tarefas em {workers} processos",
          flush=True)
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"
    t = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, f in enumerate(as_completed([pool.submit(rodar_caso, a) for a in tarefas]), 1):
            print(f"[{i}/{len(tarefas)}] {f.result()}  {time.time() - t:.0f}s", flush=True)


def consolidar_horizontes() -> None:
    linhas, faixas = [], []
    for arq in sorted(glob.glob(os.path.join(SAIDA_DIR, "*_h??.json"))):
        with open(arq, encoding="utf-8") as f:
            r = json.load(f)
        m = r["metricas"] or {}
        # com h > 14 a previsão final cai (o calendário gravado cobre só 14 dias depois da
        # última venda: KeyError); o walk-forward já terminou, e as métricas são as dele
        linhas.append({"serie": r["serie"], "h": r["horizonte"], "ordem": r["ordem"],
                       "mase": m.get("mase"), "cobertura": m.get("cobertura_ic95_pct"),
                       "rel_naive": m.get("erro_relativo_naive"), "vence_naive_pct": m.get("origens_vence_naive_pct"),
                       "erro_total_janela_pct": m.get("erro_total_14d_pct"),
                       "prev_sobre_real": m.get("previsto_sobre_real_pct"), "largura_ic": m.get("largura_ic95")})
        csv = arq[:-5] + ".csv"
        if os.path.exists(csv):
            bt = pd.read_csv(csv, sep=";")
            bt = bt[bt["aberta"].astype(bool)]
            bt["ae"] = (bt["real"] - bt["previsto"]).abs()
            bt["aen"] = (bt["real"] - bt["naive"]).abs()
            bt["dentro"] = (bt["real"] >= bt["ic_inf"]) & (bt["real"] <= bt["ic_sup"])
            for a, b in FAIXAS_H:
                d = bt[bt["horizonte"].between(a, b)]
                if len(d):
                    faixas.append({"serie": r["serie"], "h": r["horizonte"], "faixa": f"{a}-{b}",
                                   "mae": d["ae"].mean(), "rel_naive": d["ae"].sum() / d["aen"].sum(),
                                   "cobertura": d["dentro"].mean() * 100})
    res = pd.DataFrame(linhas)
    res.to_csv(os.path.join(SAIDA_DIR, "resumo_horizontes.csv"), index=False, sep=";")
    print("== métricas do walk-forward por horizonte")
    print(res.drop(columns=["ordem"]).to_string(index=False))
    print("\nMASE por horizonte:\n", res.pivot(index="serie", columns="h", values="mase").to_string())
    print("\nordem por horizonte:\n", res.pivot(index="serie", columns="h", values="ordem").to_string())
    if faixas:
        fx = pd.DataFrame(faixas)
        fx.to_csv(os.path.join(SAIDA_DIR, "resumo_horizontes_por_faixa.csv"), index=False, sep=";")
        print("\ncobertura do IC 95% por faixa de h (média das 8 séries):\n",
              fx.groupby(["h", "faixa"])["cobertura"].mean().unstack().round(1).to_string())
        print("\nerro relativo à naïve por faixa de h (média das 8 séries):\n",
              fx.groupby(["h", "faixa"])["rel_naive"].mean().unstack().round(3).to_string())


# ---------------------------------------------------------------- 2. frequência do retreino

def estender_caso(args) -> str:
    """Refaz o ajuste final de um treino semanal de `treino_trimestral_vs_semanal.py` com a
    ordem que ele escolheu e prevê até `H_LONGO` dias (o original para em 91)."""
    from ast import literal_eval
    from backend.domain.models.forecaster import ajustar, prever
    from backend.domain.models.trainer import _ajustes_datas
    chave, y, X, aberta, com_fator, com_queda, corte, ordem = args
    cfg = ConfigTreino()
    o, os_ = literal_eval(ordem)
    y_c = y[y.index <= corte]
    janela = y_c.iloc[-cfg.janela_dias:]
    dias = pd.date_range(corte + pd.Timedelta(days=1), min(corte + pd.Timedelta(days=H_LONGO), y.index.max()))
    res = ajustar(janela, X.loc[janela.index], o, os_, cfg.maxiter)
    prev, inf, sup = prever(res, X.loc[dias], cfg.alpha)
    fator, _ = _ajustes_datas(y_c, X, dias[0], dias, cfg, com_fator, com_queda)
    naive = np.array([janela.values[-cfg.m:][i % cfg.m] for i in range(len(dias))])
    nome = f"{chave.replace(':', '_')}_{corte:%Y%m%d}"
    pd.DataFrame({"serie": chave, "corte": corte, "data": dias, "h": np.arange(1, len(dias) + 1), "ordem": ordem,
                  "real": y.loc[dias].values, "previsto": prev * fator, "ic_inf": inf * fator, "ic_sup": sup * fator,
                  "naive": naive, "aberta": aberta.loc[dias].values}).to_csv(
        os.path.join(LONGAS_DIR, nome + ".csv"), index=False, sep=";")
    return nome


def rodar_estender(workers: int) -> None:
    from training_scripts.validation.holdout_vs_walk_forward import carregar_series
    os.makedirs(LONGAS_DIR, exist_ok=True)
    series = carregar_series()
    tarefas = []
    for arq in sorted(glob.glob(os.path.join(TRIMESTRAL_DIR, "*_category_*_2*.csv"))):
        if os.path.exists(os.path.join(LONGAS_DIR, os.path.basename(arq))):
            continue
        p = pd.read_csv(arq, sep=";", nrows=1, parse_dates=["corte"])
        s = series[p["serie"].iloc[0]]
        tarefas.append((s.chave, s.y, s.X, s.aberta, s.com_fator, s.com_queda, p["corte"].iloc[0], p["ordem"].iloc[0]))
    print(f"{len(tarefas)} treinos semanais a estender até h = {H_LONGO}", flush=True)
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"
    t = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, f in enumerate(as_completed([pool.submit(estender_caso, a) for a in tarefas]), 1):
            if i % 20 == 0 or i == len(tarefas):
                print(f"[{i}/{len(tarefas)}] {f.result()}  {time.time() - t:.0f}s", flush=True)


def consolidar_retreino() -> None:
    arqs = glob.glob(os.path.join(LONGAS_DIR, "*_2*.csv"))
    pts = pd.concat(pd.read_csv(f, sep=";", parse_dates=["corte", "data"]) for f in arqs)
    pts["aberta"] = pts["aberta"].astype(bool)
    cortes = sorted(pts["corte"].unique())
    primeiro, fim = cortes[0], pts["data"].max()
    passo = 7
    # dias de decisão: a partir de 91 dias depois do 1º treino (toda rotina e fase já treinou)
    # até o último dia que ainda tem a maior janela inteira à frente — os mesmos dias em todas
    # as rotinas
    dias_t = pd.date_range(primeiro + pd.Timedelta(days=max(CADENCIAS)), fim - pd.Timedelta(days=max(JANELAS_LOJA)))
    linhas = []
    for serie, ps in pts.groupby("serie"):
        p = {c: g.set_index("data") for c, g in ps.groupby("corte")}
        for k in CADENCIAS:
            for fase in range(0, k, passo):
                agenda = [c for c in cortes if ((c - primeiro).days - fase) % k == 0 and (c - primeiro).days >= fase]
                agenda = pd.DatetimeIndex(agenda)
                for L in JANELAS_LOJA:
                    for t in dias_t:
                        c = agenda[agenda <= t].max()
                        janela = pd.date_range(t + pd.Timedelta(days=1), periods=L)
                        d = p[c].loc[janela]
                        d = d[d["aberta"]]
                        if d.empty or d["real"].sum() <= 0:
                            continue
                        linhas.append({"serie": serie, "cadencia": k, "fase": fase, "L": L, "t": t,
                                       "idade": (t - c).days, "ae": (d["real"] - d["previsto"]).abs().sum(),
                                       "n": len(d), "real": d["real"].sum(), "prev": d["previsto"].sum(),
                                       "dentro": ((d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])).sum()})
    df = pd.DataFrame(linhas)
    df.to_csv(os.path.join(SAIDA_DIR, "retreino_dias.csv"), index=False, sep=";")
    df["erro_total"] = (df["prev"] - df["real"]).abs()
    g = df.groupby(["serie", "cadencia", "L"]).agg(ae=("ae", "sum"), n=("n", "sum"), erro_total=("erro_total", "sum"),
                                                  real=("real", "sum"), dentro=("dentro", "sum"))
    g["mae"] = g["ae"] / g["n"]
    g["erro_total_pct"] = g["erro_total"] / g["real"] * 100
    g["cobertura"] = g["dentro"] / g["n"] * 100
    base = g.xs(7, level="cadencia")
    g["mae_vs_semanal"] = (g["mae"] / base["mae"].reindex(g.index.droplevel("cadencia")).values - 1) * 100
    g["erro_total_vs_semanal"] = (g["erro_total_pct"] / base["erro_total_pct"].reindex(
        g.index.droplevel("cadencia")).values - 1) * 100
    g = g.round(2)
    g.to_csv(os.path.join(SAIDA_DIR, "resumo_retreino.csv"), sep=";")
    print("\n== retreino: piora do erro diário sobre o treino semanal (%), por série e janela da loja")
    print(g["mae_vs_semanal"].unstack("cadencia").to_string())
    print("\n== retreino: erro do total da janela (% do vendido)")
    print(g["erro_total_pct"].unstack("cadencia").to_string())
    tot = df.groupby(["cadencia", "L"]).agg(ae=("ae", "sum"), n=("n", "sum"), erro_total=("erro_total", "sum"),
                                            real=("real", "sum"), dentro=("dentro", "sum"))
    tot["mae_idx"] = tot["ae"] / tot["n"]
    tot["mae_idx"] = tot["mae_idx"] / tot["mae_idx"].xs(7, level="cadencia").reindex(
        tot.index.get_level_values("L")).values * 100
    tot["erro_total_pct"] = tot["erro_total"] / tot["real"] * 100
    tot["cobertura"] = tot["dentro"] / tot["n"] * 100
    tot = tot[["mae_idx", "erro_total_pct", "cobertura"]].round(1)
    tot.to_csv(os.path.join(SAIDA_DIR, "resumo_retreino_total.csv"), sep=";")
    print("\n== retreino, 8 séries somadas (erro diário: semanal = 100)")
    print(tot.to_string())
    # média das séries (cada série pesa igual, não pelo volume)
    media = g.groupby(["cadencia", "L"])[["mae_vs_semanal", "erro_total_pct", "cobertura"]].mean().round(1)
    print("\n== retreino, média das 8 séries")
    print(media.to_string())


def metricas_no_ano() -> None:
    """MASE e cobertura da faixa de 95% para cada horizonte, num ano
    inteiro em vez das 8 semanas do walk-forward de produção: as origens são os treinos
    semanais de 01/03/2025 até 91 dias antes do fim (as mesmas em todo horizonte), cada uma
    avaliada nos `h` dias seguintes. Escala do MASE como em produção: erro médio da naïve
    sazonal (7 dias) dentro da janela de 365 dias do treino."""
    from training_scripts.validation.holdout_vs_walk_forward import carregar_series
    series = carregar_series()
    pts = pd.concat(pd.read_csv(f, sep=";", parse_dates=["corte", "data"])
                    for f in glob.glob(os.path.join(LONGAS_DIR, "*_2*.csv")))
    pts = pts[pts["aberta"].astype(bool)]
    fim = pts["data"].max()
    pts = pts[pts["corte"] <= fim - pd.Timedelta(days=91)]
    escalas = {}
    for (serie, corte) in pts[["serie", "corte"]].drop_duplicates().itertuples(index=False):
        j = series[serie].y
        j = j[j.index <= corte].iloc[-365:].values
        escalas[(serie, corte)] = float(np.mean(np.abs(j[7:] - j[:-7])))
    pts["escala"] = [escalas[k] for k in zip(pts["serie"], pts["corte"])]
    pts["ae"] = (pts["real"] - pts["previsto"]).abs()
    pts["aen"] = (pts["real"] - pts["naive"]).abs()
    pts["dentro"] = (pts["real"] >= pts["ic_inf"]) & (pts["real"] <= pts["ic_sup"])
    linhas = []
    for h in HORIZONTES:
        d = pts[pts["h"] <= h]
        for serie, g in d.groupby("serie"):
            tot = g.groupby("corte")[["previsto", "real"]].sum()
            m = {"mase": (g["ae"] / g["escala"]).mean(), "cobertura_ic95_pct": g["dentro"].mean() * 100}
            linhas.append({"serie": serie, "h": h, "origens": g["corte"].nunique(), "mase": m["mase"],
                           "cobertura": m["cobertura_ic95_pct"], "rel_naive": g["ae"].sum() / g["aen"].sum(),
                           "erro_total_janela_pct": (tot["previsto"] - tot["real"]).abs().sum() / tot["real"].sum() * 100})
    res = pd.DataFrame(linhas).round(3)
    res.to_csv(os.path.join(SAIDA_DIR, "resumo_metricas_no_ano.csv"), index=False, sep=";")
    print("\n== métricas no ano (origens semanais 01/03/2025 a 91 dias antes do fim)")
    for col in ("mase", "cobertura", "erro_total_janela_pct"):
        print(f"\n{col}:\n", res.pivot(index="serie", columns="h", values=col).to_string())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--horizontes", action="store_true")
    ap.add_argument("--estender", action="store_true")
    ap.add_argument("--consolidar", action="store_true")
    ap.add_argument("--workers", type=int, default=15)
    a = ap.parse_args()
    if a.horizontes:
        rodar_horizontes(a.workers)
    if a.estender:
        rodar_estender(a.workers)
    if a.consolidar:
        os.makedirs(SAIDA_DIR, exist_ok=True)
        consolidar_horizontes()
        metricas_no_ano()
        consolidar_retreino()


if __name__ == "__main__":
    main()
