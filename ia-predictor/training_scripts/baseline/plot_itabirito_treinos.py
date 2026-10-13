"""Grafico dos dois treinos SARIMAX de Itabirito: a serie em log1p e as duas previsoes.

Tres paineis, cada um com UM eixo. A serie transformada e as previsoes em unidades nao
dividem escala: junta-las num painel so exigiria dois eixos y, que e o erro de leitura
mais comum em grafico de serie temporal.

  (a) a serie depois do log1p — o que o treino B enxerga;
  (b) a previsao operacional (h = 1) dos dois treinos contra o realizado, no periodo
      inteiro de validacao;
  (c) as ultimas 8 semanas com a faixa de 95% de cada treino, onde da para ler o dia a dia.

Cores: azul #3a6ea5 (sem log) e laranja #e67e22 (log1p), par validado para daltonismo
(dE 23,2 em protanopia). O azul/roxo usado antes no projeto reprovava (dE 1,2 em
deuteranopia, ou seja, indistinguivel). O realizado fica em cinza neutro, por ser
referencia e nao uma terceira categoria.

Uso (a partir de `ia-predictor/`, depois dos dois treinos):
    python -m training_scripts.baseline.plot_itabirito_treinos
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

from training_scripts.baseline.sarimax_itabirito_core import METRICS_DIR, serie_diaria

PLOTS_DIR = os.path.join(os.path.dirname(METRICS_DIR), "plots", "baseline")

COR_SEM_LOG = "#3a6ea5"
COR_LOG1P = "#e67e22"
COR_REAL = "#444444"
COR_GRID = "#d8dce1"
INK = "#15181d"
INK_FRACO = "#5a6471"

ZOOM_DIAS = 56          # 8 semanas
FMT_MIL = mtick.FuncFormatter(
    lambda v, _: f"{v / 1000:.0f} mil".replace(".", ",") if abs(v) >= 1000 else f"{v:.0f}")


def _operacional(nome: str) -> pd.DataFrame:
    """Serie h = 1 de um treino: a previsao feita com o modelo reajustado na vespera."""
    d = pd.read_csv(os.path.join(METRICS_DIR, f"{nome}_operacional.csv"), sep=";", decimal=".")
    d["data"] = pd.to_datetime(d["data"])
    return d.set_index("data").sort_index()


def _limpar(ax) -> None:
    """Grade e eixos recessivos: o dado e que tem de pesar na figura."""
    ax.grid(True, color=COR_GRID, lw=.6, alpha=.9)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(COR_GRID)
    ax.tick_params(colors=INK_FRACO, labelsize=9)


def main() -> None:
    os.makedirs(PLOTS_DIR, exist_ok=True)
    y = serie_diaria()
    a = _operacional("itabirito_sem_log")
    b = _operacional("itabirito_log1p")

    fig, axes = plt.subplots(3, 1, figsize=(13, 10.5))

    # ---------------------------------------------------------------- (a)
    z = np.log1p(y)
    ax = axes[0]
    ax.plot(z.index, z.values, lw=1.0, color=COR_LOG1P)
    ax.set_title("(a) A serie que o treino com log1p enxerga — log(1 + quantidade)",
                 fontsize=11, color=INK, loc="left", pad=8)
    ax.set_ylabel("log(1 + unidades)", fontsize=9, color=INK_FRACO)
    ax.set_xlim(z.index.min(), z.index.max())
    cv_antes = f"{y.std() / y.mean():.2f}".replace(".", ",")
    cv_depois = f"{z.std() / z.mean():.2f}".replace(".", ",")
    # Canto superior esquerdo: a serie em log ocupa a faixa 6–11, o topo fica livre.
    ax.annotate(f"CV cai de {cv_antes} para {cv_depois}; as quedas a zero sao domingo e feriado",
                xy=(.012, .93), xycoords="axes fraction", fontsize=8.5, color=INK_FRACO,
                va="top")
    _limpar(ax)

    # ---------------------------------------------------------------- (b)
    ax = axes[1]
    ini, fim = a.index.min(), a.index.max()
    real = y.loc[ini:fim]
    ax.plot(real.index, real.values, lw=1.0, color=COR_REAL, label="realizado", zorder=1)
    ax.plot(a.index, a["previsto"], lw=1.3, color=COR_SEM_LOG, label="previsao sem log", zorder=3)
    ax.plot(b.index, b["previsto"], lw=1.3, color=COR_LOG1P, label="previsao com log1p", zorder=2)
    ax.set_title("(b) Previsao do dia seguinte (h = 1) contra o realizado — "
                 f"{len(a)} origens, {ini.date()} a {fim.date()}",
                 fontsize=11, color=INK, loc="left", pad=8)
    ax.set_ylabel("unidades / dia", fontsize=9, color=INK_FRACO)
    ax.yaxis.set_major_formatter(FMT_MIL)
    ax.legend(fontsize=9, frameon=False, labelcolor=INK_FRACO, ncol=3, loc="upper left")
    ax.annotate("os picos de venda grande nao sao alcancados por nenhum dos dois",
                xy=(.012, .70), xycoords="axes fraction", fontsize=8.5, color=INK_FRACO)
    _limpar(ax)

    # ---------------------------------------------------------------- (c)
    ax = axes[2]
    corte = fim - pd.Timedelta(days=ZOOM_DIAS - 1)
    az, bz, rz = a.loc[corte:], b.loc[corte:], y.loc[corte:fim]
    ax.fill_between(az.index, az["ic_inf"], az["ic_sup"], color=COR_SEM_LOG, alpha=.13, lw=0)
    ax.fill_between(bz.index, bz["ic_inf"], bz["ic_sup"], color=COR_LOG1P, alpha=.16, lw=0)
    ax.plot(rz.index, rz.values, lw=1.8, color=COR_REAL, label="realizado")
    ax.plot(az.index, az["previsto"], lw=2.0, color=COR_SEM_LOG, label="sem log")
    ax.plot(bz.index, bz["previsto"], lw=2.0, color=COR_LOG1P, label="com log1p")
    ax.set_title(f"(c) Ultimas {ZOOM_DIAS // 7} semanas, com a faixa de 95% de cada treino",
                 fontsize=11, color=INK, loc="left", pad=8)
    ax.set_ylabel("unidades / dia", fontsize=9, color=INK_FRACO)
    ax.yaxis.set_major_formatter(FMT_MIL)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.legend(fontsize=9, frameon=False, labelcolor=INK_FRACO, ncol=3, loc="upper left")
    # Rotulo direto no fim de cada linha: identidade sem depender so da cor. As duas
    # previsoes convergem perto de zero no ultimo dia, entao os rotulos sao afastados na
    # vertical para nao colidirem.
    ax.set_xlim(rz.index.min(), rz.index.max() + pd.Timedelta(days=4))
    for serie, cor, nome, dy in ((az["previsto"], COR_SEM_LOG, "sem log", 9),
                                 (bz["previsto"], COR_LOG1P, "log1p", -9)):
        ax.annotate(nome, xy=(serie.index[-1], serie.iloc[-1]), xytext=(6, dy),
                    textcoords="offset points", fontsize=8.5, color=cor, va="center")
    _limpar(ax)

    fig.suptitle("Itabirito — SARIMAX com e sem log1p, mesmos parametros e mesmas exogenas",
                 fontsize=13, color=INK, x=.012, ha="left", y=.985)
    fig.tight_layout(rect=(0, 0, 1, .965))
    destino = os.path.join(PLOTS_DIR, "20_itabirito_log1p_vs_sem_log.png")
    fig.savefig(destino, dpi=130, facecolor="white")
    plt.close(fig)
    print(f"[plot] {destino}")


if __name__ == "__main__":
    main()
