"""O teste ADF: o que ele responde, o que não responde, e o que d = 1 resolveu.

Gera os gráficos 13 e 14, que sustentam a etapa 03 do artefato do A0-crua:

  13_adf_o_que_o_teste_ve.png
     (a) a distribuição de Dickey-Fuller simulada sob a hipótese nula (passeio aleatório com
         constante, mesmo n do treino) contra a normal padrão, com os valores críticos de 5% de
         cada uma e a estatística observada na série do A0-crua (log1p do treino). É o achado
         central de Dickey & Fuller (1979): sob raiz unitária, a estatística t de γ não segue a t.
     (b) a pergunta que o teste não faz: a mediana móvel de 28 dias abertos contra a mediana do
         histórico. Com d = 0 a previsão volta para essa linha; set–dez/2025 ficou acima dela.

  14_adf_d0_d1_dezembro.png
     (a) esquema: depois de uma mudança de nível, d = 0 volta para a média antiga e d = 1 parte
         do nível atual (AR(1) sintético, só para mostrar a mecânica).
     (b, c) dezembro/2025 por loja, venda de balcão real contra A1 (d escolhido pelo ADF → 0)
         e A1 d = 1, lidos de `l1_por_loja_eda_previsoes.csv` (não refaz o treino).

Uso (a partir de `ia-predictor/`, depois de `baseline.sarimax_l1_por_loja`):
    python -m training_scripts.baseline.analise_adf
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import adfuller

from training_scripts.baseline import sarimax_serie_crua as base

PREVISOES_L1 = os.path.join(base.METRICS_DIR, "l1_por_loja_eda_previsoes.csv")
N_SIM = 20_000
SEMENTE = 42

COR_DF = "#3a6ea5"
COR_NORMAL = "#8e8e8e"
COR_OBS = "#b23c2e"
COR_REAL = "#333333"
COR_D0 = "#2e86c1"
COR_D1 = "#8e44ad"

FMT_MIL = mtick.FuncFormatter(
    lambda v, _: f"{v / 1000:.1f} mil".replace(".0 mil", " mil").replace(".", ",") if abs(v) >= 1000 else f"{v:.0f}"
)


def virgula(v: float, casas: int = 2) -> str:
    return f"{v:.{casas}f}".replace(".", ",")


def simular_tau_df(n: int, n_sim: int, semente: int) -> np.ndarray:
    """Estatística τ = γ̂ / ep(γ̂) da regressão Δy = α + γ·y₋₁ + ε, com y passeio aleatório."""
    rng = np.random.default_rng(semente)
    y = np.cumsum(rng.standard_normal((n_sim, n + 1)), axis=1)
    dy, ylag = np.diff(y, axis=1), y[:, :-1]
    xm = ylag - ylag.mean(axis=1, keepdims=True)
    ym = dy - dy.mean(axis=1, keepdims=True)
    sxx = (xm ** 2).sum(axis=1)
    gamma = (xm * ym).sum(axis=1) / sxx
    resid = ym - gamma[:, None] * xm
    s2 = (resid ** 2).sum(axis=1) / (n - 2)
    return gamma / np.sqrt(s2 / sxx)


def figura_teste(serie: pd.Series, z: pd.Series) -> str:
    tau, p, lags, nobs, crit, _ = adfuller(z, autolag="AIC")
    taus = simular_tau_df(nobs, N_SIM, SEMENTE)
    crit_sim = float(np.quantile(taus, 0.05))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={"width_ratios": [1, 1.25]})

    # (a) Distribuição de Dickey-Fuller × normal
    grade = np.linspace(-7, 4, 400)
    ax1.hist(taus, bins=120, density=True, color=COR_DF, alpha=.55,
             label=f"Dickey-Fuller\n(simulada, {N_SIM // 1000} mil\npasseios aleatórios)")
    ax1.plot(grade, stats.norm.pdf(grade), color=COR_NORMAL, lw=1.6,
             label="normal\n(o que o teste t\ncomum assume)")
    ax1.axvline(stats.norm.ppf(.05), color=COR_NORMAL, lw=1.2, ls="--")
    ax1.axvline(crit["5%"], color=COR_DF, lw=1.4, ls="--")
    ax1.axvline(tau, color=COR_OBS, lw=2)
    ymax = ax1.get_ylim()[1] * 1.35
    ax1.set_ylim(0, ymax)
    caixa = {"facecolor": "white", "edgecolor": "none", "alpha": .9, "pad": 1.5}
    ax1.text(stats.norm.ppf(.05) + .1, ymax * .97, f"limite t comum (5%)\n{virgula(stats.norm.ppf(.05))}",
             color=COR_NORMAL, fontsize=8, va="top", bbox=caixa)
    ax1.text(crit["5%"] - .1, ymax * .97, f"limite Dickey-Fuller (5%)\n{virgula(crit['5%'])}",
             color=COR_DF, fontsize=8, va="top", ha="right", bbox=caixa)
    ax1.text(tau + .08, ymax * .55, f"A0-crua\nτ = {virgula(tau)}\np = 7,0×10⁻⁸",
             color=COR_OBS, fontsize=9, va="top", fontweight="bold")
    ax1.set_xlim(-7, 4)
    ax1.set_xlabel("estatística τ = γ̂ / erro-padrão")
    ax1.set_yticks([])
    ax1.set_title("(a) A pergunta do ADF: a série anda sem rumo?", fontsize=11)
    ax1.legend(fontsize=8, frameon=False, loc="upper right", bbox_to_anchor=(1, .8))

    # (b) Fases de nível que o teste não enxerga
    abertos = serie[(serie.index.weekday < 6) & (serie > 0)]
    nivel = abertos.rolling(28, min_periods=14).median()
    ref = float(abertos.loc[: z.index.max()].median())
    ax2.plot(abertos.index, abertos.values, lw=.4, color="#c9ced6", label="venda por dia aberto")
    ax2.plot(nivel.index, nivel.values, lw=2, color=COR_REAL, label="nível recente (mediana de 28 dias abertos)")
    ax2.axhline(ref, color=COR_D0, lw=1.4, ls="--", label=f"nível médio do histórico ({FMT_MIL(ref, None)})")
    ax2.fill_between(nivel.index, ref, nivel.values, where=nivel.values > ref, color=COR_OBS, alpha=.15, lw=0)
    ax2.fill_between(nivel.index, ref, nivel.values, where=nivel.values < ref, color=COR_D0, alpha=.10, lw=0)
    ax2.axvspan(pd.Timestamp("2025-09-01"), pd.Timestamp("2025-12-31"), color="#f4d03f", alpha=.18, lw=0)
    ax2.text(pd.Timestamp("2025-09-05"), 13_500, "temporada alta\nset–dez/2025", fontsize=8, va="top")
    ax2.set_ylim(0, 14_000)
    ax2.yaxis.set_major_formatter(FMT_MIL)
    loc = mdates.MonthLocator(bymonth=(1, 4, 7, 10))
    ax2.xaxis.set_major_locator(loc)
    ax2.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))
    ax2.set_ylabel("unidades / dia (eixo cortado em 14 mil)")
    ax2.set_title("(b) A pergunta que importava: o nível de agora é o de sempre?", fontsize=11)
    ax2.legend(fontsize=8, frameon=False, loc="upper left")

    fig.suptitle(
        f"ADF rejeita a raiz unitária com folga (τ {virgula(tau)} contra limite {virgula(crit['5%'])}, "
        f"{lags} defasagens por AIC) — e mesmo assim o nível muda por fases",
        fontsize=11,
    )
    fig.tight_layout()
    caminho = os.path.join(base.PLOTS_DIR, "13_adf_o_que_o_teste_ve.png")
    fig.savefig(caminho, dpi=130)
    plt.close(fig)
    print(f"[analise_adf] τ {tau:.3f} · p {p:.2e} · lags {lags} · nobs {nobs} · crit5% {crit['5%']:.3f} "
          f"(simulado {crit_sim:.3f}) · normal {stats.norm.ppf(.05):.3f}")
    print(f"[analise_adf] {caminho}")
    return caminho


def figura_solucao() -> str:
    prev = pd.read_csv(PREVISOES_L1, sep=";", decimal=",", encoding="utf-8", parse_dates=["data"])
    dez = prev[prev["avaliacao"] == "dezembro"]

    fig, axes = plt.subplots(3, 1, figsize=(13, 11), gridspec_kw={"height_ratios": [.85, 1, 1]})

    # (a) Esquema: AR(1) com mudança de nível
    rng = np.random.default_rng(7)
    n_hist, n_prev, phi = 60, 30, .6
    nivel = np.r_[np.full(40, 100.0), np.full(20, 140.0)]
    y = np.empty(n_hist)
    y[0] = nivel[0]
    for t in range(1, n_hist):
        y[t] = nivel[t] + phi * (y[t - 1] - nivel[t - 1]) + rng.normal(0, 6)
    media = y.mean()
    h = np.arange(1, n_prev + 1)
    d0 = media + (y[-1] - media) * phi ** h
    d1 = np.full(n_prev, y[-15:].mean())
    t_hist, t_prev = np.arange(n_hist), np.arange(n_hist, n_hist + n_prev)
    ax = axes[0]
    ax.plot(t_hist, y, color=COR_REAL, lw=1.6, label="histórico")
    ax.plot(t_prev, np.full(n_prev, 140.0), color=COR_REAL, lw=1, ls=":", label="o que de fato veio")
    ax.axhline(media, color=COR_D0, lw=.8, ls="--", alpha=.6)
    ax.plot(t_prev, d0, color=COR_D0, lw=2.2, label="d = 0: volta para a média do histórico")
    ax.plot(t_prev, d1, color=COR_D1, lw=2.2, label="d = 1: parte do nível de agora")
    ax.axvline(n_hist - .5, color="#999", lw=.8)
    ax.text(n_hist + .5, media - 3, "média do histórico", color=COR_D0, fontsize=8, va="top")
    ax.text(41, 92, "o nível sobe aqui", fontsize=8, color="#555")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("(a) Esquema: o que cada escolha faz depois de uma mudança de nível", fontsize=11)
    ax.legend(fontsize=8, frameon=False, loc="lower right", ncol=2)

    # (b, c) Dezembro real por loja
    for ax, unidade in zip(axes[1:], ["Jardim Canadá", "Itabirito"]):
        d = dez[dez["unidade"] == unidade]
        real = d[d["variante"] == "A1_eda"].set_index("data")["real_balcao"]
        p0 = d[d["variante"] == "A1_eda"].set_index("data")["prev"]
        p1 = d[d["variante"] == "A1_eda_d1"].set_index("data")["prev"]
        aberto = real.index.weekday < 6
        pct0, pct1 = p0.sum() / real.sum() * 100, p1.sum() / real.sum() * 100
        ax.bar(real.index, real.values, width=.8, color="#d5d8dc", label="venda de balcão real")
        ax.plot(p0.index[aberto], p0.values[aberto], "o-", ms=3, lw=1.6, color=COR_D0,
                label=f"A1 com d = 0 (ADF) — previu {virgula(pct0, 0)}% do vendido")
        ax.plot(p1.index[aberto], p1.values[aberto], "o-", ms=3, lw=1.6, color=COR_D1,
                label=f"A1 com d = 1 — previu {virgula(pct1, 0)}% do vendido")
        ax.yaxis.set_major_formatter(FMT_MIL)
        ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=(1, 8, 15, 22)))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
        ax.set_title(f"({'b' if unidade == 'Jardim Canadá' else 'c'}) {unidade} — dezembro de 2025, "
                     f"balcão (sem encomendas)", fontsize=11)
        ax.legend(fontsize=8, frameon=False, loc="upper right")

    fig.suptitle("A solução: d = 1 faz a previsão partir do nível atual — em dezembro, menos venda "
                 "fica sem previsão nas duas lojas", fontsize=11)
    fig.tight_layout()
    caminho = os.path.join(base.PLOTS_DIR, "14_adf_d0_d1_dezembro.png")
    fig.savefig(caminho, dpi=130)
    plt.close(fig)
    print(f"[analise_adf] {caminho}")
    return caminho


def main() -> None:
    serie, _ = base.carregar_serie()
    treino = serie.iloc[: -base.TEST_DAYS]
    figura_teste(serie, np.log1p(treino))
    figura_solucao()


if __name__ == "__main__":
    main()
