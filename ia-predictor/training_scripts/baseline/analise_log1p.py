"""Antes e depois do `log1p`: o que a transformação faz com a série do baseline A0-crua.

Gera o gráfico 12, que sustenta a etapa 02 do artefato do A0-crua e a análise 2.2 do mapa
de EDA (`docs/prediction/eda-explicada/000 - Mapa completo das analises exploratorias.md`):
a série entra transformada porque CV > `LOG_CV_THRESHOLD`, e o efeito é estabilizar a
variância — os picos de encomenda deixam de dominar a escala, e a distribuição sai de
assimétrica à direita para aproximadamente simétrica nos dias abertos.

Quatro painéis: série crua × série em log1p (em cima), histograma cru × histograma em
log1p (embaixo). O CV de cada escala aparece no título, junto da decisão do gate.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.baseline.analise_log1p
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

from training_scripts.baseline import sarimax_serie_crua as base

COR_CRUA = "#3a6ea5"
COR_LOG = "#8e44ad"

FMT_MIL = mtick.FuncFormatter(lambda v, _: f"{v / 1000:.0f} mil" if abs(v) >= 1000 else f"{v:.0f}")


def main() -> None:
    serie, info = base.carregar_serie()
    cv = float(serie.std() / serie.mean())
    log = base.usar_log(serie)
    z = np.log1p(serie)
    cv_z = float(z.std() / z.mean())

    fig, axes = plt.subplots(2, 2, figsize=(13, 7.5))

    # Linha de cima: a série nas duas escalas.
    axes[0, 0].plot(serie.index, serie.values, lw=.7, color=COR_CRUA)
    axes[0, 0].set_title(f"Série crua — CV {cv:.2f}".replace(".", ","))
    axes[0, 0].set_ylabel("unidades / dia")
    axes[0, 0].yaxis.set_major_formatter(FMT_MIL)

    axes[0, 1].plot(z.index, z.values, lw=.7, color=COR_LOG)
    axes[0, 1].set_title(f"Depois de log1p — CV {cv_z:.2f}".replace(".", ","))
    axes[0, 1].set_ylabel("log(1 + unidades)")

    # Linha de baixo: a distribuição nas duas escalas.
    axes[1, 0].hist(serie.values, bins=50, color=COR_CRUA, alpha=.85)
    axes[1, 0].axvline(serie.mean(), color="#000", lw=1, ls="--", label="média")
    axes[1, 0].axvline(serie.median(), color="#000", lw=1, ls=":", label="mediana")
    axes[1, 0].set_title("Distribuição crua — cauda longa à direita")
    axes[1, 0].set_xlabel("unidades / dia")
    axes[1, 0].xaxis.set_major_formatter(FMT_MIL)
    axes[1, 0].legend(fontsize=8, frameon=False)

    axes[1, 1].hist(z.values, bins=50, color=COR_LOG, alpha=.85)
    axes[1, 1].axvline(z.mean(), color="#000", lw=1, ls="--", label="média")
    axes[1, 1].axvline(z.median(), color="#000", lw=1, ls=":", label="mediana")
    axes[1, 1].set_title("Distribuição em log1p — o pico em 0 são os dias fechados")
    axes[1, 1].set_xlabel("log(1 + unidades)")
    axes[1, 1].legend(fontsize=8, frameon=False)

    decisao = "aplica log1p" if log else "mantém a escala original"
    fig.suptitle(
        f"O que o log1p faz com a série — CV {cv:.2f} > {base.LOG_CV_THRESHOLD:.1f} "
        f"⇒ {decisao}  ·  máx. {info['max'] / 1000:.0f} mil contra média "
        f"{info['media'] / 1000:.1f} mil".replace(".", ","),
    )
    fig.tight_layout()
    caminho = os.path.join(base.PLOTS_DIR, "12_log1p_antes_depois.png")
    fig.savefig(caminho, dpi=130)
    plt.close(fig)
    print(f"[analise_log1p] CV crua {cv:.3f} · CV log1p {cv_z:.3f} · gate: {decisao}")
    print(f"[analise_log1p] {caminho}")


if __name__ == "__main__":
    main()
