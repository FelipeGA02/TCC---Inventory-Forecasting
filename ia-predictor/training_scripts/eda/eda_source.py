"""EDA 1 — Compreensão dos dados (antes da preparação).

Objeto: a base transacional consolidada (`data/processed/contas_a_receber.csv`,
1 linha por documento×produto), enriquecida com a taxonomia da Etapa 3.

Responde à fase "compreensão dos dados" do CRISP-DM: o que existe, com que
qualidade, e o que disso condiciona/valida as escolhas do pré-processamento.

Blocos:
  1. Volume e completude da fonte (arquivos, datas, meses, chaves)
  2. Perfil por unidade (volume, faturamento, histórico; composição de Jardim Canadá
     por CNPJ)
  3. Perfil por categoria / categoria_fina (share, nº de SKUs)
  4. Esparsidade da série diária por SKU  → justifica a camada L2
  5. Concentração de volume (curva de Pareto por SKU)
  6. Sazonalidade preliminar (transações por mês e por dia da semana)
  7. Qualidade de dados (qtdade<=0, nulos, encoding, integridade de documento)
  8. Triagem de exógenas nominais descartadas (pagamento / vendedor — ADR-010)

Saídas: PNGs em results/plots/eda/ e results/metrics/eda_source.json
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import _common as C


# --------------------------------------------------------------------------- #
def bloco_volume_completude(df: pd.DataFrame) -> dict:
    docs = df["doc_numero"].astype(str) + "|" + df["doc_tipo"].astype(str)
    meses = df["data"].dt.to_period("M")
    esperados = pd.period_range(df["data"].min(), df["data"].max(), freq="M")
    contagem_mes = meses.value_counts().sort_index()
    dias_calendario = pd.date_range(df["data"].min(), df["data"].max(), freq="D")
    dias_com_venda = df["data"].dt.normalize().nunique()

    ult_mes = esperados[-1]
    hist_mes = contagem_mes[contagem_mes.index.month == ult_mes.month]
    return {
        "linhas_documento_x_produto": len(df),
        "documentos_distintos": int(docs.nunique()),
        "skus_distintos": int(df["produto_cod"].nunique()),
        "arquivos_origem": sorted(df["arquivo_origem"].dropna().unique().tolist()),
        "n_arquivos_origem": int(df["arquivo_origem"].nunique()),
        "data_min": df["data"].min(),
        "data_max": df["data"].max(),
        "meses_esperados": len(esperados),
        "meses_presentes": int(contagem_mes.shape[0]),
        "meses_faltando": [str(p) for p in esperados if p not in set(contagem_mes.index)],
        "linhas_por_mes": {str(k): int(v) for k, v in contagem_mes.items()},
        "dias_calendario": len(dias_calendario),
        "dias_com_venda": int(dias_com_venda),
        "dias_sem_venda": int(len(dias_calendario) - dias_com_venda),
        "ultimo_mes": str(ult_mes),
        "ultimo_mes_vs_mesmo_mes_anos_anteriores": {
            str(k): int(v) for k, v in hist_mes.items()
        },
    }


def bloco_por_unidade(df: pd.DataFrame) -> dict:
    g = df.groupby("unidade")
    out = {}
    for u, d in g:
        out[u] = {
            "linhas": len(d),
            "skus_distintos": int(d["produto_cod"].nunique()),
            "qtd_total": float(d["qtdade_n"].sum()),
            "faturamento_tot_liq": float(d["tot_liq_n"].sum()),
            "data_min": d["data"].min(),
            "data_max": d["data"].max(),
            "dias_com_venda": int(d["data"].dt.normalize().nunique()),
        }
    return out


def _cnpj_jardim_canada(d: pd.DataFrame) -> pd.Series:
    return pd.Series(np.where(d["empresa"].str.contains("GARDEN", case=False, na=False),
                              "Garden Center", "Floricultura Canadá"), index=d.index)


def bloco_jardim_canada_por_cnpj(df: pd.DataFrame) -> dict:
    """Jardim Canadá reúne dois CNPJs: as vendas do Garden Center somam-se às da
    Floricultura. Volume (qtdade) mensal de cada um e da soma."""
    d = df[(df["unidade"] == "Jardim Canadá") & (df["categoria"] != C.NAO_PRODUTO)].dropna(subset=["data"])
    piv = (d.assign(mes=d["data"].dt.to_period("M").astype(str), cnpj=_cnpj_jardim_canada(d))
             .pivot_table(index="mes", columns="cnpj", values="qtdade_n",
                          aggfunc="sum", fill_value=0.0)
             .reindex(columns=["Floricultura Canadá", "Garden Center"], fill_value=0.0))
    piv["soma"] = piv.sum(axis=1)
    garden = d[_cnpj_jardim_canada(d) == "Garden Center"]
    return {
        "primeira_venda_garden_center": garden["data"].min(),
        "linhas_por_cnpj": {k: int(v) for k, v in _cnpj_jardim_canada(d).value_counts().items()},
        "volume_mensal": {m: {c: float(v) for c, v in r.items()} for m, r in piv.iterrows()},
    }


def bloco_por_categoria(df: pd.DataFrame) -> dict:
    def resumo(col):
        q = df.groupby(col)["qtdade_n"].sum().sort_values(ascending=False)
        n_sku = df.groupby(col)["produto_cod"].nunique()
        linhas = df.groupby(col).size()
        tot = q.sum()
        return {
            str(k): {
                "qtd_total": float(v),
                "share_qtd_pct": round(100 * v / tot, 2),
                "skus_distintos": int(n_sku[k]),
                "linhas": int(linhas[k]),
            }
            for k, v in q.items()
        }

    return {"categoria_l1": resumo("categoria"),
            "categoria_fina": resumo("categoria_fina")}


def bloco_esparsidade_sku(df: pd.DataFrame) -> dict:
    """Dias com venda e volume por SKU — o argumento para não modelar SKU direto."""
    g = df.groupby("produto_cod")
    dias_ativos = g["data"].apply(lambda s: s.dt.normalize().nunique())
    qtd = g["qtdade_n"].sum()
    n_vendas = g.size()
    span_dias = (df["data"].max() - df["data"].min()).days + 1

    # Regra de fallback L2 do pré-processamento: < 28 dias com venda OU < 8 vendas.
    frac_fallback = float(((dias_ativos < 28) | (n_vendas < 8)).mean())
    densidade = dias_ativos / span_dias
    return {
        "n_skus": int(len(dias_ativos)),
        "span_dias_base": int(span_dias),
        "dias_ativos_por_sku": {
            "media": float(dias_ativos.mean()),
            "mediana": float(dias_ativos.median()),
            "p10": float(dias_ativos.quantile(.10)),
            "p90": float(dias_ativos.quantile(.90)),
            "max": int(dias_ativos.max()),
        },
        "densidade_serie_sku": {  # dias ativos / dias do calendário
            "media": float(densidade.mean()),
            "mediana": float(densidade.median()),
            "p90": float(densidade.quantile(.90)),
            "p99": float(densidade.quantile(.99)),
        },
        "pct_skus_serie_>=50pct_dias": float((densidade >= .5).mean() * 100),
        "pct_skus_serie_>=20pct_dias": float((densidade >= .2).mean() * 100),
        "pct_skus_fallback_L2_rateio_uniforme": round(frac_fallback * 100, 1),
        "skus_com_1_unica_venda_pct": round(float((n_vendas == 1).mean()) * 100, 1),
    }


def bloco_pareto_sku(df: pd.DataFrame) -> dict:
    q = df.groupby("produto_cod")["qtdade_n"].sum().sort_values(ascending=False)
    q = q[q > 0]
    cum = q.cumsum() / q.sum()
    n = len(q)
    marcos = {}
    for alvo in (0.5, 0.8, 0.9, 0.95):
        k = int((cum <= alvo).sum()) + 1
        marcos[f"skus_para_{int(alvo*100)}pct_volume"] = k
        marcos[f"pct_skus_para_{int(alvo*100)}pct_volume"] = round(100 * k / n, 2)
    for topn in (20, 50, 100):
        marcos[f"volume_top{topn}_skus_pct"] = round(float(cum.iloc[min(topn, n) - 1]) * 100, 2)
    return marcos


def bloco_sazonalidade_preliminar(df: pd.DataFrame) -> dict:
    dias_pt = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    por_dow = df.groupby(df["data"].dt.weekday).size().reindex(range(7), fill_value=0)
    qtd_dow = df.groupby(df["data"].dt.weekday)["qtdade_n"].sum().reindex(range(7), fill_value=0)
    por_mes = df.groupby(df["data"].dt.month).size().reindex(range(1, 13), fill_value=0)
    return {
        "linhas_por_dia_semana": {dias_pt[i]: int(por_dow[i]) for i in range(7)},
        "qtd_por_dia_semana": {dias_pt[i]: float(qtd_dow[i]) for i in range(7)},
        "indice_fds_vs_media": round(
            float(por_dow[[5, 6]].mean() / por_dow.mean()), 3),
        "linhas_por_mes_do_ano": {int(m): int(v) for m, v in por_mes.items()},
        "mes_pico": int(por_mes.idxmax()),
        "mes_vale": int(por_mes.idxmin()),
    }


def bloco_qualidade(df: pd.DataFrame) -> dict:
    raw = C._read_csv_resiliente(C.CONSOLIDATED_CSV)
    q = df["qtdade_n"]
    nulos = {c: int(raw[c].isna().sum()) for c in raw.columns}

    # Integridade de documento: soma de tot_liq das linhas ≈ total_liquido_doc.
    doc = df.assign(_doc=df["doc_numero"].astype(str) + "|" + df["doc_tipo"].astype(str))
    por_doc = doc.groupby("_doc").agg(
        soma_linhas=("tot_liq_n", "sum"),
        total_doc=("total_liquido_doc_n", "first"),
    )
    dif = (por_doc["soma_linhas"] - por_doc["total_doc"]).abs()
    bate = float((dif <= 0.02).mean())

    emissao_nula = int(df["data"].isna().sum())

    # Encoding — dois arquivos, dois resultados:
    #  * a FONTE (data/processed/contas_a_receber.csv) é UTF-8 válido: "CANADÁ" = C3 81.
    #  * o CSV da Etapa 3 (output/contas_a_receber_taxonomia.csv) é gravado por
    #    `df.to_csv()` SEM encoding explícito -> neste Windows cai em cp1252, então
    #    `unidade='Jardim Canadá'` vira o byte 0xE1 (inválido em UTF-8). Quem ler
    #    esse CSV com o default do Python quebra. Defeito do pipeline, não do dado.
    fonte_utf8_ok = b"CANAD\xc3\x81" in open(C.CONSOLIDATED_CSV, "rb").read(20_000_000)
    tax_bytes = open(C.TAXONOMY_CSV, "rb").read()
    tax_utf8_ok = True
    try:
        tax_bytes.decode("utf-8")
    except UnicodeDecodeError:
        tax_utf8_ok = False
    unidade_derivada_limpa = bool((df["unidade"] == "Jardim Canadá").any()) and \
        not df["unidade"].astype(str).str.contains("�").any()
    return {
        "linhas_qtdade_menor_igual_zero": int((q <= 0).sum()),
        "linhas_qtdade_negativa": int((q < 0).sum()),
        "linhas_qtdade_fracionaria": int((q % 1 != 0).sum()),
        "linhas_qtdade_nao_numerica": int(q.isna().sum()),
        "linhas_emissao_nao_parseavel": emissao_nula,
        "linhas_tot_liq_negativo": int((df["tot_liq_n"] < 0).sum()),
        "nulos_por_coluna": nulos,
        "encoding_fonte_utf8_valido": bool(fonte_utf8_ok),
        "encoding_taxonomia_csv_utf8_valido": bool(tax_utf8_ok),
        "encoding_unidade_derivada_limpa": bool(unidade_derivada_limpa),
        "integridade_doc_ok_pct": round(bate * 100, 2),
        "integridade_doc_divergencia_media_reais": float(dif[dif > 0.02].mean())
        if (dif > 0.02).any() else 0.0,
        "documentos_avaliados": int(len(por_doc)),
    }


def bloco_exogenas_nominais(df: pd.DataFrame) -> dict:
    """Sinal aparente de `pagamento`/`vendedor` — descartados como exógenas do L1
    por ADR-010 (leakage / nível de agregação). Aqui só p/ registrar o descarte."""
    pag = df.groupby("pagamento")["qtdade_n"].sum().sort_values(ascending=False)
    pag_pct = (100 * pag / pag.sum()).round(2)
    vend = df["vendedor"].nunique()
    return {
        "formas_de_pagamento": int(df["pagamento"].nunique()),
        "mix_pagamento_top6_pct": {str(k): float(v) for k, v in pag_pct.head(6).items()},
        "vendedores_distintos": int(vend),
        "nota": "pagamento e vendedor NÃO entram como exógenas do L1 (ADR-010): "
                "atributo de transação, desconhecido no horizonte de previsão.",
    }


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
def _pct(v: float) -> str:
    return f"{v:.1f}%".replace(".", ",")


def _grafico_esparsidade(df: pd.DataFrame, plt) -> str:
    """Gráfico 03: em quantos dias cada SKU vendeu, com os cortes que a Análise 1 cita
    (mediana, histórico mínimo da L2, venda única, 20% e 50% dos dias) e a contagem de SKUs
    em cada um, em número real (sem notação 10ˣ)."""
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

    g = df.groupby("produto_cod")
    dias = g["data"].apply(lambda s: s.dt.normalize().nunique())
    n_vendas = g.size()
    n = len(dias)
    span = (df["data"].max() - df["data"].min()).days + 1
    mediana = float(dias.median())
    d20, d50 = int(np.ceil(.2 * span)), int(np.ceil(.5 * span))
    # Regra da L2: < 28 dias com venda OU < 8 vendas. Como nº de vendas ≥ nº de dias, quem tem
    # < 8 vendas já tem < 8 dias; o grupo é o mesmo de "< 28 dias". O painel (a) mostra só
    # dias; o critério de vendas fica no painel (b).
    sem_hist = int(((dias < 28) | (n_vendas < 8)).sum())
    assert sem_hist == int((dias < 28).sum())
    cortes = [
        ("venderam uma única vez\n(1 venda)", int((n_vendas == 1).sum()), "#C2185B"),
        ("menos de 8 vendas", int((n_vendas < 8).sum()), "#E57BA6"),
        ("sem histórico mínimo:\nmenos de 28 dias com venda", sem_hist, "#C2185B"),
        (f"venderam em ≥ 20% dos dias\n(≥ {d20} dias)", int((dias >= d20).sum()), "#00838F"),
        (f"venderam em ≥ 50% dos dias\n(≥ {d50} dias)", int((dias >= d50).sum()), "#00838F"),
    ]
    fmt_n = FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", "."))

    fig, (ax, axb) = plt.subplots(2, 1, figsize=(11, 9), gridspec_kw={"height_ratios": [1.3, 1.1]})

    # (a) histograma em faixas de 7 dias (o corte de 28 cai na borda de uma faixa),
    # eixo log com rótulos em número real
    bins = np.arange(0, dias.max() + 8, 7)
    cont, bordas, barras = ax.hist(dias.values, bins=bins, color="#455A64")
    for b, borda in zip(barras, bordas[:-1]):
        if borda < 28:
            b.set_color("#C2185B")
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(FixedLocator([1, 3, 10, 30, 100, 300, 1000, 3000]))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(fmt_n)
    ax.set_ylim(.7, cont.max() * 2.2)
    ax.annotate(f"{fmt_n(cont[0], None)} SKUs venderam em 1 a {int(bordas[1]) - 1} dias", (bordas[1], cont[0]),
                (60, cont.max() * .8), fontsize=8.5, va="center", color="#C2185B", fontweight="bold",
                arrowprops={"arrowstyle": "-", "lw": .6, "color": "#C2185B"})
    ax.axvline(mediana, color="#000", lw=1.1, ls=":")
    ax.text(mediana + 4, cont.max() * 1.6, f"mediana = {mediana:.0f} dias", fontsize=8.5)
    ax.axvline(28, color="#C2185B", lw=1.3, ls="--")
    ax.text(60, cont.max() * .2, f"28 dias: histórico mínimo\n{fmt_n(sem_hist, None)} SKUs "
            f"({_pct(sem_hist / n * 100)}) venderam\nem menos de 28 dias", fontsize=8.5, color="#C2185B")
    for d, (rot, k, _), y in ((d20, cortes[3], 40), (d50, cortes[4], 12)):
        ax.axvline(d, color="#00838F", lw=1.1, ls="--")
        ax.text(d + 5, y, f"≥ {d} dias: {k} SKUs ({_pct(k / n * 100)})", fontsize=8.5, color="#00838F")
    ax.set_xlim(0, bordas[-1])
    ax.set_title(f"(a) Em quantos dias cada SKU vendeu ({fmt_n(n, None)} SKUs, {span} dias; "
                 "barras de 7 dias, eixo vertical em escala log)", fontsize=10)
    ax.set_xlabel("dias distintos com ao menos 1 venda")
    ax.set_ylabel("nº de SKUs")

    # (b) os cortes da análise em barras, com contagem e % do total
    y = np.arange(len(cortes))[::-1]
    ax2 = axb
    ax2.barh(y, [k for _, k, _ in cortes], color=[c for _, _, c in cortes], height=.62)
    ax2.barh(y, [n] * len(cortes), color="#455A64", alpha=.08, height=.62, zorder=0)
    for yi, (_, k, _) in zip(y, cortes):
        ax2.text(k + n * .01, yi, f"{fmt_n(k, None)} SKUs  ·  {_pct(k / n * 100)}", va="center", fontsize=9)
    ax2.set_yticks(y, [r for r, _, _ in cortes], fontsize=8.5)
    ax2.xaxis.set_major_formatter(fmt_n)
    ax2.set_xlim(0, n * 1.05)
    ax2.set_xlabel(f"nº de SKUs (faixa clara = total de {fmt_n(n, None)})")
    ax2.set_title("(b) Os cortes citados na análise", fontsize=10)
    ax2.grid(axis="y", visible=False)
    fig.tight_layout()
    return C.savefig(fig, "03_esparsidade_dias_ativos_sku.png")


def graficos(df: pd.DataFrame, plt) -> list[str]:
    figs = []

    # 1. Transações por mês, empilhado por unidade
    piv = (df.assign(mes=df["data"].dt.to_period("M").dt.to_timestamp())
             .groupby(["mes", "unidade"]).size().unstack(fill_value=0)
             .reindex(columns=C.UNIDADES, fill_value=0))
    fig, ax = plt.subplots(figsize=(11, 4))
    base = np.zeros(len(piv))
    for u in C.UNIDADES:
        ax.bar(piv.index, piv[u], bottom=base, width=20, label=u, color=C.PALETA[u])
        base += piv[u].values
    for _, r in C.datas_comemorativas(range(df["data"].dt.year.min(),
                                            df["data"].dt.year.max() + 1)).iterrows():
        if r["evento"] in ("Dia das Mães", "Finados"):
            ax.axvline(r["data"], color="#B71C1C", lw=.7, ls=":", alpha=.5)
    ax.set_title("Transações por mês, por unidade (linhas verticais = Dia das Mães / Finados)")
    ax.set_ylabel("linhas documento×produto"); ax.legend(frameon=False, ncol=2)
    figs.append(C.savefig(fig, "01_transacoes_por_mes_unidade.png"))

    # 2. Sazonalidade semanal — qtd média por dia da semana
    dias_pt = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    fig, ax = plt.subplots(figsize=(7, 4))
    for u in C.UNIDADES:
        d = df[df["unidade"] == u]
        s = d.groupby(d["data"].dt.weekday)["qtdade_n"].mean().reindex(range(7))
        ax.plot(dias_pt, s.values, marker="o", label=u, color=C.PALETA[u])
    ax.set_title("Quantidade média por linha × dia da semana")
    ax.set_ylabel("qtd média / linha"); ax.legend(frameon=False)
    figs.append(C.savefig(fig, "02_sazonalidade_semanal_unidade.png"))

    # 3. Esparsidade por SKU — histograma de dias ativos, com os cortes citados na análise
    figs.append(_grafico_esparsidade(df, plt))

    # 4. Curva de Pareto do volume por SKU
    q = df.groupby("produto_cod")["qtdade_n"].sum().sort_values(ascending=False)
    q = q[q > 0]
    cum = np.cumsum(q.values) / q.values.sum()
    x = np.arange(1, len(q) + 1) / len(q) * 100
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(x, cum * 100, color="#2E7D32")
    ax.axhline(80, color="#999", lw=.8, ls=":")
    k80 = int((cum <= .8).sum()) + 1
    ax.axvline(100 * k80 / len(q), color="#C2185B", lw=1, ls="--",
               label=f"80% do volume = {k80} SKUs ({100*k80/len(q):.1f}%)")
    ax.set_title("Concentração do volume (qtd) por SKU — curva de Pareto")
    ax.set_xlabel("% dos SKUs (ordenados por volume)")
    ax.set_ylabel("% acumulado do volume"); ax.legend(frameon=False)
    figs.append(C.savefig(fig, "04_pareto_volume_sku.png"))

    # 5. Volume por categoria_fina
    q = df.groupby("categoria_fina")["qtdade_n"].sum().sort_values()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(q.index, q.values, color="#00838F")
    ax.set_title("Volume total (qtd) por categoria_fina")
    ax.set_xlabel("soma de qtdade")
    figs.append(C.savefig(fig, "05_volume_categoria_fina.png"))

    # 6. Jardim Canadá por CNPJ — a unidade é a soma da Floricultura com o Garden Center
    d = df[(df["unidade"] == "Jardim Canadá") & (df["categoria"] != C.NAO_PRODUTO)].dropna(subset=["data"])
    piv = (d.assign(mes=d["data"].dt.to_period("M").dt.to_timestamp(), cnpj=_cnpj_jardim_canada(d))
             .pivot_table(index="mes", columns="cnpj", values="qtdade_n", aggfunc="sum", fill_value=0.0)
             .reindex(columns=["Floricultura Canadá", "Garden Center"], fill_value=0.0))
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.bar(piv.index, piv["Floricultura Canadá"], width=20, label="Floricultura Canadá",
           color=C.PALETA["Jardim Canadá"])
    ax.bar(piv.index, piv["Garden Center"], bottom=piv["Floricultura Canadá"], width=20,
           label="Garden Center", color="#00838F")
    ax.set_title("Jardim Canadá: volume mensal por CNPJ (a unidade é a soma dos dois)")
    ax.set_ylabel("soma de qtdade"); ax.legend(frameon=False)
    figs.append(C.savefig(fig, "06_jardim_canada_por_cnpj.png"))

    return figs


# --------------------------------------------------------------------------- #
def main() -> dict:
    plt = C.setup_plotting()
    df = C.load_transacoes()

    resultado = {
        "gerado_em": pd.Timestamp.now().isoformat(timespec="seconds"),
        "fonte": {
            "consolidado": C.os.path.relpath(C.CONSOLIDATED_CSV, C.REPO_ROOT).replace(C.os.sep, "/"),
            "taxonomia": C.os.path.relpath(C.TAXONOMY_CSV, C.REPO_ROOT).replace(C.os.sep, "/"),
        },
        "1_volume_completude": bloco_volume_completude(df),
        "2_por_unidade": bloco_por_unidade(df),
        "2b_jardim_canada_por_cnpj": bloco_jardim_canada_por_cnpj(df),
        "3_por_categoria": bloco_por_categoria(df),
        "4_esparsidade_sku": bloco_esparsidade_sku(df),
        "5_pareto_sku": bloco_pareto_sku(df),
        "6_sazonalidade_preliminar": bloco_sazonalidade_preliminar(df),
        "7_qualidade": bloco_qualidade(df),
        "8_exogenas_nominais": bloco_exogenas_nominais(df),
    }
    resultado["graficos"] = graficos(df, plt)
    path = C.dump_metrics("eda_source.json", resultado)

    v = resultado["1_volume_completude"]
    print(f"[eda_source] {C.fmt_int(v['linhas_documento_x_produto'])} linhas · "
          f"{C.fmt_int(v['skus_distintos'])} SKUs · {v['meses_presentes']}/{v['meses_esperados']} meses · "
          f"{v['data_min'].date()} → {v['data_max'].date()}")
    print(f"[eda_source] meses faltando: {v['meses_faltando'] or 'nenhum'}")
    s = resultado["4_esparsidade_sku"]
    print(f"[eda_source] SKU: mediana {s['dias_ativos_por_sku']['mediana']:.0f} dias ativos · "
          f"{s['pct_skus_fallback_L2_rateio_uniforme']}% cairiam no fallback L2")
    qa = resultado["7_qualidade"]
    print(f"[eda_source] qualidade: {C.fmt_int(qa['linhas_qtdade_menor_igual_zero'])} linhas qtd<=0 · "
          f"integridade doc {qa['integridade_doc_ok_pct']}%")
    print(f"[eda_source] encoding: fonte UTF-8 ok={qa['encoding_fonte_utf8_valido']} · "
          f"taxonomia.csv UTF-8 ok={qa['encoding_taxonomia_csv_utf8_valido']} "
          f"(defeito do pipeline se False) · unidade derivada limpa={qa['encoding_unidade_derivada_limpa']}")
    print(f"[eda_source] métricas: {path}  ·  {len(resultado['graficos'])} gráficos")
    return resultado


if __name__ == "__main__":
    main()
