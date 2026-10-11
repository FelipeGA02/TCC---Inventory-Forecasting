"""Enriquecimento sobre a série crua pré-EDA: A0-crua × A1-crua (calendário) × B-crua (+ clima).

Mesma estratégia do baseline `baseline/sarimax_serie_crua.py`: a mesma série total crua
(base de 2026-08-30, sem separar encomendas), o mesmo grid/AIC, log1p e d via ADF, os mesmos
hold-out de 28 dias e 4 folds de 14 dias. A única diferença entre os modelos são as
variáveis externas (exógenas). Assim o ganho medido é só do enriquecimento.

Modelos:
- A0-crua: sem exógenas (refeito aqui; tem de reproduzir o baseline).
- A1-crua: calendário. Dia da semana, feriado/loja fechada (BrasilAPI + fechamentos locais
  observados), véspera e dia seguinte a feriado, janelas de 7 dias antes das datas
  comemorativas, início do mês.
- B-crua: calendário + clima (chuva do dia, chuva acumulada em 7 dias, temperatura máxima;
  Open-Meteo). **Atenção:** o teste usa o clima observado, como se a previsão do tempo fosse
  perfeita. É o teto do ganho possível; em produção entraria a previsão do tempo.

Avaliações extras (além das do baseline):
- dezembro/2025 (28 dias, treino até 30/11);
- um ano inteiro de rodadas (26 × 14 dias, mar/2025 → fev/2026). Aqui a ordem do modelo é
  escolhida só com os dados anteriores à primeira rodada, então a escolha não vê o
  período testado (corrige o vazamento apontado no baseline, §5 item 6). Dezembro usa essa
  mesma ordem.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.enriched.sarimax_serie_crua_enriquecida
    python -m training_scripts.enriched.sarimax_serie_crua_enriquecida --so-graficos  # refaz só os gráficos
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time
import warnings
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX

from training_scripts.baseline import sarimax_serie_crua as base
from training_scripts.eda._common import datas_comemorativas
from training_scripts.preprocessing.dados_externos_10 import (
    FECHAMENTOS_LOCAIS,
    clima_diario,
    feriados_nacionais,
)

warnings.filterwarnings("ignore")

_TRAINING_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_DIR = os.path.join(_TRAINING_SCRIPTS_DIR, "results", "metrics")
PLOTS_DIR = os.path.join(_TRAINING_SCRIPTS_DIR, "results", "plots", "enriquecido")
NOME = "enriquecimento_serie_crua_pre_eda"

N_FOLDS_ANO = 26
INICIO_DEZ = pd.Timestamp("2025-12-01")
JANELA_DATA = 7  # dias antes (inclusive) de cada data comemorativa

DIAS = ["seg", "ter", "qua", "qui", "sex", "sab"]
DATAS = {
    "Dia das Mães": "maes", "Dia dos Namorados": "namorados", "Dia da Mulher": "mulher",
    "Finados": "finados", "Natal": "natal", "Dia dos Pais": "pais",
}
COLS_CAL = ([f"dia_{d}" for d in DIAS] + ["feriado", "vespera_feriado", "pos_feriado"]
            + [f"antes_{v}" for v in DATAS.values()] + ["inicio_mes"])
COLS_CLIMA = ["chuva_dia", "chuva_7d", "temp_max"]
MODELOS = {
    "A0_crua": [],
    "A1_crua_calendario": COLS_CAL,
    "B_crua_calendario_clima": COLS_CAL + COLS_CLIMA,
}
ROTULO = {"A0_crua": "A0 · sem nada extra", "A1_crua_calendario": "A1 · + calendário",
          "B_crua_calendario_clima": "B · + calendário + clima"}
COR = {"A0_crua": "#8e8e8e", "A1_crua_calendario": "#2e86c1", "B_crua_calendario_clima": "#c0392b",
       "naive": "#27ae60"}
FMT_MIL = mtick.FuncFormatter(lambda v, _: f"{v / 1000:.0f} mil" if abs(v) >= 1000 else f"{v:.0f}")


# --------------------------------------------------------------------------- #
# Exógenas
# --------------------------------------------------------------------------- #
def montar_exogenas(idx: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.Series]:
    anos = range(idx.min().year, idx.max().year + 1)
    X = pd.DataFrame(index=idx)
    for i, d in enumerate(DIAS):
        X[f"dia_{d}"] = (idx.dayofweek == i).astype(float)

    fechado = set(feriados_nacionais(anos)["data"]) | set(pd.to_datetime(FECHAMENTOS_LOCAIS))
    feriado = pd.Series(idx.isin(list(fechado)), index=idx)
    aberto = (idx.dayofweek < 6) & ~feriado.values
    X["feriado"] = (feriado & (idx.dayofweek < 6)).astype(float)
    amanha_fechado = pd.Series(feriado.values, index=idx).shift(-1, fill_value=False)
    ontem_fechado = pd.Series(feriado.values, index=idx).shift(1, fill_value=False)
    X["vespera_feriado"] = (aberto & amanha_fechado.values).astype(float)
    X["pos_feriado"] = (aberto & ontem_fechado.values).astype(float)

    dc = datas_comemorativas(anos)
    for evento, sufixo in DATAS.items():
        col = pd.Series(0.0, index=idx)
        for dia in dc.loc[dc["evento"] == evento, "data"]:
            col[(idx >= dia - pd.Timedelta(days=JANELA_DATA - 1)) & (idx <= dia)] = 1.0
        X[f"antes_{sufixo}"] = col
    X["inicio_mes"] = (idx.day <= 7).astype(float)

    clima = clima_diario(str(idx.min().date()), str(idx.max().date())).reindex(idx)
    X["chuva_dia"] = np.log1p(clima["chuva_mm"])
    X["chuva_7d"] = np.log1p(clima["chuva_mm"].rolling(7, min_periods=1).sum())
    X["temp_max"] = clima["temp_max"]
    return X, pd.Series(X["feriado"].values > 0, index=idx)


# --------------------------------------------------------------------------- #
# Ajuste / seleção / previsão
# --------------------------------------------------------------------------- #
def ajustar(z, X, order, sorder):
    return SARIMAX(
        z, exog=X, order=order, seasonal_order=sorder,
        trend="c" if order[1] == 0 else "n",
        enforce_stationarity=False, enforce_invertibility=False,
    ).fit(disp=False, maxiter=200)


def selecionar(y: pd.Series, X: pd.DataFrame | None) -> dict:
    log = base.usar_log(y)
    z = np.log1p(y) if log else y
    d, _ = base.escolher_d(z)
    melhor = None
    for p, q, P, Q in itertools.product(base.GRID_PQ, base.GRID_PQ, base.GRID_SPQ, base.GRID_SPQ):
        order, sorder = (p, d, q), (P, 0, Q, base.M)
        try:
            res = ajustar(z, X, order, sorder)
            ok = bool(res.mle_retvals.get("converged", True)) and np.isfinite(res.aic)
        except Exception:  # noqa: BLE001
            continue
        if ok and (melhor is None or res.aic < melhor["aic"]):
            melhor = {"order": order, "seasonal_order": sorder, "aic": float(res.aic), "log1p": bool(log)}
    return melhor


def prever(y_tr, X_tr, X_fut, cfg):
    z = np.log1p(y_tr) if cfg["log1p"] else y_tr
    res = ajustar(z, X_tr, cfg["order"], cfg["seasonal_order"])
    fc = res.get_forecast(len(X_fut) if X_fut is not None else cfg["_passos"], exog=X_fut)
    m, ic = fc.predicted_mean.values, fc.conf_int(alpha=base.ALPHA).values
    if cfg["log1p"]:
        m, ic = np.expm1(m), np.expm1(ic)
    return res, np.clip(m, 0, None), np.clip(ic[:, 0], 0, None), np.clip(ic[:, 1], 0, None)


def janela(serie, X, corte: int, passos: int, cols, cfg):
    tr, te = serie.iloc[:corte], serie.iloc[corte:corte + passos]
    X_tr = X.iloc[:corte][cols] if cols else None
    X_te = X.iloc[corte:corte + passos][cols] if cols else None
    cfg = {**cfg, "_passos": passos}
    res, p, lo, hi = prever(tr, X_tr, X_te, cfg)
    return tr, te, res, p, lo, hi


def resumo(df: pd.DataFrame) -> dict:
    """df: colunas real, prev, lo, hi, naive, rodada."""
    e, en = (df["real"] - df["prev"]).abs(), (df["real"] - df["naive"]).abs()
    por = df.assign(e=e, en=en).groupby("rodada")[["e", "en"]].mean()
    return {
        "mae": float(e.mean()),
        "mae_naive": float(en.mean()),
        "erro_relativo_naive": float(e.sum() / en.sum()),
        "rodadas": int(len(por)),
        "rodadas_vence_naive": int((por["e"] < por["en"]).sum()),
        "cobertura_ic95": float(((df["real"] >= df["lo"]) & (df["real"] <= df["hi"])).mean() * 100),
        "largura_ic95": float((df["hi"] - df["lo"]).mean()),
        "previsto_sobre_real_pct": float(df["prev"].sum() / df["real"].sum() * 100),
    }


def avaliar(nome, cols, serie, X, feriado) -> tuple[dict, pd.DataFrame]:
    t0 = time.time()
    n = len(serie)
    out = {"modelo": nome, "exogenas": cols}
    linhas = []

    # --- mesma estratégia do baseline: ordem escolhida com dados até o hold-out ---
    Xs = X[cols] if cols else None
    cfg1 = selecionar(serie.iloc[:-base.TEST_DAYS], Xs.iloc[:-base.TEST_DAYS] if cols else None)
    out["ordem_holdout"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg1.items()}
    print(f"  [{nome}] ordem hold-out: SARIMA{cfg1['order']}x{cfg1['seasonal_order']} AIC {cfg1['aic']:.1f}")

    tr, te, res, p, lo, hi = janela(serie, X, n - base.TEST_DAYS, base.TEST_DAYS, cols, cfg1)
    nv = base.naive_sazonal(tr, base.TEST_DAYS)
    ho = pd.DataFrame({"data": te.index, "real": te.values, "prev": p, "lo": lo, "hi": hi,
                       "naive": nv, "rodada": 0, "avaliacao": "holdout"})
    linhas.append(ho)
    m = base.metricas(te.values, p, lo, hi, tr)
    k = base.M + max(cfg1["order"][1], 1)
    lb = acorr_ljungbox(res.resid.iloc[k:], lags=[7, 14], return_df=True)["lb_pvalue"]
    out["holdout"] = {**resumo(ho), "mase": m["mase"], "rmsse": m["rmsse"],
                      "ljung_box_lag7_pvalue": float(lb.loc[7]), "ljung_box_lag14_pvalue": float(lb.loc[14]),
                      "shapiro_pvalue": float(stats.shapiro(res.resid.iloc[k:].values)[1])}
    if cols:
        ci = res.conf_int()
        out["coeficientes_holdout"] = {c: {"coef": float(res.params[c]), "ic_inf": float(ci.loc[c, 0]),
                                           "ic_sup": float(ci.loc[c, 1]), "p_valor": float(res.pvalues[c])}
                                       for c in cols}

    wf = []
    for i, kk in enumerate(range(base.N_FOLDS, 0, -1), start=1):
        tr, te, _, p, lo, hi = janela(serie, X, n - kk * base.HORIZON, base.HORIZON, cols, cfg1)
        wf.append(pd.DataFrame({"data": te.index, "real": te.values, "prev": p, "lo": lo, "hi": hi,
                                "naive": base.naive_sazonal(tr, base.HORIZON), "rodada": i,
                                "avaliacao": "walk_forward_4"}))
    wf = pd.concat(wf)
    linhas.append(wf)
    out["walk_forward_4"] = resumo(wf)

    # --- ano inteiro: ordem escolhida só com dados antes da 1ª rodada ---
    corte0 = n - N_FOLDS_ANO * base.HORIZON
    cfg2 = selecionar(serie.iloc[:corte0], Xs.iloc[:corte0] if cols else None)
    out["ordem_ano"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg2.items()}
    out["ordem_ano"]["treino_ate"] = str(serie.index[corte0 - 1].date())
    print(f"  [{nome}] ordem ano: SARIMA{cfg2['order']}x{cfg2['seasonal_order']} AIC {cfg2['aic']:.1f}")
    ano = []
    for i in range(N_FOLDS_ANO):
        corte = corte0 + i * base.HORIZON
        tr, te, _, p, lo, hi = janela(serie, X, corte, base.HORIZON, cols, cfg2)
        ano.append(pd.DataFrame({"data": te.index, "real": te.values, "prev": p, "lo": lo, "hi": hi,
                                 "naive": base.naive_sazonal(tr, base.HORIZON), "rodada": i + 1,
                                 "avaliacao": "ano_26"}))
    ano = pd.concat(ano)
    linhas.append(ano)
    out["ano_26_rodadas"] = resumo(ano)
    fer = ano["data"].map(feriado).values
    ea = (ano["real"] - ano["prev"]).abs()
    out["ano_26_rodadas"]["dias_feriado"] = int(fer.sum())
    out["ano_26_rodadas"]["mae_dias_feriado"] = float(ea[fer].mean())
    out["ano_26_rodadas"]["pct_erro_em_feriados"] = float(ea[fer].sum() / ea.sum() * 100)
    out["ano_26_rodadas"]["mae_dias_normais"] = float(ea[~fer].mean())

    corte_dez = int(np.searchsorted(serie.index, INICIO_DEZ))
    tr, te, _, p, lo, hi = janela(serie, X, corte_dez, 28, cols, cfg2)
    dez = pd.DataFrame({"data": te.index, "real": te.values, "prev": p, "lo": lo, "hi": hi,
                        "naive": base.naive_sazonal(tr, 28), "rodada": 0, "avaliacao": "dezembro"})
    linhas.append(dez)
    out["dezembro"] = resumo(dez)

    out["tempo_s"] = round(time.time() - t0, 1)
    prev = pd.concat(linhas)
    prev["modelo"] = nome
    return out, prev


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
def salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, nome), dpi=130)
    plt.close(fig)


def graficos(res: dict, prev: pd.DataFrame, X: pd.DataFrame, serie: pd.Series) -> dict:
    """Gera os gráficos 01–08 e devolve a importância RF/MDI das variáveis (vazio sem sklearn)."""
    importancia: dict = {}
    nomes = list(MODELOS)

    # 01 — erro relativo à regra simples em cada teste
    testes = [("holdout", "Fevereiro\n(teste principal)"), ("walk_forward_4", "4 rodadas\n(jan–fev)"),
              ("dezembro", "Dezembro"), ("ano_26_rodadas", "Ano inteiro\n(26 rodadas)")]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    w = 0.26
    for j, nm in enumerate(nomes):
        vals = [res[nm][t]["erro_relativo_naive"] * 100 for t, _ in testes]
        b = ax.bar(np.arange(len(testes)) + (j - 1) * w, vals, w, color=COR[nm], label=ROTULO[nm])
        ax.bar_label(b, fmt="%.0f%%", fontsize=8)
    ax.axhline(100, color=COR["naive"], ls="--", lw=1.5, label="regra simples = 100%")
    ax.set_xticks(np.arange(len(testes)), [t[1] for t in testes])
    ax.set_ylabel("erro do modelo ÷ erro da regra simples")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_title("Quanto menor, melhor. Abaixo de 100% = o modelo erra menos que repetir a semana passada")
    ax.legend(fontsize=8, loc="upper left")
    salvar(fig, "01_erro_relativo_por_teste.png")

    # 02 — fevereiro: previsões
    ho = prev[prev["avaliacao"] == "holdout"]
    fig, ax = plt.subplots(figsize=(13, 4.5))
    real = ho[ho["modelo"] == nomes[0]]
    ax.plot(real["data"], real["real"], color="#333", marker="o", ms=3, lw=1.2, label="venda real")
    for nm in nomes:
        d = ho[ho["modelo"] == nm]
        ax.plot(d["data"], d["prev"], color=COR[nm], lw=1.6, label=ROTULO[nm])
    for dia in pd.to_datetime(["2026-02-16", "2026-02-17"]):
        ax.axvspan(dia - pd.Timedelta(hours=12), dia + pd.Timedelta(hours=12), color="#f5b041", alpha=0.3)
    ax.text(pd.Timestamp("2026-02-16 12:00"), ax.get_ylim()[1] * 0.92, "Carnaval", ha="center", fontsize=9)
    ax.yaxis.set_major_formatter(FMT_MIL)
    ax.set_title("Fevereiro/2026: com calendário, o modelo sabe que a loja fecha no Carnaval")
    ax.legend(fontsize=8, loc="upper left")
    salvar(fig, "02_fevereiro_previsoes.png")

    # 03 — dezembro
    dz = prev[prev["avaliacao"] == "dezembro"]
    fig, ax = plt.subplots(figsize=(13, 4.5))
    real = dz[dz["modelo"] == nomes[0]]
    ax.bar(real["data"], real["real"], color="#bbb", label="venda real")
    for nm in nomes:
        d = dz[dz["modelo"] == nm]
        ax.plot(d["data"], d["prev"], color=COR[nm], lw=1.8, marker="o", ms=3,
                label=f"{ROTULO[nm]} — previu {res[nm]['dezembro']['previsto_sobre_real_pct']:.0f}% do vendido")
    ax.yaxis.set_major_formatter(FMT_MIL)
    ax.set_title("Dezembro/2025: calendário e clima não resolvem os picos de encomenda")
    ax.legend(fontsize=8, loc="upper right")
    salvar(fig, "03_dezembro_previsoes.png")

    # 04 — ano: erro relativo por rodada
    an = prev[prev["avaliacao"] == "ano_26"]
    fig, ax = plt.subplots(figsize=(13, 4.5))
    for nm in nomes:
        d = an[an["modelo"] == nm].assign(e=lambda x: (x.real - x.prev).abs(), en=lambda x: (x.real - x.naive).abs())
        g = d.groupby("rodada").agg(ini=("data", "min"), e=("e", "mean"), en=("en", "mean"))
        ax.plot(g["ini"], g["e"] / g["en"] * 100, marker="o", ms=4, color=COR[nm], label=ROTULO[nm])
    ax.axhline(100, color=COR["naive"], ls="--", lw=1.5, label="regra simples")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylabel("erro ÷ erro da regra simples (escala log)")
    ax.set_title("Ano inteiro (26 rodadas de 14 dias): abaixo da linha verde, o modelo ganhou naquela rodada")
    ax.legend(fontsize=8)
    salvar(fig, "04_ano_rodada_a_rodada.png")

    # 05 — feriados: erro médio em dias de feriado × dias normais (ano)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = np.arange(2)
    for j, nm in enumerate(nomes):
        a = res[nm]["ano_26_rodadas"]
        b = ax.bar(x + (j - 1) * w, [a["mae_dias_feriado"], a["mae_dias_normais"]], w, color=COR[nm], label=ROTULO[nm])
        ax.bar_label(b, fmt="%.0f", fontsize=8)
    ax.set_xticks(x, [f"feriados de seg a sáb\n({res[nomes[0]]['ano_26_rodadas']['dias_feriado']} dias, loja fechada)",
                      "demais dias"])
    ax.set_ylabel("erro médio (unidades/dia)")
    ax.set_title("Nos feriados o modelo sem calendário prevê venda com a loja fechada")
    ax.legend(fontsize=8)
    salvar(fig, "05_erro_em_feriados.png")

    # 06 — largura da faixa de segurança
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for j, nm in enumerate(nomes):
        vals = [res[nm][t]["largura_ic95"] for t, _ in testes]
        b = ax.bar(np.arange(len(testes)) + (j - 1) * w, vals, w, color=COR[nm], label=ROTULO[nm])
        ax.bar_label(b, labels=[f"{v / 1000:.0f}" for v in vals], fontsize=8)
    ax.set_xticks(np.arange(len(testes)), [t[1] for t in testes])
    ax.yaxis.set_major_formatter(FMT_MIL)
    ax.set_ylabel("largura média da faixa de 95% (unidades)")
    ax.set_title("Faixa de segurança: com o calendário ela fica ~6× mais estreita (os feriados a alargavam)")
    ax.legend(fontsize=8)
    salvar(fig, "06_largura_faixa_seguranca.png")

    # 07 — efeito estimado de cada variável (modelo B, ajuste do hold-out)
    coef = res["B_crua_calendario_clima"].get("coeficientes_holdout", {})
    if coef:
        escala = {"chuva_dia": np.log1p(10), "chuva_7d": np.log1p(50) - np.log1p(10), "temp_max": 5.0}
        nomes_leg = {"feriado": "feriado (seg–sáb)", "vespera_feriado": "véspera de feriado",
                     "pos_feriado": "dia após feriado", "inicio_mes": "dias 1–7 do mês",
                     "chuva_dia": "chuva de 10 mm no dia", "chuva_7d": "50 mm em 7 dias (vs 10)",
                     "temp_max": "+5 °C na máxima"}
        nomes_leg.update({f"antes_{v}": f"7 dias até {k}" for k, v in DATAS.items()})
        # Dia das Mães e Finados: a janela inclui o próprio dia, em que a loja abre
        # excepcionalmente (domingo/feriado com venda). O efeito vem quase todo daí.
        for v in ("maes", "finados"):
            nomes_leg[f"antes_{v}"] += " *"
        nomes_leg.update({f"dia_{d}": f"{d} (vs domingo)" for d in DIAS})
        linhas = []
        for c, v in coef.items():
            if c.startswith("dia_"):
                continue  # dia da semana vs domingo fechado: efeito enorme e óbvio, polui o gráfico
            s = escala.get(c, 1.0)
            linhas.append((nomes_leg.get(c, c), np.expm1(v["coef"] * s) * 100,
                           np.expm1(v["ic_inf"] * s) * 100, np.expm1(v["ic_sup"] * s) * 100, v["p_valor"]))
        dfc = pd.DataFrame(linhas, columns=["var", "ef", "lo", "hi", "p"]).sort_values("ef")
        fig, ax = plt.subplots(figsize=(10, 6))
        cores = ["#c0392b" if p < 0.05 else "#bbbbbb" for p in dfc["p"]]
        ax.barh(dfc["var"], dfc["ef"], color=cores)
        ax.errorbar(dfc["ef"], dfc["var"], xerr=[dfc["ef"] - dfc["lo"], dfc["hi"] - dfc["ef"]],
                    fmt="none", ecolor="#555", lw=0.8, capsize=2)
        ax.axvline(0, color="#333", lw=0.8)
        ax.set_xscale("symlog", linthresh=100)
        ax.xaxis.set_major_formatter(mtick.PercentFormatter())
        ax.set_xlabel("efeito estimado na venda do dia (vermelho = efeito confiável, p < 0,05)\n"
                      "* quase todo o efeito vem do próprio dia: a loja abre num domingo/feriado em que "
                      "estaria fechada")
        ax.set_title("O que cada informação muda na venda, segundo o modelo B")
        salvar(fig, "07_efeito_de_cada_variavel.png")

    # 08 — importância por floresta aleatória (MDI), como o projeto prevê
    try:
        from sklearn.ensemble import RandomForestRegressor
        tr = serie.iloc[:-base.TEST_DAYS]
        cols = MODELOS["B_crua_calendario_clima"]
        rf = RandomForestRegressor(n_estimators=400, min_samples_leaf=5, random_state=42, n_jobs=-1)
        rf.fit(X.loc[tr.index, cols], np.log1p(tr.values))
        imp = pd.Series(rf.feature_importances_, index=cols).sort_values()
        importancia = {k: float(v) for k, v in imp.sort_values(ascending=False).items()}
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.barh(imp.index, imp.values * 100,
                color=["#c0392b" if c in COLS_CLIMA else "#2e86c1" for c in imp.index])
        ax.xaxis.set_major_formatter(mtick.PercentFormatter())
        ax.set_title("Peso de cada variável para explicar a venda (floresta aleatória)\nazul = calendário · vermelho = clima")
        salvar(fig, "08_importancia_variaveis_rf.png")
    except ImportError:
        pass
    return importancia


# --------------------------------------------------------------------------- #
def main() -> None:
    os.makedirs(PLOTS_DIR, exist_ok=True)
    serie, info = base.carregar_serie()
    X, feriado = montar_exogenas(serie.index)
    if "--so-graficos" in sys.argv:
        with open(os.path.join(METRICS_DIR, f"{NOME}.json"), encoding="utf-8") as fh:
            res = json.load(fh)["modelos"]
        prev = pd.read_csv(os.path.join(METRICS_DIR, f"{NOME}_previsoes.csv"), sep=";", decimal=",",
                           parse_dates=["data"])
        graficos(res, prev, X, serie)
        return
    print(f"[serie] {info['inicio']} → {info['fim']} · {len(serie)} dias · exógenas {X.shape[1]}")

    res, prevs = {}, []
    for nome, cols in MODELOS.items():
        print(f"[modelo] {nome} ({len(cols)} exógenas)")
        r, p = avaliar(nome, cols, serie, X, feriado)
        res[nome] = r
        prevs.append(p)
        for t in ("holdout", "walk_forward_4", "dezembro", "ano_26_rodadas"):
            a = r[t]
            print(f"    {t:16s} erro/regra {a['erro_relativo_naive']:.2f} · vence {a['rodadas_vence_naive']}/{a['rodadas']}"
                  f" · MAE {a['mae']:.0f} · IC95 {a['cobertura_ic95']:.0f}% larg {a['largura_ic95'] / 1000:.0f} mil")
    prev = pd.concat(prevs)
    importancia = graficos(res, prev, X, serie)

    saida = {
        "experimento": NOME,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "serie": info,
        "exogenas": {"calendario": COLS_CAL, "clima": COLS_CLIMA,
                     "fechamentos_locais": FECHAMENTOS_LOCAIS,
                     "aviso_clima": "teste usa clima observado (previsão perfeita) — teto do ganho"},
        "modelos": res,
        "importancia_rf_mdi": importancia,
    }
    with open(os.path.join(METRICS_DIR, f"{NOME}.json"), "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2)
    prev.to_csv(os.path.join(METRICS_DIR, f"{NOME}_previsoes.csv"), sep=";", decimal=",", index=False)
    X.to_csv(os.path.join(METRICS_DIR, f"{NOME}_exogenas.csv"), sep=";", decimal=",", index_label="data")
    print(f"[saida] {os.path.join(METRICS_DIR, NOME + '.json')}")


if __name__ == "__main__":
    main()
