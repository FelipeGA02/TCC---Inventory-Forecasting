"""Graficos que consolidam a etapa de testes de Itabirito (para o e-mail ao orientador).

Um PNG por figura, em `results/email_orientador/`, numerados na ordem em que o e-mail os
cita. Em cada figura, todos os paineis usam a mesma escala; metricas de unidades diferentes
(razao x porcentagem, unidades x log) ficam em arquivos separados (sufixos a/b).

  1. Separacao das encomendas
    01_serie_total_itabirito.png        venda total diaria, dias com encomenda marcados
    02_tamanho_das_vendas.png           distribuicao do tamanho da venda (documento) e o corte de 2.000
    03_fluxo_e_encomendas.png           a serie partida em fluxo diario + encomendas
  2. Previsao da loja inteira (L1)
    04a_fluxo_em_unidades.png           fluxo diario em unidades (treino C)
    04b_fluxo_em_log1p.png              o mesmo fluxo em log1p (treino D)
    05a_treinos_l1_mase.png             treinos A-D: MASE
    05b_treinos_l1_cobertura_vies.png   treinos A-D: cobertura do IC 95% e volume previsto / vendido
    06_previsto_vs_real_fluxo.png       treinos C e D contra o realizado, ultimas 12 semanas
  3. Desagregacao x modelo por produto
    07a_skus_mase.png                   MASE por metodo
    07b_skus_percentuais.png            vence o naive, cobertura da faixa, erro no total de 14 dias
    08_sku_exemplo_grama_esmeralda.png  exemplo: faixa do SARIMAX por produto x da desagregacao
  4. Modelo por produto regular
    09_series_skus_regulares.png        as 12 series de SKU do teste por produto
    10_skus_mase_por_produto.png        MASE de cada produto nos tres metodos principais
    11a_skus_configuracoes_mase.png     ajuste do SARIMAX por produto: MASE das 4 configuracoes (d x log)
    11b_skus_configuracoes_largura.png  idem: largura da faixa de 95% / venda media
    12a_regra_produto_largura.png       regra de encomenda por produto: largura da faixa antes x depois
    12b_regra_produto_volume_tirado.png quanto da venda de cada produto a regra tratou como encomenda

Todas as metricas sao dos dias de loja aberta (domingo e feriado tem venda 0 e previsao ~0,
o que deixa MASE menor e cobertura maior sem informar nada).

Cores (validadas para daltonismo e contraste): azul = sem log, laranja = log1p,
roxo = encomendas / desagregacao, cinza = realizado.

Uso (a partir de `ia-predictor/`, depois dos treinos A-D e de
`disaggregation/sku_regular_vs_desagregacao.py --unidade itabirito`):
    python -m training_scripts.relatorios.plots_etapa_itabirito
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from training_scripts.baseline.sarimax_itabirito_core import (  # noqa: E402
    BASE_ENCOMENDAS, BASE_FLUXO_DIARIO, BASE_ITABIRITO, CALENDARIO, METRICS_DIR,
    PRIMEIRA_ORIGEM, _bloco, serie_diaria,
)
from training_scripts.disaggregation.sku_regular_vs_desagregacao import carregar_fluxo  # noqa: E402
from training_scripts.preprocessing.remove_encomendas_06 import (  # noqa: E402
    CLASSIFIED_CSV, LIMIAR_QTD_VENDA,
)

SAIDA = os.path.join(os.path.dirname(METRICS_DIR), "email_orientador")
UNIDADE = "Itabirito"

AZUL, LARANJA, ROXO = "#3a6ea5", "#c8650f", "#8e44ad"
REAL, GRADE, TINTA, TINTA_FRACA = "#444444", "#d8dce1", "#15181d", "#5a6471"
FMT_MIL = mtick.FuncFormatter(
    lambda v, _: f"{v / 1000:.0f} mil" if abs(v) >= 1000 else f"{v:.0f}")
_MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MESES = mtick.FuncFormatter(
    lambda v, _: f"{_MESES_PT[mdates.num2date(v).month - 1]}/{mdates.num2date(v):%y}")


def br(v: float, casas: int = 2) -> str:
    """Numero no padrao brasileiro: 1.234,56."""
    return f"{v:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _br_tick(v, _):
    if float(v).is_integer():
        return br(v, 0)
    return br(v, 1) if abs(v * 10 - round(v * 10)) < 1e-9 else br(v, 2)


FMT_BR = mtick.FuncFormatter(_br_tick)

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.labelcolor": TINTA_FRACA, "xtick.color": TINTA_FRACA, "ytick.color": TINTA_FRACA,
    "axes.edgecolor": GRADE, "figure.dpi": 110, "savefig.dpi": 160,
    "savefig.bbox": "tight", "legend.frameon": False,
})


def _limpar(ax, y_mil: bool = False) -> None:
    ax.grid(True, axis="y", color=GRADE, lw=.6)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    if y_mil:
        ax.yaxis.set_major_formatter(FMT_MIL)
    elif ax.get_yscale() == "linear":
        ax.yaxis.set_major_formatter(FMT_BR)


def _inicio_teste(ax, rotulo: bool = True) -> None:
    ax.axvline(PRIMEIRA_ORIGEM, color=TINTA_FRACA, lw=.8, ls="--")
    if rotulo:
        ax.text(PRIMEIRA_ORIGEM, ax.get_ylim()[1], "  início do teste", va="top", ha="left",
                fontsize=8, color=TINTA_FRACA)


def _rotular_figura(fig, nome: str) -> None:
    """Prefixa o titulo com "Figura N" (tirado do nome do arquivo), para casar anexo e texto."""
    rotulo = f"Figura {nome.split('_')[0].lstrip('0')} · "
    sup = fig._suptitle
    if sup is not None and sup.get_text():
        sup.set_text(rotulo + sup.get_text())
        return
    ax = fig.axes[0]
    ax.set_title(rotulo + ax.get_title(loc="left"), loc="left")


def _salvar(fig, nome: str, recortar: bool = True) -> str:
    _rotular_figura(fig, nome)
    os.makedirs(SAIDA, exist_ok=True)
    caminho = os.path.join(SAIDA, nome)
    # recortar=False mantem o tamanho da figura: duas figuras com eixo em posicao fixa
    # saem com a area de plotagem identica (o recorte "tight" varia com o titulo).
    # bbox_inches=None cairia no rcParams ("tight"); "standard" forca o tamanho da figura.
    with plt.rc_context({"savefig.bbox": "tight" if recortar else "standard"}):
        fig.savefig(caminho, facecolor="white")
    plt.close(fig)
    print(f"[ok] {nome}")
    return caminho


def _fechados() -> set:
    cal = pd.read_csv(CALENDARIO, sep=";", parse_dates=["data"])
    return set(cal.loc[(cal["unidade"] == UNIDADE) & (cal["loja_fechada"] == 1), "data"])


# --------------------------------------------------------------------------- #
# Series usadas no treino
# --------------------------------------------------------------------------- #
def series() -> tuple[pd.Series, pd.Series, pd.Series]:
    total = serie_diaria(BASE_ITABIRITO)
    fluxo = serie_diaria(BASE_FLUXO_DIARIO, calendario=total.index)
    enc = serie_diaria(BASE_ENCOMENDAS, calendario=total.index)
    return total, fluxo, enc


def p01_serie_total(total, enc):
    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot(total.index, total.values, color=REAL, lw=.7)
    dias = enc[enc > 0].index
    ax.scatter(dias, total.loc[dias], s=14, color=ROXO, zorder=3,
               label=f"dia com encomenda (venda > {LIMIAR_QTD_VENDA:,} un.)".replace(",", "."))
    pico = total.idxmax()
    ax.annotate(f"{pico:%d/%m/%Y}: {total.max():,.0f} un.\n(uma única venda: 61.172)".replace(",", "."),
                (pico, total.max()), xytext=(-190, -45), textcoords="offset points",
                fontsize=8, color=TINTA, arrowprops=dict(arrowstyle="-", color=TINTA_FRACA, lw=.6))
    _limpar(ax, y_mil=True)
    _inicio_teste(ax)
    ax.xaxis.set_major_formatter(MESES)
    ax.set_title("Itabirito · venda total diária (jan/2024 a fev/2026)", loc="left")
    ax.set_ylabel("unidades por dia")
    ax.legend(loc="upper left")
    fig.text(0.01, -0.04, f"CV diário {br(total.std() / total.mean())} · mediana {br(total.median(), 0)} un./dia · "
             f"{(enc > 0).sum()} dias com encomenda concentram {br(enc.sum() / total.sum() * 100, 0)}% do volume",
             fontsize=8.5, color=TINTA_FRACA)
    return _salvar(fig, "01_serie_total_itabirito.png")


def p02_tamanho_vendas():
    cols = ["unidade", "emissao", "doc_numero", "qtdade", "categoria"]
    df = pd.read_csv(CLASSIFIED_CSV, sep=";", usecols=cols, dtype=str, keep_default_na=False)
    df = df[(df["unidade"] == UNIDADE) & (df["categoria"] != "Servico e taxa")]
    df["qtdade"] = pd.to_numeric(df["qtdade"], errors="coerce").fillna(0.0)
    vendas = df.groupby(["emissao", "doc_numero"])["qtdade"].sum()
    vendas = vendas[vendas > 0]
    grandes = vendas[vendas > LIMIAR_QTD_VENDA]

    fig, ax = plt.subplots(figsize=(9, 3.8))
    bins = np.logspace(0, np.log10(vendas.max()) + .05, 60)
    ax.hist(vendas[vendas <= LIMIAR_QTD_VENDA], bins=bins, color=AZUL, alpha=.85, label="fluxo diário")
    ax.hist(grandes, bins=bins, color=ROXO, label="encomenda")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.axvline(LIMIAR_QTD_VENDA, color=TINTA, lw=1, ls="--")
    ax.text(LIMIAR_QTD_VENDA * 1.1, ax.get_ylim()[1] * .5,
            f"corte: {br(LIMIAR_QTD_VENDA, 0)} un. por venda\n{len(grandes)} vendas "
            f"({br(len(grandes) / len(vendas) * 100)}%)\n= {br(grandes.sum() / vendas.sum() * 100, 1)}% do volume",
            fontsize=8.5, va="top", color=TINTA)
    _limpar(ax)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))
    ax.set_title("Itabirito · tamanho de cada venda (soma do documento)", loc="left")
    ax.set_xlabel("unidades na venda (escala log)")
    ax.set_ylabel("nº de vendas (escala log)")
    ax.legend(loc="upper center")
    fig.text(0.01, -0.06, f"{len(vendas):,} vendas · mediana {vendas.median():.0f} un. · p99 {vendas.quantile(.99):.0f} un."
             .replace(",", "."), fontsize=8.5, color=TINTA_FRACA)
    return _salvar(fig, "02_tamanho_das_vendas.png")


def p03_fluxo_encomendas(fluxo, enc):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True, sharey=True)
    a1.plot(fluxo.index, fluxo.values, color=AZUL, lw=.7)
    a1.set_title(f"Fluxo diário — o que o SARIMAX prevê · CV {br(fluxo.std() / fluxo.mean())} "
                 f"(a venda total tinha CV 2,35)", loc="left")
    a2.bar(enc.index, enc.values, color=ROXO, width=1.5)
    a2.set_title(f"Encomendas — {(enc > 0).sum()} dias com venda em 789 · fora da série do SARIMAX",
                 loc="left")
    for ax in (a1, a2):
        _limpar(ax, y_mil=True)
        ax.set_ylabel("unidades por dia")
        _inicio_teste(ax, rotulo=ax is a1)
    a2.xaxis.set_major_formatter(MESES)
    fig.suptitle("Itabirito · a venda total separada em dois fluxos pelo tamanho da venda "
                 "(mesma escala nos dois painéis)", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    return _salvar(fig, "03_fluxo_e_encomendas.png")


FOLGA_TOPO = 1.05      # topo do eixo 5% acima do maior valor, igual nas duas figuras


def _serie_com_cv(z: pd.Series, cor: str, titulo: str, nome: str, rotulo_y: str,
                  rotulo_cv: str, fmt) -> str:
    """A serie que o modelo ajusta (y no treino C, log(1 + y) no treino D), com o CV dela.

    04a e 04b ficam na MESMA proporcao: eixo em posicao fixa (area de plotagem identica,
    sem tight_layout nem recorte) e topo do eixo = maior valor x FOLGA_TOPO, de modo que o
    maior pico ocupa a mesma altura relativa nas duas. Os valores do eixo y sao os da serie
    que o modelo ve: unidades no 04a, log(1 + unidades) no 04b. CV com todos os dias, como
    o 0,78 citado no texto.
    """
    fig = plt.figure(figsize=(11, 3.6))
    a = fig.add_axes([0.08, 0.12, 0.90, 0.74])
    a.plot(z.index, z.values, color=cor, lw=.7)
    a.xaxis.set_major_formatter(MESES)
    a.set_ylim(0, float(z.max()) * FOLGA_TOPO)
    _limpar(a)
    a.yaxis.set_major_formatter(fmt)
    a.set_title(f"{rotulo_cv} = {br(z.std() / z.mean())}", loc="right", fontsize=10.5, color=cor)
    a.set_ylabel(rotulo_y)
    _inicio_teste(a)
    a.set_title(titulo, loc="left")
    return _salvar(fig, nome, recortar=False)


def p04_log1p(fluxo):
    _serie_com_cv(fluxo, AZUL, "Itabirito · base sem encomendas, como o modelo sem log enxerga",
                  "04a_fluxo_em_unidades.png", "unidades por dia", "CV de y", FMT_BR)
    _serie_com_cv(np.log1p(fluxo), LARANJA, "Itabirito · base sem encomendas em log(1 + y), como o modelo log1p enxerga",
                  "04b_fluxo_em_log1p.png", "log(1 + unidades por dia)", "CV de log(1 + y)", FMT_BR)


def p05_skus(tab: pd.DataFrame):
    """Venda diaria (base sem encomendas) de cada produto testado, no periodo completo da base.

    Grafico de linha simples, em unidades, com a MESMA escala em todos os paineis.
    """
    fluxo, _ = carregar_fluxo(UNIDADE)
    idx = pd.date_range(fluxo["emissao"].min(), fluxo["emissao"].max(), freq="D")
    ini, fim = idx[0], idx[-1]

    fig, axes = plt.subplots(4, 3, figsize=(12, 9.5), sharex=True, sharey=True)
    for ax, r in zip(axes.flat, tab.itertuples()):
        d = (fluxo[fluxo["produto_cod"] == r.sku].groupby("emissao")["qtdade"].sum()
             .reindex(idx, fill_value=0.0))
        ax.plot(d.index, d.values, color=AZUL, lw=.6)
        ax.set_title(r.nome[:34], loc="left", fontsize=8.5)
        _limpar(ax)
        ax.axvline(PRIMEIRA_ORIGEM, color=TINTA_FRACA, lw=.7, ls="--")
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
        ax.xaxis.set_major_formatter(MESES)
        ax.tick_params(labelsize=7.5)
    for ax in axes[:, 0]:
        ax.set_ylabel("unidades por dia", fontsize=8)
    fig.suptitle(f"Itabirito · venda diária dos 12 produtos regulares, sem encomendas · "
                 f"{ini:%d/%m/%Y} a {fim:%d/%m/%Y} · tracejado = início do teste", x=0.01, ha="left", fontweight="bold", fontsize=10)
    fig.tight_layout()
    return _salvar(fig, "09_series_skus_regulares.png")


# --------------------------------------------------------------------------- #
# Resultados
# --------------------------------------------------------------------------- #
TREINOS = [
    ("A", "com encomendas\nsem log", "itabirito_sem_log_deslizante_previsoes", AZUL, False),
    ("B", "com encomendas\nlog1p", "itabirito_log1p_deslizante_previsoes", LARANJA, False),
    ("C", "sem encomendas\nsem log", "itabirito_fluxo_sem_log_deslizante_previsoes", AZUL, True),
    ("D", "sem encomendas\nlog1p", "itabirito_fluxo_log1p_deslizante_previsoes", LARANJA, True),
]


def metricas_treinos() -> pd.DataFrame:
    fech = _fechados()
    linhas = []
    for letra, rot, arq, _, _ in TREINOS:
        d = pd.read_csv(os.path.join(METRICS_DIR, f"{arq}.csv"), sep=";", parse_dates=["origem", "data"])
        d = d.dropna(subset=["real"])
        b = _bloco(d[~d["data"].isin(fech)])
        linhas.append({"treino": letra, "rotulo": rot, **b})
    return pd.DataFrame(linhas)


def _faixa_meta(ax, lo=90, hi=98):
    ax.axhspan(lo, hi, color="#e8f5e0", zorder=0)


TITULO_COBERTURA = ("Cobertura do intervalo de 95%\n"
                    "% dos dias em que a venda ficou dentro do intervalo · meta 90–98% (verde)")


def _paineis_barras(paineis, desenhar, titulo: str, nome: str, ylim: tuple, legenda=None) -> str:
    """Varias metricas da MESMA unidade, lado a lado, com o mesmo eixo y."""
    largura = 9 if len(paineis) == 1 else 5.4 * len(paineis)
    fig, axes = plt.subplots(1, len(paineis), figsize=(largura, 4.4), sharey=True, squeeze=False)
    for a, (col, sub, ref, fmt) in zip(axes[0], paineis):
        desenhar(a, col, fmt)
        titulo_painel, _, explicacao = sub.partition("\n")
        a.set_title(titulo_painel, loc="left", fontsize=10.5, pad=18 if explicacao else 6)
        if explicacao:      # segunda linha mais leve: o que o numero mede e qual o valor ideal
            a.text(0, 1.015, explicacao, transform=a.transAxes, fontsize=8.5, color=TINTA_FRACA,
                   va="bottom")
        _limpar(a)
        a.set_ylim(*ylim)
        if col == "cobertura_ic95_pct":
            _faixa_meta(a)
        if ref is not None:
            a.axhline(ref, color=TINTA, lw=.9, ls="--")
    fig.suptitle(titulo, x=0.01, ha="left", fontweight="bold", fontsize=10)
    fig.tight_layout(rect=(0, .07 if legenda else 0, 1, .9 if "\n" in titulo else .93))
    if legenda:
        fig.legend(*legenda, loc="lower center", ncol=len(legenda[0]))
    return _salvar(fig, nome)


def p06_treinos(m: pd.DataFrame):
    x = np.arange(len(TREINOS))
    cores = [t[3] for t in TREINOS]
    rot = [t[1] for t in TREINOS]

    def desenhar(a, col, fmt):
        barras = a.bar(x, m[col], color=cores, width=.62)
        for i, b in enumerate(barras):
            if TREINOS[i][4]:
                b.set_hatch("///")
                b.set_edgecolor("white")
        a.bar_label(barras, labels=[fmt(v) for v in m[col]], fontsize=8.5, padding=2)
        a.set_xticks(x, [""] * len(x))      # a legenda (cor + hachurado) identifica as barras
        a.tick_params(axis="x", length=0)

    from matplotlib.patches import Patch
    neutro = "#9aa4b1"
    leg = ([Patch(color=AZUL), Patch(color=LARANJA), Patch(facecolor=neutro),
            Patch(facecolor=neutro, hatch="///", edgecolor="white")],
           ["sem log", "log1p", "base com encomendas", "base sem encomendas"])
    base = "Itabirito · previsão da loja inteira, janela deslizante de 425 dias, 351 origens, h = 1..14, dias de loja aberta"
    teto = m["mase"].max() * 1.15
    _paineis_barras([("mase", "MASE", 1.0, lambda v: br(v))],
                    desenhar, base, "05a_treinos_l1_mase.png", (0, teto), leg)
    _paineis_barras([("cobertura_ic95_pct", TITULO_COBERTURA, None, lambda v: br(v, 1) + "%"),
                     ("vies_previsto_sobre_real_pct", "Volume previsto ÷ volume vendido\n"
                      "100% = sem viés · abaixo de 100% = prevê menos do que vende", 100,
                      lambda v: br(v, 0) + "%")],
                    desenhar, base, "05b_treinos_l1_cobertura_vies.png", (0, 112), leg)


def p07_previsto_real():
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True, sharey=True)
    for ax, (rot, arq, cor) in zip(axes, [
            ("sem log", "itabirito_fluxo_sem_log_deslizante_operacional", AZUL),
            ("log1p", "itabirito_fluxo_log1p_deslizante_operacional", LARANJA)]):
        d = pd.read_csv(os.path.join(METRICS_DIR, f"{arq}.csv"), sep=";", parse_dates=["data"])
        d = d.set_index("data").sort_index().iloc[-84:]
        ax.fill_between(d.index, d["ic_inf"], d["ic_sup"], color=cor, alpha=.18, lw=0, label="faixa 95%")
        ax.plot(d.index, d["real"], color=REAL, lw=1.3, label="vendido (sem encomendas)")
        ax.plot(d.index, d["previsto"], color=cor, lw=1.6, label="previsto")
        ax.set_title(f"Base sem encomendas · {rot} · previsão do dia seguinte", loc="left")
        _limpar(ax, y_mil=True)
        ax.legend(loc="upper left", ncol=3)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    fig.suptitle("Itabirito · previsto × vendido nas últimas 12 semanas do teste (janela deslizante de 425 dias)", x=0.01, ha="left",
                 fontweight="bold")
    fig.tight_layout()
    return _salvar(fig, "06_previsto_vs_real_fluxo.png")


METODOS = [("sarimax_sku", "SARIMAX\npor produto"), ("desag_8sem", "Desagregação\n8 semanas"),
           ("desag_hist", "Desagregação\nhistórico")]


def p08_skus_metodos(met: dict):
    x = np.arange(len(METODOS))
    w = .36
    variantes = [("sem_log", AZUL, "sem log"), ("log1p", LARANJA, "log1p")]

    def desenhar(a, col, fmt):
        for j, (var, cor, rotv) in enumerate(variantes):
            vals = [met[f"{mt}|{var}"]["dias_abertos"][col] for mt, _ in METODOS]
            b = a.bar(x + (j - .5) * w, vals, w * .92, color=cor, label=rotv)
            a.bar_label(b, labels=[fmt(v) for v in vals], fontsize=8, padding=2)
        a.set_xticks(x, [r for _, r in METODOS], fontsize=8.5)

    from matplotlib.patches import Patch
    leg = ([Patch(color=c) for _, c, _ in variantes], [r for *_, r in variantes])
    base = "Itabirito · previsão diária por produto: 12 produtos regulares, origem diária (h = 1–14), dias de loja aberta"
    teto = max(met[k]["dias_abertos"]["mase"] for k in met) * 1.15
    _paineis_barras([("mase", "MASE", 1.0,
                      lambda v: br(v))],
                    desenhar, base, "07a_skus_mase.png", (0, teto), leg)
    _paineis_barras([("vence_naive_pct", "Rodadas em que errou menos que o naive sazonal\n"
                      "% das combinações produto × rodada · maior é melhor", None, lambda v: br(v, 0) + "%"),
                     ("cobertura_ic95_pct", TITULO_COBERTURA, None, lambda v: br(v, 0) + "%"),
                     ("erro_total_14d_pct", "Erro no total de 14 dias do produto\n"
                      "|previsto − vendido| ÷ vendido, na quinzena · menor é melhor", None,
                      lambda v: br(v, 0) + "%")],
                    desenhar, base, "07b_skus_percentuais.png", (0, 112), leg)


def p09_mase_por_sku(tab: pd.DataFrame):
    t = tab.iloc[::-1]
    y = np.arange(len(t))
    fig, ax = plt.subplots(figsize=(10, 5.6))
    series_ = [("mase|desag_hist|sem_log", ROXO, "^", "Desagregação (histórico, sem log)"),
               ("mase|sarimax_sku|sem_log", AZUL, "s", "SARIMAX por produto, sem log"),
               ("mase|sarimax_sku|log1p", LARANJA, "o", "SARIMAX por produto, log1p")]
    for col, cor, mk, rot in series_:
        ax.scatter(t[col], y, color=cor, marker=mk, s=46, label=rot, zorder=3,
                   edgecolor="white", linewidth=1)
    faixa = t[[c for c, *_ in series_]]
    ax.hlines(y, faixa.min(axis=1), faixa.max(axis=1), color=GRADE, lw=1.2, zorder=1)
    ax.axvline(1, color=TINTA, lw=.9, ls="--")
    ax.text(1, -.9, " MASE = 1", fontsize=8, color=TINTA, va="center")
    ax.set_ylim(-1.3, len(t) - .4)
    ax.xaxis.set_major_formatter(FMT_BR)
    ax.set_yticks(y, [f"{n[:34]} ({int(r)} rod.)" for n, r in zip(t["nome"], t["rodadas"])], fontsize=8.5)
    ax.grid(True, axis="x", color=GRADE, lw=.6)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.set_xlabel("MASE nos dias de loja aberta")
    ax.set_title("Itabirito · MASE de cada produto (o SARIMAX por produto com log1p é o menor nos 12)",
                 loc="left", fontsize=10.5)
    fig.tight_layout(rect=(0, .07, 1, 1))
    h, lab = ax.get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=3, fontsize=8.5)
    return _salvar(fig, "10_skus_mase_por_produto.png")


def p10_exemplo(prev: pd.DataFrame, sku: str = "00013475"):
    d = prev[(prev["sku"] == sku) & (prev["variante"] == "log1p")]
    # Origens a cada 14 dias contando da ultima, para as janelas nao se sobreporem.
    origens = sorted(d["origem"].unique())[::-1][::14][:6][::-1]
    d = d[d["origem"].isin(origens)]
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True, sharey=True)
    for ax, (met, cor, rot) in zip(axes, [("sarimax_sku", LARANJA, "SARIMAX no próprio produto (log1p)"),
                                          ("desag_hist", ROXO, "Desagregação: previsão da loja × fatia do produto (log1p)")]):
        g = d[d["metodo"] == met].set_index("data").sort_index()
        dentro = ((g["real"] >= g["ic_inf"]) & (g["real"] <= g["ic_sup"]))[~g.index.isin(_fechados())].mean()
        ax.fill_between(g.index, g["ic_inf"], g["ic_sup"], color=cor, alpha=.2, lw=0, label="faixa 95%")
        ax.plot(g.index, g["real"], color=REAL, lw=1.3, label="vendido")
        ax.plot(g.index, g["previsto"], color=cor, lw=1.6, label="previsto")
        for o in origens:
            ax.axvline(o, color=GRADE, lw=.8)
        aberto = ~g.index.isin(_fechados())
        larg = (g["ic_sup"] - g["ic_inf"])[aberto].mean()
        ax.set_title(f"{rot} · faixa acertou {dentro:.0%} dos dias abertos · largura média "
                     f"{br(larg, 0)} un. (venda média {br(g['real'][aberto].mean(), 0)})", loc="left", fontsize=10)
        _limpar(ax)
        ax.legend(loc="upper left", ncol=3)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    fig.suptitle("Exemplo · Grama Esmeralda (ITO), 6 janelas de 14 dias sem sobreposição (linhas verticais = "
                 "início de cada rodada)", x=0.01, ha="left", fontweight="bold", fontsize=10)
    fig.tight_layout()
    return _salvar(fig, "08_sku_exemplo_grama_esmeralda.png")


CONFIGS_SKU = [("d0|sem_log", "d = 0\nsem log", AZUL, False), ("d1|sem_log", "d = 1\nsem log", AZUL, True),
               ("d0|log1p", "d = 0\nlog1p", LARANJA, False), ("d1|log1p", "d = 1\nlog1p", LARANJA, True)]


def _leg_configs():
    from matplotlib.patches import Patch
    neutro = "#9aa4b1"
    return ([Patch(color=AZUL), Patch(color=LARANJA), Patch(facecolor=neutro),
             Patch(facecolor=neutro, hatch="///", edgecolor="white")],
            ["sem log", "log1p", "d = 0 (com constante)", "d = 1"])


def p11_ajuste_parametros(met_enc: dict):
    """Teste de ajuste do SARIMAX por produto: 4 configuracoes, so a regra da loja ("antes")."""
    x = np.arange(len(CONFIGS_SKU))

    def desenhar(a, col, fmt):
        vals = [met_enc[f"{k}|antes"][col] for k, *_ in CONFIGS_SKU]
        barras = a.bar(x, vals, color=[c for *_, c, _ in CONFIGS_SKU], width=.62)
        for b, (*_, listrado) in zip(barras, CONFIGS_SKU):
            if listrado:
                b.set_hatch("///")
                b.set_edgecolor("white")
        a.bar_label(barras, labels=[fmt(v) for v in vals], fontsize=8.5, padding=2)
        a.set_xticks(x, [""] * len(x))
        a.tick_params(axis="x", length=0)

    base = "Itabirito · SARIMAX por produto, 4 configurações, 12 produtos regulares, origem diária (h = 1–14), dias de loja aberta"
    teto = max(met_enc[f"{k}|antes"]["mase"] for k, *_ in CONFIGS_SKU) * 1.15
    _paineis_barras([("mase", "MASE", 1.0, lambda v: br(v))],
                    desenhar, base, "11a_skus_configuracoes_mase.png", (0, teto), _leg_configs())
    teto = max(met_enc[f"{k}|antes"]["largura_sobre_venda_media"] for k, *_ in CONFIGS_SKU) * 1.18
    _paineis_barras([("largura_sobre_venda_media", "Largura da faixa de 95% ÷ venda média do produto\n"
                      "quantas vezes a faixa é maior que a venda média do dia · menor é melhor", None,
                      lambda v: br(v, 1) + "×")],
                    desenhar, base, "11b_skus_configuracoes_largura.png", (0, teto), _leg_configs())


def p12_regra_por_produto(met_enc: dict, volume_por_sku: dict, nomes: dict):
    """Encomenda marcada por produto (Iglewicz & Hoaglin): largura da faixa e volume tirado."""
    from matplotlib.patches import Patch
    x = np.arange(len(CONFIGS_SKU))
    w = .36
    neutro = "#9aa4b1"

    def desenhar(a, col, fmt):
        for j, (quando, cor) in enumerate([("antes", neutro), ("depois", ROXO)]):
            vals = [met_enc[f"{k}|{quando}"][col] for k, *_ in CONFIGS_SKU]
            b = a.bar(x + (j - .5) * w, vals, w * .92, color=cor)
            a.bar_label(b, labels=[fmt(v) for v in vals], fontsize=8, padding=2)
        a.set_xticks(x, [r for _, r, *_ in CONFIGS_SKU], fontsize=8.5)

    leg = ([Patch(color=neutro), Patch(color=ROXO)],
           ["só a regra da loja (nota > 2.000 un.)", "+ regra de encomenda por produto"])
    teto = max(v["largura_sobre_venda_media"] for v in met_enc.values()) * 1.18
    _paineis_barras([("largura_sobre_venda_media", "Largura da faixa de 95% ÷ venda média do produto\n"
                      "quantas vezes a faixa é maior que a venda média do dia · menor é melhor", None,
                      lambda v: br(v, 1) + "×")],
                    desenhar, "Itabirito · efeito da regra de encomenda por produto sobre a faixa de previsão",
                    "12a_regra_produto_largura.png", (0, teto), leg)

    v = pd.Series(volume_por_sku).sort_values()
    fig, ax = plt.subplots(figsize=(9, 5))
    y = np.arange(len(v))
    barras = ax.barh(y, v.values, color=ROXO, height=.62)
    ax.bar_label(barras, labels=[br(x, 0) + "%" for x in v.values], fontsize=8.5, padding=3)
    ax.set_yticks(y, [nomes.get(s, s)[:34] for s in v.index], fontsize=8.5)
    ax.set_xlim(0, 100)
    ax.grid(True, axis="x", color=GRADE, lw=.6)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v_, _: f"{v_:.0f}%"))
    ax.set_xlabel("% da venda do produto nos dias de teste tratada como encomenda")
    ax.set_title("Itabirito · quanto da venda a regra por produto tirou de cada produto", loc="left")
    fig.tight_layout()
    return _salvar(fig, "12b_regra_produto_volume_tirado.png")


def main():
    total, fluxo, enc = series()
    p01_serie_total(total, enc)
    p02_tamanho_vendas()
    p03_fluxo_encomendas(fluxo, enc)
    p04_log1p(fluxo)

    base = os.path.join(METRICS_DIR, "sku_regular_itabirito")
    tab = pd.read_csv(f"{base}_por_sku.csv", sep=";", dtype={"sku": str})
    with open(f"{base}.json", encoding="utf-8") as fh:
        met_sku = json.load(fh)["metricas"]
    # Os graficos usam o bloco de todos os horizontes (h = 1..14).
    met_sku = {k: {"dias_abertos": v["dias_abertos"]["geral_todos_horizontes"]} for k, v in met_sku.items()}
    prev = pd.read_csv(f"{base}_previsoes.csv", sep=";", dtype={"sku": str}, parse_dates=["origem", "data"])
    p05_skus(tab)

    m = metricas_treinos()
    print(m[["treino", "mae", "mase", "mae_relativo_naive", "cobertura_ic95_pct", "largura_ic95",
             "vies_previsto_sobre_real_pct"]].round(3).to_string(index=False))
    p06_treinos(m)
    p07_previsto_real()
    p08_skus_metodos(met_sku)
    p09_mase_por_sku(tab)
    p10_exemplo(prev)

    # Seção 4 do e-mail: ajuste de parametros e regra de encomenda por produto
    with open(os.path.join(METRICS_DIR, "sku_encomenda_produto_itabirito.json"), encoding="utf-8") as fh:
        enc_prod = json.load(fh)
    _, nomes = carregar_fluxo(UNIDADE)
    met_enc = {k: v["geral_todos_horizontes"] for k, v in enc_prod["metricas_dias_abertos"].items()}
    p11_ajuste_parametros(met_enc)
    p12_regra_por_produto(met_enc, enc_prod["volume_tirado_por_sku_pct"], nomes)


if __name__ == "__main__":
    main()
