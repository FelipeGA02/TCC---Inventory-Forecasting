"""O modelo volta à média do ano: janela menor, d = 1 ou sazonalidade anual corrigem isso?

Pergunta
--------
Com d = 0 e janela de 365 dias, o SARIMAX de produção volta à média do último ano em ~2
semanas: prevê demais na baixa (jan–fev: 119% a 157% do vendido no walk-forward de
28/02/2026) e de menos na virada para a alta (doc 09). Três variantes, cada uma mudando só uma
coisa na receita de produção (ADR-017/018/019):

  - **base**:     a receita de produção (janela 365, d = 0, sem termo anual);
  - **janela180**: janela deslizante de 180 dias (no ajuste e na escolha da ordem): a média para
    a qual o modelo volta fica mais perto do nível atual;
  - **d1**:       d = 1 (sem constante, como em `forecaster.ajustar`): a previsão parte do nível
    recente e não volta à média;
  - **fourier**:  regressão harmônica (Hyndman & Athanasopoulos, *Forecasting: Principles and
    Practice*, 3ª ed., §10.5 e §12.1): K pares sen/cos de período 365,25 dias como exógenas, K ∈
    {1, 2} escolhido por AIC junto com a ordem — o modelo aprende o formato do ano na janela.

Protocolo
---------
Os 52 cortes semanais de `treino_trimestral_vs_semanal.py` (01/03/2025 a 21/02/2026), as 4
categorias das 2 lojas. Em cada corte, ajuste final na janela até o corte e previsão dos 28
dias seguintes, com o fator das datas comemorativas calculado só com venda até o corte. A
ordem (e K) é escolhida por AIC, como em produção, na janela antes da 1ª origem do
walk-forward, mas **a cada 4 cortes** (13 escolhas por série), reaproveitada nos 3 seguintes —
inclusive na **base**, que reusa a ordem que o experimento original escolheu no 1º corte de
cada bloco. Assim as 4 variantes seguem o mesmo protocolo.

Sazonalidade anual com o histórico inteiro (`--anual`)
-----------------------------------------------------
Com a janela de 365 dias cada mês aparece uma vez, e os termos anuais se confundem com o nível.
`--anual` refaz o teste com a janela **de todo o histórico** (desde jan/2024: 2 janeiros para
prever o 3º), d = 0 e d = 1, com e sem Fourier anual — variantes `hist`, `hist_fourier`, `hist_d1`
e `hist_fourier_d1` — nas 8 categorias; `--consolidar-anual` compara com `base` e `d1` (365 dias).

Uso (a partir de `ia-predictor/`, banco local):
    python -m training_scripts.validation.variantes_nivel_sazonal --rodar --workers 15
    python -m training_scripts.validation.variantes_nivel_sazonal --consolidar
Saída: `training_scripts/results/metrics/variantes_nivel_sazonal/`.
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

from backend.domain.models.forecaster import ajustar, prever
from backend.domain.models.order_selection import NenhumaOrdemConvergiu, selecionar_ordem
from backend.domain.models.trainer import ConfigTreino, _ajustes_datas, _janela, motivo_inelegivel, origens_walk_forward

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA_DIR = os.path.join(_RAIZ, "results", "metrics", "variantes_nivel_sazonal")
TRIMESTRAL_DIR = os.path.join(_RAIZ, "results", "metrics", "treino_trimestral_vs_semanal")

H = 28
PRIMEIRO_CORTE = pd.Timestamp("2025-03-01")
FIM_TESTE = pd.Timestamp("2026-02-28")
BLOCO = 4
VARIANTES = ("base", "janela180", "d1", "fourier")
VARIANTES_ANUAIS = ("hist", "hist_fourier", "hist_d1", "hist_fourier_d1")
JANELA_TODA = 100_000  # dias: o histórico inteiro até o corte
K_FOURIER = (1, 2)
PERIODO_ANO = 365.25
EPOCA = pd.Timestamp("2024-01-01")


def _cfg(variante: str) -> ConfigTreino:
    cfg = ConfigTreino()
    if variante == "janela180":
        return replace(cfg, janela_dias=180)
    if variante.startswith("hist"):
        cfg = replace(cfg, janela_dias=JANELA_TODA)
    if variante.endswith("d1"):
        cfg = replace(cfg, d=1)
    return cfg


def _fourier(idx: pd.DatetimeIndex, k: int) -> pd.DataFrame:
    t = (idx - EPOCA).days.values.astype(float)
    cols = {}
    for j in range(1, k + 1):
        cols[f"sen{j}"] = np.sin(2 * np.pi * j * t / PERIODO_ANO)
        cols[f"cos{j}"] = np.cos(2 * np.pi * j * t / PERIODO_ANO)
    return pd.DataFrame(cols, index=idx)


def _x(X: pd.DataFrame, k: int) -> pd.DataFrame:
    return X if k == 0 else pd.concat([X, _fourier(X.index, k)], axis=1)


def _nome(variante: str, chave: str, corte: pd.Timestamp) -> str:
    return f"{variante}_{chave.replace(':', '_')}_{corte:%Y%m%d}"


def rodar_bloco(args) -> str:
    variante, chave, nivel, y, X, aberta, com_fator, com_queda, cortes, ordem_base, saida = args
    cfg = _cfg(variante)
    primeiro = cortes[0]
    y_c = y[y.index <= primeiro]
    # produto que em produção ficaria sem previsão neste corte (histórico curto, poucos dias
    # com venda) fica fora nas duas variantes
    if motivo_inelegivel(y_c, ConfigTreino(), nivel):
        for c in cortes:
            open(os.path.join(saida, _nome(variante, chave, c) + ".pulado"), "w").close()
        return f"{variante} {chave} {primeiro:%Y%m%d}: inelegível"
    pre = _janela(y_c, origens_walk_forward(primeiro, cfg)[0], cfg.janela_dias)
    # escolha da ordem (e de K) no 1º corte do bloco
    if variante == "base" and ordem_base is not None:
        o, os_ = literal_eval(ordem_base)
        k = 0
    else:
        melhor = None
        for k_ in (K_FOURIER if "fourier" in variante else (0,)):
            try:
                esc = selecionar_ordem(pre, _x(X, k_).loc[pre.index], d=cfg.d, D=cfg.D, m=cfg.m,
                                       grade_pq=cfg.grade_pq, grade_PQ=cfg.grade_PQ, maxiter=cfg.maxiter)
            except NenhumaOrdemConvergiu:
                continue
            if melhor is None or esc.aic < melhor[0]:
                melhor = (esc.aic, esc.ordem, esc.ordem_sazonal, k_)
        if melhor is None:
            return f"{variante} {chave} {primeiro:%Y%m%d}: nenhuma ordem"
        _, o, os_, k = melhor
    Xk = _x(X, k)
    feitos = 0
    for corte in cortes:
        y_c = y[y.index <= corte]
        janela = y_c.iloc[-cfg.janela_dias:]
        dias = pd.date_range(corte + pd.Timedelta(days=1), min(corte + pd.Timedelta(days=H), y.index.max()))
        try:
            res = ajustar(janela, Xk.loc[janela.index], o, os_, cfg.maxiter)
            prev, inf, sup = prever(res, Xk.loc[dias], cfg.alpha)
        except Exception:  # noqa: BLE001 — corte que não ajusta fica sem previsão (contado no consolidado)
            continue
        fator, _ = _ajustes_datas(y_c, X, dias[0], dias, ConfigTreino(), com_fator, com_queda)
        base_janela = y_c.iloc[-ConfigTreino().janela_dias:]
        naive = np.array([base_janela.values[-7:][i % 7] for i in range(len(dias))])
        pd.DataFrame({"variante": variante, "serie": chave, "corte": corte, "data": dias,
                      "h": np.arange(1, len(dias) + 1), "ordem": str((o, os_)), "k": k,
                      "real": y.loc[dias].values, "previsto": prev * fator, "ic_inf": inf * fator,
                      "ic_sup": sup * fator, "naive": naive, "aberta": aberta.loc[dias].values}).to_csv(
            os.path.join(saida, _nome(variante, chave, corte) + ".csv"), index=False, sep=";")
        feitos += 1
    return f"{variante} {chave} {primeiro:%Y%m%d}: {feitos}/{len(cortes)} (k={k}, {o}{os_})"


def _saida(produtos: bool) -> str:
    return SAIDA_DIR + "_produtos" if produtos else SAIDA_DIR


def _variantes(produtos: bool) -> tuple[str, ...]:
    # nos produtos de grama, só a pergunta que ficou aberta nas categorias: d = 1 na família Grama
    return ("base", "d1") if produtos else VARIANTES


def rodar(workers: int, produtos: bool = False, variantes: tuple[str, ...] | None = None) -> None:
    from training_scripts.validation.holdout_vs_walk_forward import carregar_series
    saida = _saida(produtos)
    os.makedirs(saida, exist_ok=True)
    todas = carregar_series()
    if produtos:
        # os produtos de grama que têm previsão em produção (elegíveis com a base inteira)
        series = {k: s for k, s in todas.items() if s.nivel == "product" and not motivo_inelegivel(s.y, ConfigTreino(), s.nivel)}
    else:
        series = {k: s for k, s in todas.items() if s.nivel == "category"}
    print(f"{len(series)} séries: {sorted(series)}", flush=True)
    cortes = list(pd.date_range(PRIMEIRO_CORTE, FIM_TESTE - pd.Timedelta(days=7), freq="7D"))
    blocos = [cortes[i:i + BLOCO] for i in range(0, len(cortes), BLOCO)]
    tarefas = []
    ordem = list(variantes) if variantes else [v for v in ("fourier", "d1", "janela180", "base") if v in _variantes(produtos)]
    for variante in ordem:
        for chave, s in series.items():
            for b in blocos:
                if all(glob.glob(os.path.join(saida, _nome(variante, chave, c) + ".*")) for c in b):
                    continue
                orig = os.path.join(TRIMESTRAL_DIR, f"{chave.replace(':', '_')}_{b[0]:%Y%m%d}.csv")
                ordem_base = (pd.read_csv(orig, sep=";", nrows=1)["ordem"].iloc[0]
                              if variante == "base" and not produtos else None)
                tarefas.append((variante, chave, s.nivel, s.y, s.X, s.aberta, s.com_fator, s.com_queda, b,
                                ordem_base, saida))
    print(f"{len(cortes)} cortes em {len(blocos)} blocos; {len(tarefas)} tarefas em {workers} processos", flush=True)
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = "1"
    t = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, f in enumerate(as_completed([pool.submit(rodar_bloco, a) for a in tarefas]), 1):
            print(f"[{i}/{len(tarefas)}] {f.result()}  {time.time() - t:.0f}s", flush=True)


# ---------------------------------------------------------------- consolidação

def _met(d: pd.DataFrame) -> pd.Series:
    e, en = (d["real"] - d["previsto"]).abs(), (d["real"] - d["naive"]).abs()
    return pd.Series({"dias": len(d), "mae": e.mean(), "rel_naive": e.sum() / en.sum(),
                      "cobertura": ((d["real"] >= d["ic_inf"]) & (d["real"] <= d["ic_sup"])).mean() * 100,
                      "prev_real": d["previsto"].sum() / d["real"].sum() * 100,
                      "largura": (d["ic_sup"] - d["ic_inf"]).mean()})


def consolidar(produtos: bool = False) -> None:
    pd.set_option("display.width", 250)
    SAIDA = _saida(produtos)
    variantes = _variantes(produtos)
    pts = pd.concat(pd.read_csv(f, sep=";", parse_dates=["corte", "data"])
                    for f in glob.glob(os.path.join(SAIDA, "*_2*.csv")))
    pts = pts[pts["aberta"].astype(bool)]
    # só (série, corte) que todas as variantes previram
    n = pts.groupby(["serie", "corte"])["variante"].nunique()
    ok = n[n == len(variantes)].index
    faltam = len(n) - len(ok)
    pts = pts.set_index(["serie", "corte"]).loc[ok].reset_index()
    print(f"(série, corte) com as {len(variantes)} variantes: {len(ok)}; sem alguma: {faltam}")
    sem = pts[pts["h"] <= 7]                     # treino semanal: cada dia pelo treino mais recente
    linhas = []
    for (serie, var), g in sem.groupby(["serie", "variante"]):
        linhas.append({"serie": serie, "variante": var, **_met(g)})
    r = pd.DataFrame(linhas)
    base = r[r["variante"] == "base"].set_index("serie")["mae"]
    r["mae_vs_base"] = (r["mae"] / r["serie"].map(base) - 1) * 100
    r.round(3).to_csv(os.path.join(SAIDA, "resumo_semanal.csv"), index=False, sep=";")
    print("\n== treino semanal (h 1–7), ano inteiro: erro diário sobre a base (%)")
    print(r.pivot(index="serie", columns="variante", values="mae_vs_base").round(1).to_string())
    print("\nerro relativo à naïve sazonal:")
    print(r.pivot(index="serie", columns="variante", values="rel_naive").round(3).to_string())
    print("\ncobertura do IC 95%:")
    print(r.pivot(index="serie", columns="variante", values="cobertura").round(1).to_string())
    print("\nprevisto ÷ vendido (%):")
    print(r.pivot(index="serie", columns="variante", values="prev_real").round(1).to_string())
    print("\nlargura média do IC 95% (un.):")
    print(r.pivot(index="serie", columns="variante", values="largura").round(0).to_string())

    # por mês (treino semanal), 8 séries somadas
    sem = sem.assign(mes=sem["data"].dt.to_period("M"), ae=(sem["real"] - sem["previsto"]).abs())
    mes = sem.groupby(["variante", "mes"]).agg(ae=("ae", "sum"), prev=("previsto", "sum"), real=("real", "sum"))
    idx = (mes["ae"] / mes["ae"].xs("base", level="variante").reindex(mes.index.get_level_values("mes")).values * 100)
    print("\n== por mês, 8 séries somadas: erro diário (base = 100)")
    print(idx.unstack("variante").round(0).to_string())
    print("\nprevisto ÷ vendido por mês (%):")
    print((mes["prev"] / mes["real"] * 100).unstack("variante").round(0).to_string())
    pd.concat({"erro_idx": idx, "prev_real": mes["prev"] / mes["real"] * 100}, axis=1).round(1).to_csv(
        os.path.join(SAIDA, "resumo_por_mes.csv"), sep=";")

    # horizonte de 28 dias: todos os cortes, h 1–28, por faixa de semana
    pts = pts.assign(sem_h=(pts["h"] - 1) // 7 + 1, ae=(pts["real"] - pts["previsto"]).abs())
    hz = pts.groupby(["variante", "sem_h"])["ae"].mean().unstack("variante")
    print("\n== erro diário por semana do horizonte (todos os cortes), base da 1ª semana = 100")
    print((hz / hz.loc[1, "base"] * 100).round(1).to_string())
    print("\nK escolhido (fourier):", pts[pts["variante"] == "fourier"].groupby("k")["corte"].nunique().to_dict())


def consolidar_anual() -> None:
    """Histórico inteiro com e sem Fourier anual × a receita de 365 dias, nas 8 categorias somadas."""
    import statsmodels.api as sm
    pd.set_option("display.width", 250)
    todas = ("base", "d1") + VARIANTES_ANUAIS
    pts = pd.concat(pd.read_csv(f, sep=";", parse_dates=["corte", "data"])
                    for v in todas for f in glob.glob(os.path.join(SAIDA_DIR, f"{v}_*_2*.csv")))
    pts = pts[pts["aberta"].astype(bool) & (pts["h"] <= 7)]   # treino semanal: os 7 dias seguintes
    w = pts.pivot_table(index=["serie", "corte", "data"], columns="variante", values="previsto").dropna()
    real = pts[pts["variante"] == "base"].set_index(["serie", "corte", "data"])["real"]
    w = w.join(real).reset_index()
    print(f"pontos com as {len(todas)} variantes: {len(w)}; séries: {w['serie'].nunique()}; cortes: {w['corte'].nunique()}")
    for v in todas:
        w[f"ae_{v}"] = (w["real"] - w[v]).abs()

    def dm(g, a, b):
        dd = (g[f"ae_{a}"] - g[f"ae_{b}"]).groupby(g["data"]).sum()
        return sm.OLS(dd.values, np.ones(len(dd))).fit(cov_type="HAC", cov_kwds={"maxlags": 7}).pvalues[0]

    pares = [("hist", "base", "janela toda × 365 (d = 0)"), ("hist_fourier", "hist", "Fourier anual, janela toda (d = 0)"),
             ("hist_fourier", "base", "janela toda + Fourier × produção 365 (d = 0)"),
             ("hist_d1", "d1", "janela toda × 365 (d = 1)"), ("hist_fourier_d1", "hist_d1", "Fourier anual, janela toda (d = 1)"),
             ("hist_fourier_d1", "d1", "janela toda + Fourier × 365 (d = 1)")]
    linhas = []
    w["mes"] = w["data"].dt.month
    for a, b, nome in pares:
        r = {"comparacao": nome, "total_pct": (w[f"ae_{a}"].sum() / w[f"ae_{b}"].sum() - 1) * 100, "p": dm(w, a, b)}
        for mes, rot in ((1, "jan"), (2, "fev"), (11, "nov"), (12, "dez")):
            g = w[w["mes"] == mes]
            r[rot] = (g[f"ae_{a}"].sum() / g[f"ae_{b}"].sum() - 1) * 100
        linhas.append(r)
    res = pd.DataFrame(linhas)
    res.round(3).to_csv(os.path.join(SAIDA_DIR, "anual_resumo.csv"), sep=";", index=False)
    print("\n== erro diário, 8 categorias somadas (a sobre b, %)\n", res.round(2).to_string(index=False))
    mes = w.groupby("mes")
    pr = pd.DataFrame({v: mes[v].sum() / mes["real"].sum() * 100 for v in todas})
    print("\n== previsto ÷ vendido por mês (%)\n", pr.round(0).to_string())
    er = pd.DataFrame({v: mes[f"ae_{v}"].sum() for v in todas})
    print("\n== erro por mês, base = 100\n", (er.div(er["base"], axis=0) * 100).round(0).to_string())
    se = w.groupby("serie")
    print("\n== por série: erro sobre a base (%)\n",
          pd.DataFrame({v: (se[f"ae_{v}"].sum() / se["ae_base"].sum() - 1) * 100 for v in todas[1:]}).round(1).to_string())
    print("\nK escolhido:", pts[pts["variante"].str.contains("fourier")].groupby(["variante", "k"])["corte"].nunique().to_dict())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rodar", action="store_true")
    ap.add_argument("--consolidar", action="store_true")
    ap.add_argument("--workers", type=int, default=15)
    ap.add_argument("--produtos", action="store_true", help="produtos de grama: base × d1")
    ap.add_argument("--anual", action="store_true", help="roda as variantes de janela toda (com e sem Fourier)")
    ap.add_argument("--consolidar-anual", action="store_true")
    a = ap.parse_args()
    if a.anual:
        rodar(a.workers, False, VARIANTES_ANUAIS)
    if a.consolidar_anual:
        consolidar_anual()
    if a.rodar:
        rodar(a.workers, a.produtos)
    if a.consolidar:
        consolidar(a.produtos)


if __name__ == "__main__":
    main()
