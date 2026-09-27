"""Diagnóstico do baseline A0-crua: por que o SARIMA sobre a série crua pré-EDA foi fraco.

Lê o resultado salvo por `sarimax_serie_crua.py` (ordem, folds, hold-out) e gera os
gráficos 05–11 e um JSON com os números citados em
`docs/prediction/02-baseline_serie_crua_pre_eda.md`. Nada aqui altera o experimento: a
separação de encomendas é usada só para *explicar* os erros (regra do ADR-012, k = 5
dias típicos da unidade × categoria), não para treinar.

Uso (a partir de `ia-predictor/`), depois de rodar o baseline:
    python -m training_scripts.baseline.analise_serie_crua
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

from training_scripts.baseline import sarimax_serie_crua as base
from training_scripts.preprocessing.encomendas import limiares_encomenda, marcar_encomendas

COR_BALCAO = "#3a6ea5"
COR_ENCOMENDA = "#e67e22"
COR_MODELO = "#c0392b"
COR_SIMPLES = "#27ae60"
COR_REAL = "#444444"
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

FMT_MIL = mtick.FuncFormatter(lambda v, _: f"{v / 1000:.0f} mil" if abs(v) >= 1000 else f"{v:.0f}")


def carregar_linhas() -> pd.DataFrame:
    df = pd.read_csv(
        base.PRE_EDA_CSV, sep=";", decimal=",", encoding="latin-1",
        dtype={"produto_cod": str}, usecols=["emissao", "qtdade", "unidade", "categoria"],
    )
    df = df[df["categoria"].str.strip().str.lower() != "servico e taxa"].copy()
    df["data"] = pd.to_datetime(df["emissao"], dayfirst=True).dt.normalize()
    # Para a regra de encomenda, Garden Center conta como Jardim Canadá (mesma loja física).
    df["loja"] = np.where(df["unidade"].str.startswith("Itabirito"), "Itabirito", "Jardim Canadá")
    regra = df[["loja", "categoria", "data", "qtdade"]].rename(columns={"loja": "unidade"})
    df["encomenda"] = marcar_encomendas(regra, limiares_encomenda(regra, col_qtd="qtdade"), col_qtd="qtdade")
    return df


def salvar(fig, nome: str) -> None:
    fig.tight_layout()
    fig.savefig(os.path.join(base.PLOTS_DIR, nome), dpi=130)
    plt.close(fig)


def main() -> None:
    with open(os.path.join(base.METRICS_DIR, f"baseline_{base.NOME}.json"), encoding="utf-8") as fh:
        res = json.load(fh)
    order = tuple(res["ordem"]["order"])
    sorder = tuple(res["ordem"]["seasonal_order"])
    log = res["config"]["log1p"]

    serie, _ = base.carregar_serie()
    linhas = carregar_linhas()
    cal = serie.index
    enc = linhas[linhas["encomenda"]].groupby("data")["qtdade"].sum().reindex(cal, fill_value=0.0)
    balcao = serie - enc
    num: dict = {}

    # ------------------------------------------------------------------ #
    # 05 — De onde vêm os picos: balcão × encomendas grandes
    # ------------------------------------------------------------------ #
    num["encomendas"] = {
        "linhas": int(linhas["encomenda"].sum()),
        "pct_linhas": float(linhas["encomenda"].mean() * 100),
        "pct_volume": float(enc.sum() / serie.sum() * 100),
        "dias_com_encomenda": int((enc > 0).sum()),
        "maior_linha": float(linhas["qtdade"].max()),
        "variacao_serie_total_cv": float(serie.std() / serie.mean()),
        "variacao_balcao_cv": float(balcao.std() / balcao.mean()),
        "top10_dias_pct_encomenda": float(enc[serie.nlargest(10).index].sum() / serie.nlargest(10).sum() * 100),
    }
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True, sharey=True)
    axes[0].bar(cal, balcao, width=1, color=COR_BALCAO, label="vendas do dia a dia (balcão)")
    axes[0].bar(cal, enc, bottom=balcao, width=1, color=COR_ENCOMENDA, label="encomendas grandes")
    axes[0].set_title("O que o modelo recebeu: vendas do balcão + encomendas grandes misturadas")
    axes[0].legend(loc="upper left")
    axes[1].bar(cal, balcao, width=1, color=COR_BALCAO)
    axes[1].set_title("Só o balcão: a parte que dá para prever pelo calendário")
    for ax in axes:
        ax.yaxis.set_major_formatter(FMT_MIL)
        ax.set_ylabel("unidades vendidas / dia")
    salvar(fig, "05_picos_sao_encomendas.png")

    # ------------------------------------------------------------------ #
    # 06 — Onde o modelo mais erra (dentro do período de treino)
    # ------------------------------------------------------------------ #
    treino = serie.iloc[: -base.TEST_DAYS]
    z = np.log1p(treino) if log else treino
    ajuste = base.ajustar(z, order, sorder)
    fit = ajuste.fittedvalues
    fit = np.clip(np.expm1(fit) if log else fit, 0, None)
    erro_abs = (treino - fit).abs().iloc[base.M :]
    tem_enc = enc.reindex(erro_abs.index) > 0
    num["erros_treino"] = {
        "pct_dias_com_encomenda": float(tem_enc.mean() * 100),
        "pct_erro_nos_dias_com_encomenda": float(erro_abs[tem_enc].sum() / erro_abs.sum() * 100),
        "erro_medio_dia_com_encomenda": float(erro_abs[tem_enc].mean()),
        "erro_medio_dia_sem_encomenda": float(erro_abs[~tem_enc].mean()),
    }
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2), gridspec_kw={"width_ratios": [1, 1]})
    e = num["erros_treino"]
    axes[0].bar(["dias sem\nencomenda", "dias com\nencomenda"],
                [e["erro_medio_dia_sem_encomenda"], e["erro_medio_dia_com_encomenda"]],
                color=[COR_BALCAO, COR_ENCOMENDA])
    axes[0].set_title("Erro médio do modelo por tipo de dia")
    axes[0].yaxis.set_major_formatter(FMT_MIL)
    axes[0].set_ylabel("unidades de erro / dia")
    axes[1].bar(["parte dos dias", "parte do erro total"],
                [e["pct_dias_com_encomenda"], e["pct_erro_nos_dias_com_encomenda"]],
                color=[COR_ENCOMENDA, COR_ENCOMENDA], alpha=0.85)
    for i, v in enumerate([e["pct_dias_com_encomenda"], e["pct_erro_nos_dias_com_encomenda"]]):
        axes[1].text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=12)
    axes[1].set_ylim(0, 100)
    axes[1].set_title("Dias com encomenda: poucos dias, grande parte do erro")
    axes[1].yaxis.set_major_formatter(mtick.PercentFormatter())
    salvar(fig, "06_erro_concentrado_nas_encomendas.png")

    # ------------------------------------------------------------------ #
    # 07 — A "régua frouxa": por que o MASE parece bom
    # ------------------------------------------------------------------ #
    mae_naive_treino, _ = base.escala_naive(treino)
    teste = serie.iloc[-base.TEST_DAYS :]
    ho = res["holdout"]
    mae_naive_teste = res["holdout_naive_sazonal"]["mae"]
    num["regua"] = {
        "erro_regra_simples_no_treino": mae_naive_treino,
        "erro_regra_simples_no_teste": mae_naive_teste,
        "erro_modelo_no_teste": ho["mae"],
        "mase": ho["mase"],
        "mae_relativo_naive": ho["mae_relativo_naive"],
    }
    fig, ax = plt.subplots(figsize=(10, 4.5))
    barras = [mae_naive_treino, mae_naive_teste, ho["mae"]]
    rot = ["régua usada pelo MASE\n(regra simples no treino,\ncom as encomendas)",
           "regra simples\nno mês de teste", "nosso modelo\nno mês de teste"]
    ax.bar(rot, barras, color=["#999999", COR_SIMPLES, COR_MODELO])
    for i, v in enumerate(barras):
        ax.text(i, v + 60, f"{v:,.0f}".replace(",", "."), ha="center", fontsize=11)
    ax.set_ylabel("erro médio (unidades / dia)")
    ax.set_title(f"MASE = {ho['mase']:.2f} compara com a régua cinza; contra a régua justa (verde) o ganho é só "
                 f"{(1 - ho['mae_relativo_naive']) * 100:.0f}%", fontsize=10.5)
    salvar(fig, "07_regua_frouxa_do_mase.png")

    # ------------------------------------------------------------------ #
    # 08 — Faixa de segurança (IC 95%) grande demais
    # ------------------------------------------------------------------ #
    ho_csv = pd.read_csv(os.path.join(base.METRICS_DIR, f"baseline_{base.NOME}_holdout.csv"),
                         sep=";", decimal=",", parse_dates=["data"])
    num["faixa"] = {
        "largura_media": float((ho_csv["ic95_sup"] - ho_csv["ic95_inf"]).mean()),
        "venda_media_teste": float(ho_csv["real"].mean()),
        "maior_venda_teste": float(ho_csv["real"].max()),
        "maior_venda_historico": float(serie.max()),
    }
    fig, ax = plt.subplots(figsize=(13, 4.5))
    ax.fill_between(ho_csv["data"], ho_csv["ic95_inf"], ho_csv["ic95_sup"], color=COR_MODELO, alpha=0.15,
                    label="faixa de segurança do modelo (95%)")
    ax.plot(ho_csv["data"], ho_csv["real"], color=COR_REAL, marker="o", ms=3, label="venda real")
    ax.plot(ho_csv["data"], ho_csv["previsto"], color=COR_MODELO, lw=1.6, label="previsão")
    ax.axhline(num["faixa"]["venda_media_teste"], color=COR_REAL, ls=":", lw=1, label="venda média do mês")
    ax.yaxis.set_major_formatter(FMT_MIL)
    ax.set_title(f"Fevereiro/2026: a faixa vai de 0 a ~{num['faixa']['largura_media'] / 1000:.0f} mil em média, "
                 f"com venda real em torno de {num['faixa']['venda_media_teste'] / 1000:.1f} mil")
    ax.legend(loc="upper left")
    salvar(fig, "08_faixa_de_seguranca_inutil.png")

    # ------------------------------------------------------------------ #
    # 09 — Rodadas de teste: modelo × regra simples
    # ------------------------------------------------------------------ #
    folds = res["walk_forward"]["folds"]
    x = np.arange(len(folds))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(x - 0.2, [f["mae"] for f in folds], 0.4, color=COR_MODELO, label="nosso modelo")
    ax.bar(x + 0.2, [f["mae_naive"] for f in folds], 0.4, color=COR_SIMPLES,
           label="regra simples (repete a semana anterior)")
    ax.set_xticks(x, [f"rodada {i + 1}\n{pd.Timestamp(f['origem']):%d/%m} a "
                      f"{pd.Timestamp(f['origem']) + pd.Timedelta(days=13):%d/%m}" for i, f in enumerate(folds)])
    for i, f in enumerate(folds):
        venceu = f["mae"] < f["mae_naive"]
        ax.text(i, max(f["mae"], f["mae_naive"]) + 120, "modelo ganhou" if venceu else "modelo perdeu",
                ha="center", color=COR_MODELO if venceu else "#555", fontsize=10)
    ax.yaxis.set_major_formatter(FMT_MIL)
    ax.set_ylabel("erro médio (unidades / dia)")
    ax.set_title("4 rodadas de teste de 14 dias: o modelo ganha em 2 e perde em 2")
    ax.legend(loc="upper right")
    salvar(fig, "09_rodadas_modelo_vs_regra_simples.png")

    # ------------------------------------------------------------------ #
    # 10 — E se o teste caísse em dezembro (mês de picos)?
    # ------------------------------------------------------------------ #
    ini = pd.Timestamp("2025-12-01")
    tr_dez = serie[serie.index < ini]
    te_dez = serie[(serie.index >= ini) & (serie.index < ini + pd.Timedelta(days=28))]
    _, p_dez, lo_dez, hi_dez = base.prever(tr_dez, len(te_dez), order, sorder, log)
    naive_dez = base.naive_sazonal(tr_dez, len(te_dez))
    m_dez = base.metricas(te_dez.values, p_dez, lo_dez, hi_dez, tr_dez)
    m_dez_naive = base.metricas(te_dez.values, naive_dez, naive_dez, naive_dez, tr_dez)
    num["dezembro"] = {
        "periodo": f"{te_dez.index[0].date()} a {te_dez.index[-1].date()}",
        "erro_medio_modelo": m_dez["mae"],
        "erro_medio_regra_simples": m_dez_naive["mae"],
        "mae_relativo_naive": m_dez["mae"] / m_dez_naive["mae"],
        "mase": m_dez["mase"],
        "venda_total_real": float(te_dez.sum()),
        "venda_total_prevista": float(p_dez.sum()),
        "pct_previsto_do_real": float(p_dez.sum() / te_dez.sum() * 100),
        "pct_volume_encomendas": float(enc.reindex(te_dez.index).sum() / te_dez.sum() * 100),
    }
    fig, ax = plt.subplots(figsize=(13, 4.5))
    ax.bar(te_dez.index, balcao.reindex(te_dez.index), color=COR_BALCAO, label="real — balcão")
    ax.bar(te_dez.index, enc.reindex(te_dez.index), bottom=balcao.reindex(te_dez.index), color=COR_ENCOMENDA,
           label="real — encomendas grandes")
    ax.plot(te_dez.index, p_dez, color=COR_MODELO, lw=2, marker="o", ms=3, label="previsão do modelo")
    ax.yaxis.set_major_formatter(FMT_MIL)
    d = num["dezembro"]
    ax.set_title(f"Teste extra em dezembro/2025: o modelo previu {d['pct_previsto_do_real']:.0f}% do que foi vendido "
                 f"— as encomendas ({d['pct_volume_encomendas']:.0f}% do volume) passam batido", fontsize=10.5)
    ax.legend(loc="upper left")
    salvar(fig, "10_teste_extra_dezembro.png")

    # ------------------------------------------------------------------ #
    # 11 — Categorias com ritmos semanais diferentes, misturadas numa série
    # ------------------------------------------------------------------ #
    bal_lin = linhas[~linhas["encomenda"]]
    perfil = (bal_lin.groupby(["categoria", bal_lin["data"].dt.dayofweek])["qtdade"].sum().unstack(fill_value=0))
    perfil = perfil.div(perfil.sum(axis=1), axis=0) * 100
    num["perfil_semana_pct"] = {c: [round(v, 1) for v in perfil.loc[c].tolist()] for c in perfil.index}
    fig, ax = plt.subplots(figsize=(10, 4.5))
    w = 0.27
    for i, (cat, cor) in enumerate(zip(perfil.index, ["#6b8e23", "#d35400", "#3a6ea5"])):
        ax.bar(np.arange(7) + (i - 1) * w, perfil.loc[cat].values, w, label=cat, color=cor)
    ax.set_xticks(np.arange(7), DIAS_SEMANA)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylabel("% das vendas da semana")
    ax.set_title("Cada tipo de produto tem seu dia forte, mas a série única junta todos num padrão médio")
    ax.legend()
    salvar(fig, "11_ritmo_semanal_por_categoria.png")

    with open(os.path.join(base.METRICS_DIR, f"baseline_{base.NOME}_diagnostico.json"), "w", encoding="utf-8") as fh:
        json.dump(num, fh, ensure_ascii=False, indent=2)
    print(json.dumps(num, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
