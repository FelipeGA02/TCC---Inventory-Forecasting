"""EDA 5 — Classificação de demanda por SKU (Syntetos, Boylan & Croston, 2005).

Responde, com um critério da literatura em vez de um limiar arbitrário do projeto, à
pergunta que sustenta a arquitetura hierárquica L1→L2: a série diária de um SKU tem
padrão que um SARIMAX consegue estimar, ou é "esparsa demais" no sentido formal do termo?

## O critério

Syntetos, A.A.; Boylan, J.E.; Croston, J.D. (2005). "On the categorization of demand
patterns." Journal of the Operational Research Society, 56(5), 495–503.
https://doi.org/10.1057/palgrave.jors.2601841

Classifica qualquer série de demanda em 4 padrões a partir de dois indicadores:

  * **ADI** (average inter-demand interval) — span da série (do 1º ao último dia com
    venda) dividido pelo nº de dias com venda. ADI alto = venda esparsa no tempo.
  * **CV²** (coeficiente de variação ao quadrado) da quantidade vendida, calculado só
    nos dias COM venda. CV² alto = tamanho do pedido muito variável quando ocorre.

Cortes do artigo: ADI = 1,32 · CV² = 0,49 (os valores para os quais o erro quadrático
médio de SES e de Croston se igualam — ver a derivação no artigo original).

|            | CV² baixo (< 0,49) | CV² alto (≥ 0,49) |
| ---------- | ------------------ | ------------------ |
| ADI baixo (< 1,32) | **suave** (smooth) — SES/SARIMAX servem bem | **errático** (erratic) — regular no tempo, tamanho instável |
| ADI alto (≥ 1,32)  | **intermitente** (intermittent) — Croston/SBA/TSB | **lumpy** — o pior caso: nem quando nem quanto é regular |

SARIMAX pressupõe uma série contínua e razoavelmente regular: serve bem a séries
**suaves**, tolera **erráticas** (com log1p), mas SES/ARIMA tendem a ter MSE pior que
Croston nos quadrantes **intermitente** e **lumpy** — é exatamente a fronteira que o
artigo deriva.

## Como isso justifica o agrupamento

Aplicamos o mesmo critério a três níveis: (1) cada SKU isolado; (2) as 6 séries de
desagregação `unidade × categoria`; (3) as 2 séries `unidade` que o L1 de fato ajusta
(ADR-011 §4). Se a maioria dos SKUs cai em intermitente/lumpy e as séries agregadas caem em
suave/errático, o critério da literatura confirma — não apenas qualitativamente, como já
dizia `01-pre_processing.md` §5.2, mas com o instrumento padrão da área — que agregar até
`unidade` (e não parar em categoria, nem ir até SKU) é o nível de granularidade correto
para o SARIMAX, e que Croston/TSB/SBA (já na trilha de comparação do projeto, ADR-009 §3)
são a escolha adequada para o nível de SKU.

Saídas: results/plots/eda/24_classificacao_demanda_sku.png e
results/metrics/eda_classificacao_sku.json
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import _common as C

ADI_CORTE = 1.32
CV2_CORTE = 0.49

QUADRANTE_COR = {
    "suave": "#2E7D32", "erratico": "#F9A825", "intermitente": "#1565C0", "lumpy": "#C2185B",
}


def _classifica(adi: pd.Series, cv2: pd.Series) -> pd.Series:
    baixo_adi, baixo_cv2 = adi < ADI_CORTE, cv2 < CV2_CORTE
    return pd.Series(
        np.select(
            [baixo_adi & baixo_cv2, baixo_adi & ~baixo_cv2, ~baixo_adi & baixo_cv2],
            ["suave", "erratico", "intermitente"],
            default="lumpy",
        ),
        index=adi.index,
    )


def _adi_cv2_por_sku(df: pd.DataFrame) -> pd.DataFrame:
    """Um SKU = todas as suas vendas em todas as unidades somadas por dia (a granularidade
    em que o catálogo é de fato gerido — o mesmo produto_cod é o mesmo item físico nas
    duas unidades). Span = do 1º ao último dia com venda do próprio SKU (span="par",
    mesma convenção de `serie_diaria()`) — não o calendário inteiro: um SKU descontinuado
    ou lançado no meio do período não deve ter ADI inflado por dias em que nunca poderia
    vender."""
    d = df.dropna(subset=["data"])
    por_dia = d.groupby(["produto_cod", d["data"].dt.normalize()])["qtdade_n"].sum()
    por_dia = por_dia[por_dia > 0]
    g = por_dia.groupby(level=0)
    dias_venda = g.size()
    primeiro = g.apply(lambda s: s.index.get_level_values(1).min())
    ultimo = g.apply(lambda s: s.index.get_level_values(1).max())
    span = (ultimo - primeiro).dt.days + 1
    media = g.mean()
    # ddof=1 exige >= 2 observações; SKU com 1 único dia de venda não tem CV² definido.
    dp = g.std(ddof=1)
    out = pd.DataFrame({
        "dias_com_venda": dias_venda, "span_dias": span,
        "adi": span / dias_venda, "cv2": (dp / media) ** 2,
        "volume_total": g.sum(),
    })
    out["classificavel"] = out["dias_com_venda"] >= 2
    out.loc[out["classificavel"], "classe"] = _classifica(
        out.loc[out["classificavel"], "adi"], out.loc[out["classificavel"], "cv2"])
    return out


def _adi_cv2_desagregacao(df: pd.DataFrame) -> pd.DataFrame:
    """O mesmo critério aplicado às 6 séries de desagregação `unidade × categoria`
    (span="par", como em `eda_series.py`) — não são mais série L1 própria (ADR-011 §4),
    mas ilustram como a classificação já melhora um nível acima do SKU."""
    linhas = []
    for u, c in C.pares_l1(df):
        s = C.serie_diaria(df, u, c, span="par")
        nz = s[s > 0]
        adi = len(s) / len(nz)
        cv2 = (nz.std(ddof=1) / nz.mean()) ** 2
        linhas.append({"par": f"{u} · {c}", "dias_com_venda": len(nz), "span_dias": len(s),
                       "adi": adi, "cv2": cv2, "classe": _classifica(pd.Series([adi]), pd.Series([cv2])).iloc[0]})
    return pd.DataFrame(linhas).set_index("par")


def _adi_cv2_das_series_l1(df: pd.DataFrame) -> pd.DataFrame:
    """O mesmo critério aplicado às 2 séries `unidade` que o L1 de fato ajusta
    (ADR-011 §4; ver `eda_series_unidade.py`)."""
    linhas = []
    for u in C.UNIDADES:
        s = C.serie_unidade(df, u, span="par")
        nz = s[s > 0]
        adi = len(s) / len(nz)
        cv2 = (nz.std(ddof=1) / nz.mean()) ** 2
        linhas.append({"unidade": u, "dias_com_venda": len(nz), "span_dias": len(s),
                       "adi": adi, "cv2": cv2, "classe": _classifica(pd.Series([adi]), pd.Series([cv2])).iloc[0]})
    return pd.DataFrame(linhas).set_index("unidade")


def graficos(sku: pd.DataFrame, desagr: pd.DataFrame, l1: pd.DataFrame, plt) -> list[str]:
    fig, ax = plt.subplots(figsize=(8, 6.5))
    cl = sku[sku["classificavel"]]
    for classe, cor in QUADRANTE_COR.items():
        d = cl[cl["classe"] == classe]
        ax.scatter(d["adi"], d["cv2"].clip(upper=5), s=6, alpha=.35, color=cor, label=f"{classe} (SKU, n={len(d)})")
    ax.scatter(desagr["adi"], desagr["cv2"], s=70, marker="D", color="#455A64", zorder=4,
               label="desagregação (unidade × categoria)")
    ax.scatter(l1["adi"], l1["cv2"], s=200, marker="*", color="black", zorder=5,
               label="séries L1 (unidade)")
    # Ordena por CV² para escalonar o deslocamento vertical dos rótulos e evitar sobreposição.
    for i, (par, r) in enumerate(desagr.sort_values("cv2").iterrows()):
        ax.annotate(par, (r["adi"], r["cv2"]), fontsize=6.5, color="#455A64",
                    xytext=(8, -4 + 4 * (i % 3)), textcoords="offset points")
    for u, r in l1.iterrows():
        ax.annotate(u, (r["adi"], r["cv2"]), fontsize=8, fontweight="bold",
                    xytext=(8, 6), textcoords="offset points")
    ax.axvline(ADI_CORTE, color="#555", lw=.8, ls="--")
    ax.axhline(CV2_CORTE, color="#555", lw=.8, ls="--")
    ax.set_xscale("log"); ax.set_yscale("symlog", linthresh=1)
    ax.set_xlim(right=ax.get_xlim()[1] * 3)
    ax.set_xlabel("ADI — intervalo médio entre vendas (dias, escala log)")
    ax.set_ylabel("CV² — variabilidade do tamanho da venda (escala log, cortada em 5)")
    ax.set_title("Classificação de demanda (Syntetos, Boylan & Croston, 2005)\n"
                  "SKU individual × desagregação × séries do L1")
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    return [C.savefig(fig, "24_classificacao_demanda_sku.png")]


def main() -> dict:
    plt = C.setup_plotting()
    df = C.load_transacoes()
    df = df[df["categoria"] != C.NAO_PRODUTO]

    sku = _adi_cv2_por_sku(df)
    desagr = _adi_cv2_desagregacao(df)
    l1 = _adi_cv2_das_series_l1(df)

    cl = sku[sku["classificavel"]]
    dist_skus = (cl["classe"].value_counts(normalize=True) * 100).round(1)
    dist_volume = (cl.groupby("classe")["volume_total"].sum() / cl["volume_total"].sum() * 100).round(1)
    n_um_dia = int((~sku["classificavel"]).sum())

    resultado = {
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "referencia": "Syntetos, A.A.; Boylan, J.E.; Croston, J.D. (2005). On the categorization "
                      "of demand patterns. Journal of the Operational Research Society, 56(5), "
                      "495-503. https://doi.org/10.1057/palgrave.jors.2601841",
        "cortes": {"ADI": ADI_CORTE, "CV2": CV2_CORTE},
        "n_skus_total": int(len(sku)),
        "n_skus_um_unico_dia_de_venda_nao_classificavel": n_um_dia,
        "pct_skus_um_unico_dia_de_venda": round(n_um_dia / len(sku) * 100, 1),
        "distribuicao_skus_classificaveis_pct": dist_skus.to_dict(),
        "distribuicao_volume_classificaveis_pct": dist_volume.to_dict(),
        "series_l1_unidade": l1.reset_index().to_dict(orient="records"),
        "series_desagregacao_unidade_x_categoria": desagr.reset_index().to_dict(orient="records"),
    }
    resultado["graficos"] = graficos(sku, desagr, l1, plt)
    path = C.dump_metrics("eda_classificacao_sku.json", resultado)

    print("[eda_classificacao_sku] cortes: ADI >=", ADI_CORTE, "· CV2 >=", CV2_CORTE)
    print(f"[eda_classificacao_sku] {n_um_dia} SKUs ({resultado['pct_skus_um_unico_dia_de_venda']}%) "
          f"tem 1 unico dia de venda — CV2 indefinido, nao classificavel")
    print("[eda_classificacao_sku] distribuicao dos SKUs classificaveis (% de SKUs | % do volume):")
    for classe in ("suave", "erratico", "intermitente", "lumpy"):
        print(f"[eda_classificacao_sku]   {classe:<14}{dist_skus.get(classe, 0):>6}%  |  "
              f"{dist_volume.get(classe, 0):>6}% do volume")
    print("[eda_classificacao_sku] series L1 (unidade):")
    for u, r in l1.iterrows():
        print(f"[eda_classificacao_sku]   {u:<18} ADI={r['adi']:.2f} CV2={r['cv2']:.2f}  -> {r['classe']}")
    print("[eda_classificacao_sku] series de desagregacao (unidade x categoria):")
    for par, r in desagr.iterrows():
        print(f"[eda_classificacao_sku]   {par:<34} ADI={r['adi']:.2f} CV2={r['cv2']:.2f}  -> {r['classe']}")
    print(f"[eda_classificacao_sku] metricas: {path}  ·  {len(resultado['graficos'])} grafico(s)")
    return resultado


if __name__ == "__main__":
    main()
