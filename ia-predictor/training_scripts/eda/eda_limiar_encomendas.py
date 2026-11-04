"""EDA 6 — Distribuição da quantidade dos pedidos e limiar de encomenda grande (ADR-018).

Agrupa a base de cada loja por pedido (documento: `CHAVE_VENDA`), soma a quantidade de cada
um (sem Serviço e taxa) e olha a distribuição dessas quantidades, em unidades. O pedido
acima de média + 4 desvios-padrão da sua loja é encomenda grande (`calcular_limiares`).

Saídas
------
* `results/plots/encomendas/distribuicao_pedidos.png` — por loja, o histograma da quantidade
  dos pedidos (eixo em escala log só para caber de 1 a 60 mil un.), com a média e os
  limiares de 3 e 4 desvios e o fixo de 2.000 un. (ADR-013);
* `results/plots/encomendas/limiar_no_tempo.png` — o limiar de cada loja recalculado com a
  base até o fim de cada mês, como ele anda à medida que as planilhas chegam;
* `results/metrics/limiar_encomendas_distribuicao.json` — por loja: n, média, desvio,
  quantis, limiares;
* `results/metrics/limiar_encomendas_series.csv` — o efeito em cada série do treino
  (4 categorias e produtos de grama, por loja): pedidos marcados, % do volume, CV e máximo
  da série diária que sobra e % do volume de `CONSUMIDOR` tirado (o custo, como no ADR-013),
  com o limiar fixo de 2.000 e com 3 e 4 desvios da loja.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.eda.eda_limiar_encomendas
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from training_scripts.preprocessing.classificacao_03 import CLASSIFIED_CSV
from training_scripts.preprocessing.limpeza_para_treino_04 import CATEGORIA_NAO_PRODUTO, UNIDADES
from training_scripts.preprocessing.remove_encomendas_06 import (
    CHAVE_VENDA,
    LIMIAR_QTD_VENDA,
    limiar_por_desvios,
    marcar_encomendas_por_unidade,
    tamanho_dos_pedidos,
)

from . import _common as C

PLOTS_DIR = os.path.join(os.path.dirname(C.PLOTS_DIR), "encomendas")
DISTRIBUICAO_JSON = os.path.join(C.METRICS_DIR, "limiar_encomendas_distribuicao.json")
SERIES_CSV = os.path.join(C.METRICS_DIR, "limiar_encomendas_series.csv")

MIN_DIAS_COM_VENDA = 28   # produto de grama treinado: venda em ≥ 28 dias do último ano (ADR-017)
JANELA_ULTIMO_ANO = 365
KS = (3.0, 4.0)
COR = {"hist": "#90A4AE", "media": "#37474F", 3.0: "#F9A825", 4.0: "#C62828", "fixo": "#1565C0"}


def _n(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


def carregar() -> pd.DataFrame:
    df = pd.read_csv(CLASSIFIED_CSV, sep=";", dtype=str, keep_default_na=False)
    df["qtdade"] = pd.to_numeric(df["qtdade"], errors="coerce").fillna(0.0)
    df["emissao"] = pd.to_datetime(df["emissao"], errors="coerce")
    df = df[(df["categoria"] != CATEGORIA_NAO_PRODUTO) & df["unidade"].isin(UNIDADES)
            & df["emissao"].notna()].copy()
    df["consumidor"] = df["cliente_nome"].str.strip().str.upper() == "CONSUMIDOR"
    return df


def series_do_treino(df: pd.DataFrame) -> list[dict]:
    """As séries que o treino recebe: as 4 categorias e os produtos de grama com venda em
    ≥ 28 dias do último ano, por loja."""
    series = []
    for unidade in UNIDADES:
        base = df[df["unidade"] == unidade]
        for cat in C.CATEGORIAS_L1:
            series.append({"unidade": unidade, "nivel": "categoria", "serie": cat, "nome": cat})
        ultimo_ano = base[base["emissao"] > base["emissao"].max() - pd.Timedelta(days=JANELA_ULTIMO_ANO)]
        grama = ultimo_ano[ultimo_ano["categoria"] == "Grama"]
        dias = grama.groupby("produto_cod")["emissao"].nunique()
        volume = grama.groupby("produto_cod")["qtdade"].sum()
        nomes = base.sort_values("emissao").groupby("produto_cod")["produto_nome"].last()
        for cod in volume[dias >= MIN_DIAS_COM_VENDA].sort_values(ascending=False).index:
            series.append({"unidade": unidade, "nivel": "produto", "serie": cod, "nome": nomes[cod]})
    return series


def distribuicao(pedidos: pd.Series) -> dict:
    t = pedidos[pedidos > 0]
    saida = {"pedidos": int(len(t)), "media_un": round(float(t.mean()), 2), "desvio_padrao_un": round(float(t.std()), 2),
             "quantis_un": {f"p{q * 100:g}": float(t.quantile(q)) for q in (0.5, 0.9, 0.99, 0.999)},
             "max_un": float(t.max()), "limiares": {}}
    for k in KS:
        lim = limiar_por_desvios(t, k)
        saida["limiares"][f"{k:g}_desvios"] = {"limiar_un": round(lim, 1), "pedidos_acima": int((t > lim).sum()),
                                               "pct_volume": round(100 * t[t > lim].sum() / t.sum(), 1)}
    saida["limiares"]["fixo_2000"] = {"limiar_un": LIMIAR_QTD_VENDA,
                                      "pedidos_acima": int((t > LIMIAR_QTD_VENDA).sum()),
                                      "pct_volume": round(100 * t[t > LIMIAR_QTD_VENDA].sum() / t.sum(), 1)}
    return saida


def _grafico_distribuicao(pedidos: pd.Series, caminho: str) -> None:
    fig, eixos = plt.subplots(len(UNIDADES), 1, figsize=(11, 4.2 * len(UNIDADES)))
    for ax, unidade in zip(eixos, UNIDADES):
        t = pedidos.xs(unidade, level="unidade")
        t = t[t > 0]
        bins = np.logspace(0, np.log10(t.max() * 1.1), 70)
        ax.hist(t, bins=bins, color=COR["hist"])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.axvline(t.mean(), color=COR["media"], lw=1.2,
                   label=f"média = {t.mean():.1f} un. (desvio-padrão {_n(t.std())})".replace(".", ",", 1))
        for k in KS:
            lim = limiar_por_desvios(t, k)
            ax.axvline(lim, color=COR[k], lw=1.6, ls="--",
                       label=f"média + {k:g} desvios = {_n(lim)} un. · {int((t > lim).sum())} pedidos, "
                             f"{100 * t[t > lim].sum() / t.sum():.1f}% do volume")
        ax.axvline(LIMIAR_QTD_VENDA, color=COR["fixo"], lw=1.2, ls=":",
                   label=f"fixo 2.000 un. (ADR-013) · {int((t > LIMIAR_QTD_VENDA).sum())} pedidos")
        ax.set_title(f"{unidade}: quantidade de cada pedido ({_n(len(t))} pedidos)", fontsize=10)
        ax.set_xlabel("quantidade do pedido (un., eixo em escala log)")
        ax.set_ylabel("pedidos (escala log)")
        ax.legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(caminho, dpi=130)
    plt.close(fig)


def limiar_no_tempo(df: pd.DataFrame) -> pd.DataFrame:
    """O limiar de cada loja recalculado com a base até o fim de cada mês — o que a carga de
    cada planilha mensal teria calculado."""
    pedidos = tamanho_dos_pedidos(df)
    datas = pedidos.index.get_level_values("emissao")
    lojas = pedidos.index.get_level_values("unidade")
    linhas = []
    for fim in pd.date_range(df["emissao"].min(), df["emissao"].max() + pd.offsets.MonthEnd(0), freq="ME"):
        for unidade in UNIDADES:
            ate = pedidos[(datas <= fim) & (lojas == unidade)]
            linhas.append({"ate": fim, "unidade": unidade, "pedidos": int((ate > 0).sum()),
                           **{f"limiar_k{k:g}": limiar_por_desvios(ate, k) for k in KS}})
    return pd.DataFrame(linhas)


def _grafico_no_tempo(tempo: pd.DataFrame, caminho: str) -> None:
    fig, ax = plt.subplots(figsize=(11, 3.8))
    for unidade, estilo in zip(UNIDADES, ("-", "--")):
        t = tempo[tempo["unidade"] == unidade]
        ax.plot(t["ate"], t["limiar_k4"], ls=estilo, marker="o", ms=3, color=COR[4.0],
                label=f"{unidade}: média + 4 desvios")
    ax.axhline(LIMIAR_QTD_VENDA, color=COR["fixo"], ls=":", label="fixo 2.000 un.")
    ax.set_ylabel("limiar (un.)")
    ax.set_title("Limiar de encomenda grande de cada loja recalculado com a base até o fim de cada mês", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(caminho, dpi=130)
    plt.close(fig)


def efeito_nas_series(df: pd.DataFrame, series: list[dict], regras: dict) -> pd.DataFrame:
    """Cada regra (limiar de cada loja) aplicada à base inteira, medida em cada série do treino."""
    marcas = {nome: marcar_encomendas_por_unidade(df, limiares) for nome, limiares in regras.items()}
    linhas = []
    for nome, marca in marcas.items():
        for s in series:
            base = df[df["unidade"] == s["unidade"]]
            coluna = "categoria" if s["nivel"] == "categoria" else "produto_cod"
            b = base[base[coluna] == s["serie"]]
            m = marca.loc[b.index]
            cal = pd.date_range(b["emissao"].min(), b["emissao"].max(), freq="D")
            fluxo = b[~m].groupby("emissao")["qtdade"].sum().reindex(cal, fill_value=0.0)
            vol_cons = b.loc[b["consumidor"], "qtdade"].sum()
            linhas.append({
                "regra": nome, "unidade": s["unidade"], "nivel": s["nivel"], "serie": s["serie"], "nome": s["nome"],
                "pedidos_marcados": int(b[m].groupby(CHAVE_VENDA).ngroups),
                "pct_volume": round(100 * b.loc[m, "qtdade"].sum() / b["qtdade"].sum(), 1),
                "cv_fluxo": round(fluxo.std() / fluxo.mean(), 2) if fluxo.mean() else None,
                "max_fluxo": round(float(fluxo.max()), 0),
                "pct_consumidor_tirado": round(100 * b.loc[m & b["consumidor"], "qtdade"].sum() / vol_cons, 1)
                if vol_cons else None,
            })
    return pd.DataFrame(linhas)


def main() -> None:
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(C.METRICS_DIR, exist_ok=True)
    df = carregar()
    pedidos = tamanho_dos_pedidos(df)

    dist = {u: distribuicao(t) for u, t in pedidos.groupby(level="unidade")}
    tempo = limiar_no_tempo(df)
    for u in dist:
        dist[u]["limiar_no_tempo_4_desvios_un"] = {f"{r.ate:%Y-%m}": round(r.limiar_k4, 1)
                                                   for r in tempo[tempo["unidade"] == u].itertuples()}
    with open(DISTRIBUICAO_JSON, "w", encoding="utf-8") as fh:
        json.dump(dist, fh, ensure_ascii=False, indent=2)
    _grafico_distribuicao(pedidos, os.path.join(PLOTS_DIR, "distribuicao_pedidos.png"))
    _grafico_no_tempo(tempo, os.path.join(PLOTS_DIR, "limiar_no_tempo.png"))

    series = series_do_treino(df)
    regras = {"fixo 2.000 un. (ADR-013)": {u: LIMIAR_QTD_VENDA for u in UNIDADES},
              **{f"{k:g} desvios da loja": {u: limiar_por_desvios(t, k) for u, t in pedidos.groupby(level="unidade")}
                 for k in KS}}
    efeito = efeito_nas_series(df, series, regras)
    efeito.to_csv(SERIES_CSV, sep=";", index=False, encoding="utf-8")

    pd.set_option("display.width", 220)
    print(json.dumps({u: {k: v for k, v in d.items() if k != "limiar_no_tempo_4_desvios_un"}
                      for u, d in dist.items()}, ensure_ascii=False, indent=1))
    print(efeito.pivot_table(index=["unidade", "nome"], columns="regra",
                             values=["pct_volume", "cv_fluxo", "pct_consumidor_tirado"]).round(2).to_string())
    print(f"[limiar_encomendas] {len(series)} séries · gráficos em {PLOTS_DIR}; "
          f"tabelas em {DISTRIBUICAO_JSON}, {SERIES_CSV}")


if __name__ == "__main__":
    main()
