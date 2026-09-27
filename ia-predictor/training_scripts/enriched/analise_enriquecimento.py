"""Diagnóstico do treino enriquecido (A0/A1/B sobre a série crua): o que melhorou e por que
ainda não é bom.

Lê os resultados salvos por `sarimax_serie_crua_enriquecida.py` e gera os gráficos 09–12 e
um JSON com os números citados em `docs/prediction/03-enriquecimento_serie_crua.md`. As
encomendas são marcadas pela regra do ADR-012 (k = 5), só para explicar os erros.

Uso (a partir de `ia-predictor/`), depois de rodar o experimento:
    python -m training_scripts.enriched.analise_enriquecimento
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
from training_scripts.baseline.analise_serie_crua import carregar_linhas
from training_scripts.enriched import sarimax_serie_crua_enriquecida as exp

COR_FERIADO = "#f5b041"
COR_ENCOMENDA = "#e67e22"
COR_BALCAO = "#3a6ea5"
COR_OUTROS = "#bbbbbb"
FMT_MIL = exp.FMT_MIL


def salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(os.path.join(exp.PLOTS_DIR, nome), dpi=130)
    plt.close(fig)


def main() -> None:
    with open(os.path.join(exp.METRICS_DIR, f"{exp.NOME}.json"), encoding="utf-8") as fh:
        res = json.load(fh)["modelos"]
    prev = pd.read_csv(os.path.join(exp.METRICS_DIR, f"{exp.NOME}_previsoes.csv"), sep=";", decimal=",",
                       parse_dates=["data"])
    serie, _ = base.carregar_serie()
    X, feriado = exp.montar_exogenas(serie.index)
    linhas = carregar_linhas()
    enc = linhas[linhas["encomenda"]].groupby("data")["qtdade"].sum().reindex(serie.index, fill_value=0.0)
    balcao = serie - enc
    num: dict = {}

    # ------------------------------------------------------------------ #
    # 09 — De onde vinha a faixa larga: resíduos (escala do modelo) por tipo de dia
    # ------------------------------------------------------------------ #
    tr = serie.iloc[:-base.TEST_DAYS]
    z = np.log1p(tr)
    fatias = {}
    for nome, cols in (("A0_crua", []), ("A1_crua_calendario", exp.COLS_CAL)):
        cfg = res[nome]["ordem_holdout"]
        r = exp.ajustar(z, X.loc[tr.index, cols] if cols else None, tuple(cfg["order"]),
                        tuple(cfg["seasonal_order"]))
        e2 = r.resid.iloc[base.M + 1:] ** 2
        f = feriado.reindex(e2.index).values
        en = (enc.reindex(e2.index) > 0).values & ~f
        fatias[nome] = {"feriados": float(e2[f].sum()), "dias_com_encomenda": float(e2[en].sum()),
                        "demais_dias": float(e2[~f & ~en].sum()), "sigma2": float(r.params["sigma2"])}
    num["faixa_residuos2"] = fatias
    fig, ax = plt.subplots(figsize=(10, 4.8))
    base_y = np.zeros(2)
    modelos = ("A0_crua", "A1_crua_calendario")
    tot = np.array([sum(fatias[n][k] for k in ("feriados", "dias_com_encomenda", "demais_dias")) for n in modelos])
    rot = []
    for n, t in zip(modelos, tot):
        f = fatias[n]
        rot.append(f"{exp.ROTULO[n]}\nferiados {f['feriados'] / t * 100:.0f}% · encomendas "
                   f"{f['dias_com_encomenda'] / t * 100:.0f}% · demais {f['demais_dias'] / t * 100:.0f}%")
    for chave, cor, leg in (("feriados", COR_FERIADO, "feriados (loja fechada)"),
                            ("dias_com_encomenda", COR_ENCOMENDA, "dias com encomenda grande"),
                            ("demais_dias", COR_OUTROS, "demais dias")):
        v = np.array([fatias[n][chave] for n in modelos])
        ax.bar(rot, v, bottom=base_y, color=cor, label=leg, width=0.55)
        base_y += v
    ax.set_ylabel("\"surpresa\" total do modelo no treino\n(soma dos erros² na escala do modelo)")
    ax.set_title("O que alargava a faixa de segurança: os feriados, não as encomendas")
    ax.legend()
    salvar(fig, "09_causa_da_faixa_larga.png")

    # ------------------------------------------------------------------ #
    # 10 — Mudança de nível: o A1 fica preso na média do histórico
    # ------------------------------------------------------------------ #
    ano = prev[prev["avaliacao"] == "ano_26"]
    sem = {}
    for nome in ("A0_crua", "A1_crua_calendario"):
        d = ano[ano["modelo"] == nome].set_index("data")
        aberto = d["real"] > 0
        sem[nome] = d.loc[aberto, "prev"].resample("W").mean()
        sem["real"] = d.loc[aberto, "real"].resample("W").mean()
    bal_sem = balcao[(balcao.index >= ano["data"].min()) & (serie > 0)].resample("W").mean()
    media_treino = float(serie.iloc[:len(serie) - exp.N_FOLDS_ANO * base.HORIZON]
                         [lambda s: s > 0].mean())
    por_rodada = {}
    for nome in ("A0_crua", "A1_crua_calendario"):
        d = ano[ano["modelo"] == nome]
        g = d.groupby("rodada").agg(ini=("data", "min"), p=("prev", "sum"), r=("real", "sum"))
        por_rodada[nome] = g
    g1 = por_rodada["A1_crua_calendario"]
    num["nivel"] = {
        "media_dia_aberto_treino_ano": media_treino,
        "a1_rodadas_acima_de_110pct": int((g1["p"] / g1["r"] > 1.10).sum()),
        "a1_rodadas_abaixo_de_90pct": int((g1["p"] / g1["r"] < 0.90).sum()),
        "a1_previsto_sobre_real_por_rodada": [round(float(v), 3) for v in (g1["p"] / g1["r"])],
    }
    fig, axes = plt.subplots(2, 1, figsize=(13, 7.5), sharex=True)
    ax = axes[0]
    ax.plot(sem["real"].index, sem["real"].values, color="#333", lw=1.8, label="venda real (dias abertos)")
    ax.plot(bal_sem.index, bal_sem.values, color=COR_BALCAO, lw=1, ls=":", label="real só balcão (sem encomendas)")
    ax.plot(sem["A0_crua"].index, sem["A0_crua"].values, color=exp.COR["A0_crua"], lw=1.4, label=exp.ROTULO["A0_crua"])
    ax.plot(sem["A1_crua_calendario"].index, sem["A1_crua_calendario"].values, color=exp.COR["A1_crua_calendario"],
            lw=1.8, label=exp.ROTULO["A1_crua_calendario"])
    ax.yaxis.set_major_formatter(FMT_MIL)
    ax.set_ylabel("média por dia aberto, na semana")
    ax.set_title("As previsões ficam quase planas: o modelo não acompanha as fases de alta e de baixa")
    ax.legend(fontsize=8, loc="upper left")
    ax = axes[1]
    for nome in ("A0_crua", "A1_crua_calendario"):
        g = por_rodada[nome]
        ax.plot(g["ini"], g["p"] / g["r"] * 100, marker="o", ms=4, color=exp.COR[nome], label=exp.ROTULO[nome])
    ax.axhline(100, color="#27ae60", ls="--", lw=1.2, label="previsão = venda real")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylabel("previsto ÷ vendido na rodada")
    ax.set_title("Acima de 100%: previu demais (fases fracas) · abaixo: previu de menos (picos e fases fortes)")
    ax.legend(fontsize=8)
    salvar(fig, "10_mudanca_de_nivel.png")

    # ------------------------------------------------------------------ #
    # 11 — Abertura excepcional: os únicos domingos/feriados com venda
    # ------------------------------------------------------------------ #
    # Efeito colateral no A1: a janela "7 dias até a data" espalha pela semana o salto do dia
    a1 = ano[ano["modelo"] == "A1_crua_calendario"].set_index("data")
    erro_total = float((a1["real"] - a1["prev"]).abs().sum())
    semanas = {}
    for nome, ini, fim in (("Dia das Mães 2025", "2025-05-05", "2025-05-11"),
                           ("Finados 2025", "2025-10-27", "2025-11-02")):
        w = a1.loc[ini:fim]
        semanas[nome] = {"previsto": float(w["prev"].sum()), "real": float(w["real"].sum()),
                         "erro": float((w["real"] - w["prev"]).abs().sum()),
                         "previsto_dia_util_medio": float(w.loc[w.index.dayofweek < 5, "prev"].mean())}
    num["a1_semanas_de_data"] = {**semanas, "pct_do_erro_do_ano": sum(v["erro"] for v in semanas.values())
                                 / erro_total * 100}

    fechado_normal = (serie.index.dayofweek == 6) | feriado.values
    excecoes = serie[fechado_normal & (serie > 0)]
    num["abertura_excepcional"] = {str(d.date()): float(v) for d, v in excecoes.items()}
    comp = []
    for nome, dia in (("Dia das Mães 2024", "2024-05-12"), ("Dia das Mães 2025", "2025-05-11"),
                      ("Finados 2024", "2024-11-02"), ("Finados 2025", "2025-11-02")):
        d = pd.Timestamp(dia)
        ab = (serie.index.dayofweek < 6) & (serie > 0).values
        w = (serie.index >= d - pd.Timedelta(days=6)) & (serie.index < d) & ab
        ref = (serie.index >= d - pd.Timedelta(days=60)) & (serie.index < d - pd.Timedelta(days=6)) & ab
        comp.append((nome, float(balcao[w].mean() / balcao[ref].mean() - 1) * 100, float(serie[d])))
    num["semana_antes_balcao_vs_2meses_pct"] = {n: round(v, 1) for n, v, _ in comp}
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), gridspec_kw={"width_ratios": [1.1, 1]})
    ax = axes[0]
    b = ax.bar([n for n, _, _ in comp], [v for _, _, v in comp], color="#c0392b")
    ax.bar_label(b, fmt="%.0f")
    ax.set_ylabel("unidades vendidas no próprio dia")
    ax.set_title("A loja abre no próprio dia\n(domingo ou feriado, em que normalmente vende 0)")
    ax.tick_params(axis="x", labelsize=8)
    ax = axes[1]
    cores = ["#27ae60" if v >= 0 else "#c0392b" for _, v, _ in comp]
    b = ax.bar([n for n, _, _ in comp], [v for _, v, _ in comp], color=cores)
    ax.bar_label(b, fmt="%+.0f%%")
    ax.axhline(0, color="#333", lw=0.8)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_title("Na semana anterior o efeito é bem menor e irregular\n(balcão vs 2 meses antes)")
    ax.tick_params(axis="x", labelsize=8)
    salvar(fig, "11_abertura_excepcional.png")

    # ------------------------------------------------------------------ #
    # 12 — Quanto do erro do A1 no ano cai em dias com encomenda
    # ------------------------------------------------------------------ #
    d1 = ano[ano["modelo"] == "A1_crua_calendario"].set_index("data")
    e = (d1["real"] - d1["prev"]).abs()
    tem = enc.reindex(d1.index) > 0
    e_bal = (balcao.reindex(d1.index) - d1["prev"]).abs()
    num["erro_ano_a1"] = {
        "pct_dias_com_encomenda": float(tem.mean() * 100),
        "pct_erro_em_dias_com_encomenda": float(e[tem].sum() / e.sum() * 100),
        "mae_dias_com_encomenda": float(e[tem].mean()),
        "mae_dias_sem_encomenda": float(e[~tem].mean()),
        "mae_contra_so_balcao": float(e_bal.mean()),
        "pct_volume_encomenda_no_ano": float(enc.reindex(d1.index).sum() / d1["real"].sum() * 100),
    }
    dz = prev[(prev["avaliacao"] == "dezembro") & (prev["modelo"] == "A1_crua_calendario")].set_index("data")
    num["dezembro_a1"] = {
        "previsto": float(dz["prev"].sum()), "real": float(dz["real"].sum()),
        "real_balcao": float(balcao.reindex(dz.index).sum()),
        "previsto_sobre_balcao_pct": float(dz["prev"].sum() / balcao.reindex(dz.index).sum() * 100),
    }
    a = num["erro_ano_a1"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.3))
    ax = axes[0]
    b = ax.bar(["dias sem\nencomenda", "dias com\nencomenda"], [a["mae_dias_sem_encomenda"], a["mae_dias_com_encomenda"]],
               color=[COR_BALCAO, COR_ENCOMENDA])
    ax.bar_label(b, fmt="%.0f")
    ax.yaxis.set_major_formatter(FMT_MIL)
    ax.set_ylabel("erro médio do A1 (unidades/dia)")
    ax.set_title("Ano de teste: erro do modelo com calendário por tipo de dia")
    ax = axes[1]
    vals = [a["pct_dias_com_encomenda"], a["pct_erro_em_dias_com_encomenda"], a["pct_volume_encomenda_no_ano"]]
    b = ax.bar(["parte dos dias", "parte do erro", "parte do volume\nvendido"], vals, color=COR_ENCOMENDA)
    ax.bar_label(b, fmt="%.0f%%")
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_title("Dias com encomenda: poucos dias, grande parte do erro")
    salvar(fig, "12_erro_restante_encomendas.png")

    with open(os.path.join(exp.METRICS_DIR, f"{exp.NOME}_diagnostico.json"), "w", encoding="utf-8") as fh:
        json.dump(num, fh, ensure_ascii=False, indent=2)
    print(json.dumps(num, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
