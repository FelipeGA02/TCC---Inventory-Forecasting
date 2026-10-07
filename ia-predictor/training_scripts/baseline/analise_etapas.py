"""Gráficos de apoio às etapas 01, 04, 05, 07 e 09 do artefato do A0-crua.

Cada figura ilustra a decisão metodológica de uma etapa com os dados do próprio projeto:

  15_estrutura_e_modelos.png   (01) a memória que o SARIMA modela (ACF da série em log1p,
                               picos em 1 e 7) e os modelos já comparados no mesmo protocolo
                               (26 rodadas, erro relativo à regra simples por loja).
  16_sazonalidade_D.png        (04) o perfil de dia da semana é estável trimestre a trimestre
                               (sazonalidade determinística) e o que D = 1 faria: a ACF da série
                               diferenciada em 7 dias ganha o pico negativo em 7 típico de
                               diferenciação em excesso, e a variação dia a dia aumenta.
  17_grid_aic.png              (05) as 36 ordens do grid ordenadas por AIC, e o AIC desmontado em
                               ajuste (−2·log L) e penalidade (2k).
  18_esquema_avaliacao.png     (06/07) hold-out e as 4 rodadas de walk-forward numa linha do
                               tempo.
  19_ljung_box_corrigido.png   (09) p-valores do Ljung-Box nos defasamentos 1–28, com e sem
                               descontar os 4 parâmetros ARMA dos graus de liberdade.

Uso (a partir de `ia-predictor/`; o grid leva ~2,5 min):
    python -m training_scripts.baseline.analise_etapas
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import acf

from training_scripts.baseline import sarimax_serie_crua as base

L1_JSON = os.path.join(base.METRICS_DIR, "l1_por_loja_eda.json")
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
COR = {"azul": "#3a6ea5", "roxo": "#8e44ad", "cinza": "#8e8e8e", "verm": "#b23c2e",
       "verde": "#1e8449", "laranja": "#e67e22", "escuro": "#333333"}


def virgula(v: float, casas: int = 2) -> str:
    return f"{v:.{casas}f}".replace(".", ",")


def salvar(fig, nome: str) -> str:
    caminho = os.path.join(base.PLOTS_DIR, nome)
    fig.savefig(caminho, dpi=130)
    plt.close(fig)
    print(f"[analise_etapas] {caminho}")
    return caminho


def barras_acf(ax, valores, n, cor, titulo):
    lags = np.arange(1, len(valores))
    ax.bar(lags, valores[1:], width=.6, color=cor)
    banda = 1.96 / np.sqrt(n)
    ax.axhspan(-banda, banda, color="#000", alpha=.07, lw=0)
    ax.axhline(0, color="#000", lw=.6)
    for k in (7, 14, 21, 28):
        ax.axvline(k, color="#999", lw=.6, ls=":")
    ax.set_xlabel("defasagem (dias)")
    ax.set_title(titulo, fontsize=10.5)


# --------------------------------------------------------------------------- #
# 01 — estrutura e modelos comparados
# --------------------------------------------------------------------------- #
def fig_estrutura(z: pd.Series) -> None:
    with open(L1_JSON, encoding="utf-8") as f:
        l1 = json.load(f)["resultados"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4.8), gridspec_kw={"width_ratios": [1.2, 1]})

    barras_acf(ax1, acf(z, nlags=28), len(z), COR["azul"],
               "(a) A memória que o SARIMA modela: correlação da venda com dias anteriores")
    ax1.set_ylabel("correlação (log1p)")
    ax1.annotate("ontem: quase nada", (1, acf(z, nlags=1)[1]), (2, .45), fontsize=8,
                 arrowprops={"arrowstyle": "-", "lw": .6})
    ax1.annotate("mesmo dia da\nsemana passada", (7, acf(z, nlags=7)[7]), (9.5, .62), fontsize=8,
                 arrowprops={"arrowstyle": "-", "lw": .6})

    variantes = [("HW_eda", "Holt-Winters"), ("A0_eda", "SARIMA\n(sem calendário)"),
                 ("A1_eda", "SARIMAX\n+ calendário"), ("A1_eda_d1", "SARIMAX\n+ calendário, d = 1")]
    lojas = ["Jardim Canadá", "Itabirito"]
    x = np.arange(len(variantes))
    for j, (loja, cor) in enumerate(zip(lojas, [COR["azul"], COR["laranja"]])):
        vals = [l1[loja][v]["ano_26"]["erro_relativo_naive"] for v, _ in variantes]
        venc = [l1[loja][v]["ano_26"]["rodadas_vence_naive"] for v, _ in variantes]
        barras = ax2.bar(x + (j - .5) * .38, vals, width=.36, color=cor, label=loja)
        for b, v, n in zip(barras, vals, venc):
            ax2.text(b.get_x() + b.get_width() / 2, v + .015, f"{virgula(v)}\n{n}/26", ha="center", fontsize=7.5)
    ax2.axhline(1, color=COR["verde"], lw=1.2, ls="--")
    ax2.text(len(variantes) - .5, 1.01, "regra simples (= 1)", color=COR["verde"], fontsize=8, ha="right", va="bottom")
    ax2.set_xticks(x, [r for _, r in variantes], fontsize=8)
    ax2.set_ylim(0, 1.2)
    ax2.set_ylabel("erro ÷ erro da regra simples")
    ax2.set_title("(b) Modelos já comparados: 26 rodadas, 1 ano, por loja\n(menor é melhor; número de baixo = rodadas vencidas)",
                  fontsize=10.5)
    ax2.legend(fontsize=8, frameon=False, loc="upper left")
    fig.tight_layout()
    salvar(fig, "15_estrutura_e_modelos.png")


# --------------------------------------------------------------------------- #
# 04 — D = 0
# --------------------------------------------------------------------------- #
def fig_sazonalidade(serie: pd.Series, z: pd.Series) -> dict:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))

    # (a) perfil semanal por trimestre: a forma se repete
    df = pd.DataFrame({"y": serie})
    df["tri"] = df.index.to_period("Q")
    df["dow"] = df.index.weekday
    abertos = df[df["y"] > 0]
    perfis = abertos.groupby(["tri", "dow"])["y"].median().unstack()
    perfis = perfis.div(perfis.loc[:, :5].mean(axis=1), axis=0)
    for tri, linha in perfis.iterrows():
        axes[0].plot(range(6), linha.values[:6], color=COR["azul"], alpha=.35, lw=1)
    axes[0].plot(range(6), perfis.median().values[:6], color=COR["escuro"], lw=2.4, label="mediana dos trimestres")
    axes[0].set_xticks(range(6), DIAS[:6])
    axes[0].set_ylabel("venda ÷ média seg–sáb do trimestre")
    axes[0].set_title(f"(a) O formato da semana se repete\n({len(perfis)} trimestres, um por linha azul; domingo = fechado)",
                      fontsize=10.5)
    axes[0].legend(fontsize=8, frameon=False)

    # (b) e (c): o que sobra com dummies × com D = 1
    media_dow = z.groupby(z.index.weekday).transform("mean")
    dummies = (z - media_dow).dropna()
    dif7 = z.diff(7).dropna()
    barras_acf(axes[1], acf(dummies, nlags=28), len(dummies), COR["verde"],
               f"(b) Tirando a média de cada dia da semana\n(desvio-padrão do que sobra: {virgula(dummies.std())})")
    barras_acf(axes[2], acf(dif7, nlags=28), len(dif7), COR["verm"],
               f"(c) Subtraindo a semana passada (D = 1)\n(desvio-padrão do que sobra: {virgula(dif7.std())})")
    lim = max(abs(np.r_[axes[1].get_ylim(), axes[2].get_ylim()]))
    for ax in axes[1:]:
        ax.set_ylim(-lim, lim)
    a7 = acf(dif7, nlags=7)[7]
    axes[2].annotate(f"pico negativo em 7: {virgula(a7)}\n(marca de diferenciação em excesso)", (7, a7),
                     (10, a7 * .9), fontsize=8, arrowprops={"arrowstyle": "-", "lw": .6})
    fig.tight_layout()
    salvar(fig, "16_sazonalidade_D.png")
    return {"sd_dummies": float(dummies.std()), "sd_dif7": float(dif7.std()), "acf7_dif7": float(a7),
            "acf7_dummies": float(acf(dummies, nlags=7)[7])}


# --------------------------------------------------------------------------- #
# 05 — grid AIC
# --------------------------------------------------------------------------- #
def fig_grid(z: pd.Series, d: int) -> tuple[pd.DataFrame, object]:
    linhas, melhor_res = [], None
    for p in base.GRID_PQ:
        for q in base.GRID_PQ:
            for P in base.GRID_SPQ:
                for Q in base.GRID_SPQ:
                    res = base.ajustar(z, (p, d, q), (P, 0, Q, base.M))
                    k = len(res.params)
                    linhas.append({"ordem": f"({p},{d},{q})({P},0,{Q})", "sazonal": f"({P},0,{Q})₇",
                                   "aic": res.aic, "m2ll": -2 * res.llf, "k": k,
                                   "ok": bool(res.mle_retvals.get("converged", True))})
                    if (p, q, P, Q) == (1, 1, 1, 1):
                        melhor_res = res
    g = pd.DataFrame(linhas).sort_values("aic").reset_index(drop=True)
    g["delta"] = g["aic"] - g["aic"].min()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.4), gridspec_kw={"width_ratios": [1.4, 1]})
    cores = {"(0,0,0)₇": "#bbbbbb", "(1,0,0)₇": COR["laranja"], "(0,0,1)₇": COR["verde"], "(1,0,1)₇": COR["azul"]}
    teto = 15
    ax1.bar(range(len(g)), g["delta"].clip(upper=teto), color=[cores[s] for s in g["sazonal"]])
    ax1.axhline(2, color=COR["verm"], lw=1, ls="--")
    fora = g[g["delta"] > teto]
    ax1.text(len(g) - 1, teto * .8, f"{len(fora)} ordens sem a parte sazonal (1,0,1)₇:\n"
             f"Δ entre {fora['delta'].min():.0f} e {fora['delta'].max():.0f}, fora da escala",
             fontsize=8, ha="right", va="top", bbox={"facecolor": "white", "edgecolor": "none", "alpha": .9})
    ax1.set_ylim(0, teto)
    ax1.set_xticks(range(len(g)), g["ordem"], rotation=90, fontsize=6.5)
    ax1.set_ylabel(f"Δ AIC em relação ao melhor (cortado em {teto})")
    ax1.set_title("(a) As 36 ordens do grid, da melhor para a pior", fontsize=10.5)
    ax1.legend(handles=[mpatches.Patch(color=c, label=f"parte sazonal {s}") for s, c in cores.items()]
               + [plt.Line2D([], [], color=COR["verm"], lw=1, ls="--", label="Δ = 2: abaixo, indistinguíveis")],
               fontsize=8, frameon=False, loc="upper left", bbox_to_anchor=(0, .9))

    top = g[g["sazonal"] == "(1,0,1)₇"].head(8)
    ax2.scatter(top["k"], top["m2ll"], s=36, color=[cores[s] for s in top["sazonal"]], zorder=3)
    for (_, r), dy in zip(top.head(3).iterrows(), (-12, 8, 8)):
        ax2.annotate(r["ordem"], (r["k"], r["m2ll"]), (6, dy), textcoords="offset points", fontsize=7.5)
    ks = np.linspace(top["k"].min() - .5, top["k"].max() + .5, 10)
    aic0 = g["aic"].min()
    for delta, estilo in [(0, "-"), (2, "--"), (10, ":")]:
        ax2.plot(ks, aic0 + delta - 2 * ks, color="#555", lw=.8, ls=estilo)
        ax2.text(ks[-1], aic0 + delta - 2 * ks[-1], f" AIC = melhor + {delta}", fontsize=7, va="center")
    ax2.set_xlabel("k = número de parâmetros")
    ax2.set_ylabel("−2·log L (menor = ajusta melhor)")
    ax2.set_title("(b) O AIC desmontado: ajuste contra penalidade\n(8 melhores; cada linha = mesmo AIC)", fontsize=10.5)
    fig.tight_layout()
    salvar(fig, "17_grid_aic.png")
    print(g.head(6).to_string())
    return g, melhor_res


# --------------------------------------------------------------------------- #
# 06/07 — esquema de avaliação
# --------------------------------------------------------------------------- #
def fig_esquema(serie: pd.Series) -> None:
    n = len(serie)
    idx = serie.index
    linhas = [("Hold-out (etapa 06)", n - base.TEST_DAYS, base.TEST_DAYS)]
    for i, k in enumerate(range(base.N_FOLDS, 0, -1), 1):
        corte = n - k * base.HORIZON
        linhas.append((f"Rodada {i} (etapa 07)", corte, base.HORIZON))
    fig, ax = plt.subplots(figsize=(13, 3.6))
    for y, (rot, corte, h) in enumerate(reversed(linhas)):
        ax.barh(y, (idx[corte - 1] - idx[0]).days, left=mdates.date2num(idx[0]), height=.55, color="#c9d6e8")
        ax.barh(y, h, left=mdates.date2num(idx[corte]), height=.55, color=COR["verm"])
        ax.text(mdates.date2num(idx[corte]) + h + 2, y, f"{idx[corte]:%d/%m} – {idx[corte + h - 1]:%d/%m/%Y}",
                va="center", fontsize=8)
    ax.set_yticks(range(len(linhas)), [r for r, _, _ in reversed(linhas)], fontsize=9)
    ax.xaxis_date()
    ax.set_xlim(mdates.date2num(idx[0]) - 5, mdates.date2num(idx[-1]) + 60)
    ax.legend(handles=[mpatches.Patch(color="#c9d6e8", label="dados que o modelo vê para aprender"),
                       mpatches.Patch(color=COR["verm"], label="dias que ele tem de prever sem ter visto")],
              fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(.5, -.12), ncol=2)
    ax.set_title("Como o modelo é avaliado: sempre treina no passado e prevê o futuro", fontsize=10.5)
    fig.tight_layout()
    salvar(fig, "18_esquema_avaliacao.png")


# --------------------------------------------------------------------------- #
# 09 — Ljung-Box com graus de liberdade corrigidos
# --------------------------------------------------------------------------- #
def fig_ljung_box(res, d: int) -> dict:
    resid = res.resid.iloc[max(d, 1) + base.M:]
    lags = np.arange(5, 29)
    sem = acorr_ljungbox(resid, lags=lags, return_df=True)["lb_pvalue"]
    com = acorr_ljungbox(resid, lags=lags, model_df=4, return_df=True)["lb_pvalue"]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.plot(lags, sem.values, "o-", ms=4, color=COR["cinza"], label="como no código: graus de liberdade = h")
    ax.plot(lags, com.values, "o-", ms=4, color=COR["azul"], label="corrigido (Ljung & Box): h − 4 parâmetros ARMA")
    ax.axhline(.05, color=COR["verm"], lw=1, ls="--")
    ax.text(28, .06, "p = 0,05", color=COR["verm"], fontsize=8, ha="right")
    for h in (7, 14):
        ax.axvline(h, color="#999", lw=.6, ls=":")
        ax.annotate(f"h={h}: {virgula(sem[h], 3)} → {virgula(com[h], 3)}", (h, com[h]), (h + .4, com[h] - .12),
                    fontsize=8, color=COR["azul"])
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("defasagem máxima testada (h)")
    ax.set_ylabel("p-valor do Ljung-Box")
    ax.set_title("Sobrou padrão nos erros? O p-valor cai com a correção, mas fica acima de 0,05 até h = 28 "
                 if (com > .05).all() else "Sobrou padrão nos erros? Com a correção, alguns defasamentos cruzam 0,05",
                 fontsize=10.5)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    fig.tight_layout()
    salvar(fig, "19_ljung_box_corrigido.png")
    out = {"lb7": float(sem[7]), "lb14": float(sem[14]), "lb7_corr": float(com[7]), "lb14_corr": float(com[14]),
           "min_corr": float(com.min()), "lag_min_corr": int(com.idxmin())}
    print(f"[analise_etapas] Ljung-Box {out}")
    return out


def main() -> None:
    serie, _ = base.carregar_serie()
    treino = serie.iloc[: -base.TEST_DAYS]
    z = np.log1p(treino)
    d, _ = base.escolher_d(z)

    fig_estrutura(z)
    print(f"[analise_etapas] sazonalidade {fig_sazonalidade(treino, z)}")
    fig_esquema(serie)
    _, res = fig_grid(z, d)
    fig_ljung_box(res, d)


if __name__ == "__main__":
    main()
