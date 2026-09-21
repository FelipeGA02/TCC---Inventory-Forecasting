"""EDA 2 — Análise da série-alvo do L1: `unidade` (2 séries).

**Decisão de 2026-09-21 (ADR-011), fundamentada em `eda_separacao.py`:** separar por
unidade tem apoio nos dados (Itabirito ganha 17–11% de MASE com modelo próprio; a soma
dos dois modelos de unidade bate o modelo do total da rede); separar por categoria dentro
da unidade **não** tem — nenhuma das 3 categorias ganha o mínimo exigido, e a soma das 3
fica a menos de 5% do modelo da unidade. O L1 passa de **6 séries** (`unidade ×
categoria`) para **2 séries** (`unidade`); `categoria` (e, dentro dela, `categoria_fina` e
SKU) passam a ser níveis de desagregação — o mesmo método de participação móvel × perfil
de dia-da-semana que a L2 já usava para SKU, agora também entre `unidade` e `categoria`
(ver `eda_series.py`, que documenta essa camada).

Reaproveita a mesma bateria de diagnóstico do antigo alvo (`eda_series.analisa_serie`) —
densidade, distribuição, sazonalidade semanal/anual, efeito de datas, tendência,
estacionariedade, autocorrelação, outliers — agora sobre as 2 séries que o SARIMAX do L1
de fato vai ajustar.

Saídas: PNGs `16_series_l1_unidade.png` a `19_stl_unidade.png` em results/plots/eda/ e
results/metrics/eda_series_unidade.json
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from . import _common as C
from .eda_series import analisa_serie

warnings.filterwarnings("ignore")


def analisa_unidade(df: pd.DataFrame, unidade: str) -> dict:
    s = C.serie_unidade(df, unidade, span="par")
    df_u = df[(df["unidade"] == unidade) & (df["categoria"] != C.NAO_PRODUTO)]
    return analisa_serie(s, df_u)


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
def graficos(series: dict[str, pd.Series], plt) -> list[str]:
    figs = []
    unidades = list(series)
    dias_pt = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

    # 16. Série diária + média móvel 28d — as 2 séries que o SARIMAX do L1 ajusta
    fig, axes = plt.subplots(1, len(unidades), figsize=(7 * len(unidades), 3.6), sharey=False)
    for ax, u in zip(np.atleast_1d(axes), unidades):
        s = series[u]
        ax.plot(s.index, s.values, lw=.5, color="#B0BEC5")
        ax.plot(s.index, s.rolling(28, min_periods=7).mean(), lw=1.6, color=C.PALETA.get(u, "#333"))
        ax.set_title(f"{u}  (CV={s.std()/s.mean():.2f})", fontsize=10)
    fig.suptitle("Série diária do L1 (cinza) + média móvel 28d — as 2 séries `unidade` "
                 "que o SARIMAX ajusta")
    fig.tight_layout()
    figs.append(C.savefig(fig, "16_series_l1_unidade.png"))

    # 17. Perfil de dia da semana + perfil mensal, lado a lado
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6))
    for u in unidades:
        s = series[u]
        by_dow = s.groupby(s.index.weekday).mean().reindex(range(7)) / s.mean()
        ax1.plot(dias_pt, by_dow.values, marker="o", lw=1.4, label=u, color=C.PALETA.get(u, "#333"))
        by_mes = s.groupby(s.index.month).mean().reindex(range(1, 13)) / s.mean()
        ax2.plot(range(1, 13), by_mes.values, marker="o", lw=1.4, label=u, color=C.PALETA.get(u, "#333"))
    ax1.axhline(1, color="#999", lw=.8, ls=":")
    ax1.set_title("Índice por dia da semana"); ax1.set_ylabel("demanda relativa (1.0 = média)")
    ax1.legend(frameon=False, fontsize=8)
    ax2.axhline(1, color="#999", lw=.8, ls=":")
    ax2.axvline(5, color="#B71C1C", lw=.7, ls="--", alpha=.5)
    ax2.axvline(11, color="#B71C1C", lw=.7, ls="--", alpha=.5)
    ax2.set_title("Índice por mês (tracejado vermelho: maio / nov)"); ax2.set_xlabel("mês")
    ax2.legend(frameon=False, fontsize=8)
    fig.suptitle("Séries `unidade` — perfil semanal e mensal")
    fig.tight_layout()
    figs.append(C.savefig(fig, "17_perfil_semanal_mensal_unidade.png"))

    # 18. ACF + distribuição (histograma), 2 unidades × 2 métricas
    from statsmodels.graphics.tsaplots import plot_acf
    fig, axes = plt.subplots(2, len(unidades), figsize=(7 * len(unidades), 7))
    for j, u in enumerate(unidades):
        s = series[u]
        plot_acf(s.astype(float).values, lags=21, ax=axes[0, j], alpha=.05)
        axes[0, j].set_title(f"ACF — {u}", fontsize=10)
        axes[1, j].hist(s.values, bins=40, color=C.PALETA.get(u, "#333"), alpha=.8)
        axes[1, j].axvline(s.mean(), color="#000", lw=1, ls="--")
        axes[1, j].set_title(f"Distribuição da qtd. diária — {u}", fontsize=10)
    fig.suptitle("Séries `unidade` — autocorrelação (linha 1) e distribuição (linha 2)")
    fig.tight_layout()
    figs.append(C.savefig(fig, "18_acf_dist_unidade.png"))

    # 19. STL — decomposição das 2 séries lado a lado (aqui dá para mostrar as duas
    # inteiras, ao contrário do nível categoria onde só a mais densa era exibida)
    from statsmodels.tsa.seasonal import STL
    fig, axes = plt.subplots(4, len(unidades), figsize=(7 * len(unidades), 9), sharex="col")
    for j, u in enumerate(unidades):
        s = series[u].astype(float)
        res = STL(s, period=7, robust=True).fit()
        for i, (comp, nome) in enumerate(zip(
                [res.observed, res.trend, res.seasonal, res.resid],
                ["observado", "tendência", "sazonal (m=7)", "resíduo"])):
            axes[i, j].plot(s.index, comp, lw=.8, color="#37474F")
            if j == 0:
                axes[i, j].set_ylabel(nome)
        axes[0, j].set_title(u, fontsize=10)
    fig.suptitle("Decomposição STL das 2 séries-alvo do L1")
    fig.tight_layout()
    figs.append(C.savefig(fig, "19_stl_unidade.png"))

    return figs


# --------------------------------------------------------------------------- #
def main() -> dict:
    plt = C.setup_plotting()
    df = C.load_transacoes()
    unidades = [u for u in C.UNIDADES if u in set(df["unidade"])]
    series = {u: C.serie_unidade(df, u, span="par") for u in unidades}

    por_unidade = {u: analisa_unidade(df, u) for u in unidades}

    resultado = {
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "nota": "L1 = 2 séries por unidade (ADR-011, 2026-09-21); categoria e SKU são "
                "obtidos por desagregação (eda_series.py e o L2 original).",
        "n_series_l1": len(unidades),
        "por_unidade": por_unidade,
    }

    resumo = []
    for u, r in por_unidade.items():
        resumo.append({
            "unidade": u,
            "dias_com_venda": r["1_densidade"]["dias_com_venda"],
            "pct_dias_com_venda": round(r["1_densidade"]["pct_dias_com_venda"], 1),
            "cv": round(r["2_distribuicao"]["cv"], 2) if r["2_distribuicao"]["cv"] else None,
            "log1p": r["2_distribuicao"]["aplicar_log1p"],
            "Fs_semanal": round(r["3_sazonalidade_semanal"]["forca_sazonal_semanal"], 2)
            if r["3_sazonalidade_semanal"]["forca_sazonal_semanal"] is not None else None,
            "sugestao_d": r["6_estacionariedade"]["sugestao_d"],
            "acf_lag7": round(r["7_autocorrelacao"]["acf_lag7"], 2)
            if r["7_autocorrelacao"]["acf_lag7"] is not None else None,
            "veredito": r["9_veredito_sarimax"]["nivel"],
        })
    resultado["sumario"] = resumo
    resultado["graficos"] = graficos(series, plt)
    path = C.dump_metrics("eda_series_unidade.json", resultado)

    print(f"[eda_series_unidade] {len(unidades)} séries L1 (uma por unidade)")
    print(f"[eda_series_unidade] {'unidade':<18}{'d.venda':>8}{'%d':>6}{'CV':>7}{'log1p':>7}"
          f"{'Fs':>6}{'d':>3}{'acf7':>7}  veredito")
    for r in resumo:
        print(f"[eda_series_unidade] {r['unidade']:<18}{r['dias_com_venda']:>8}{r['pct_dias_com_venda']:>6}"
              f"{r['cv']!s:>7}{str(r['log1p']):>7}{r['Fs_semanal']!s:>6}{r['sugestao_d']:>3}"
              f"{r['acf_lag7']!s:>7}  {r['veredito']}")
    print(f"[eda_series_unidade] métricas: {path}  ·  {len(resultado['graficos'])} gráficos")
    return resultado


if __name__ == "__main__":
    main()
