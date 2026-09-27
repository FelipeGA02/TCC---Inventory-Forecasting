"""Diagnóstico do L1 por loja (doc 04): MASE formal, viés, peso das encomendas e um teste de
calibração do viés.

Lê as previsões salvas por `sarimax_l1_por_loja.py` (não treina de novo) e gera os gráficos
07–10 e `l1_por_loja_eda_diagnostico.json`:

  * **MASE formal** (critério do CLAUDE.md, MASE < 1): erro da rodada ÷ erro médio da regra
    simples semanal **no treino** daquela rodada (balcão com o limiar da origem);
  * **viés**: previsto ÷ vendido, mês a mês. A previsão é a mediana (ótima para o erro
    absoluto), que fica abaixo da média numa série assimétrica;
  * **encomendas**: quanto do erro contra a venda total vem só delas;
  * **calibração do viés** (teste de solução, sem retreinar): a previsão de cada rodada é
    multiplicada por Σ vendido ÷ Σ previsto das 4 rodadas anteriores (só o passado).

Uso (a partir de `ia-predictor/`), depois do treino:
    python -m training_scripts.baseline.analise_l1_por_loja
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

from training_scripts.baseline import sarimax_l1_por_loja as L
from training_scripts.preprocessing.constants import UNIDADES

MELHOR = "A1_eda_d1"
N_CALIB = 4  # rodadas anteriores usadas na calibração


def _salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(os.path.join(L.PLOTS_DIR, nome), dpi=130)
    plt.close(fig)


def mase_formal(prev: pd.DataFrame, dados: L.Dados) -> dict:
    """MASE por rodada com a escala da regra simples semanal no treino da própria rodada."""
    an = prev[prev["avaliacao"] == "ano_26"]
    out = {}
    for u in UNIDADES:
        out[u] = {}
        for n in L.VARIANTES:
            d = an[(an["unidade"] == u) & (an["variante"] == n)]
            vals = []
            for _, g in d.groupby("rodada"):
                o = g["data"].min()
                tr = dados.balcao(o)[u]
                tr = tr[tr.index < o].values
                escala = np.mean(np.abs(tr[L.M:] - tr[:-L.M]))
                vals.append(float((g["real_balcao"] - g["prev"]).abs().mean() / escala))
            out[u][n] = {"mase_medio": float(np.mean(vals)), "rodadas_mase_menor_1": int(np.sum(np.array(vals) < 1)),
                         "mase_por_rodada": [round(v, 3) for v in vals]}
    return out


def calibrar(d: pd.DataFrame) -> pd.DataFrame:
    """Multiplica cada rodada por Σreal/Σprev das N_CALIB rodadas anteriores (dias abertos)."""
    d = d.sort_values(["rodada", "data"]).copy()
    somas = d[d["loja_fechada"] == 0].groupby("rodada")[["real_balcao", "prev"]].sum()
    fator = {}
    for r in somas.index:
        ant = somas.loc[(somas.index < r) & (somas.index >= r - N_CALIB)]
        fator[r] = float(ant["real_balcao"].sum() / ant["prev"].sum()) if len(ant) else 1.0
    d["fator"] = d["rodada"].map(fator)
    d["prev_calibrada"] = d["prev"] * d["fator"]
    return d


def main() -> None:
    prev = pd.read_csv(os.path.join(L.METRICS_DIR, f"{L.NOME}_previsoes.csv"), sep=";", decimal=",",
                       parse_dates=["data"])
    dados = L.Dados()
    an = prev[prev["avaliacao"] == "ano_26"]
    num = {"mase_formal": mase_formal(prev, dados)}
    for u in UNIDADES:
        m = num["mase_formal"][u][MELHOR]
        print(f"[MASE] {u} · {MELHOR}: {m['mase_medio']:.3f} (rodadas < 1: {m['rodadas_mase_menor_1']}/26)")

    # ------------------------------------------------------------------ #
    # 07 — viés mês a mês (melhor variante)
    # ------------------------------------------------------------------ #
    b = an[an["variante"] == MELHOR].copy()
    b["mes"] = b["data"].dt.to_period("M")
    mensal = b.groupby(["unidade", "mes"])[["prev", "real_balcao"]].sum()
    mensal["pct"] = mensal["prev"] / mensal["real_balcao"] * 100
    num["vies_mensal_pct"] = {u: {str(k): round(v, 1) for k, v in mensal.loc[u, "pct"].items()} for u in UNIDADES}
    num["vies_ano_pct"] = {u: round(float(b[b.unidade == u].prev.sum() / b[b.unidade == u].real_balcao.sum() * 100), 1)
                           for u in UNIDADES}
    fig, ax = plt.subplots(figsize=(12, 4.5))
    meses = sorted(b["mes"].unique())
    x = np.arange(len(meses))
    for j, u in enumerate(UNIDADES):
        v = [mensal.loc[(u, mm), "pct"] if (u, mm) in mensal.index else np.nan for mm in meses]
        ax.bar(x + (j - 0.5) * 0.4, v, 0.4, label=u, color=["#1565C0", "#6A1B9A"][j])
    ax.axhline(100, color="#27ae60", ls="--", lw=1.3, label="previsão = vendido")
    ax.set_xticks(x, [str(mm) for mm in meses], rotation=45, fontsize=8)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_ylabel("previsto ÷ vendido no balcão")
    ax.set_title("A previsão fica abaixo do vendido na maior parte do ano (A1 com d=1)")
    ax.legend(fontsize=8)
    _salvar(fig, "07_vies_mes_a_mes.png")

    # ------------------------------------------------------------------ #
    # 08 — quanto do erro contra a venda total vem das encomendas
    # ------------------------------------------------------------------ #
    enc = {}
    for u in UNIDADES:
        d = b[b["unidade"] == u]
        e_bal = (d["real_balcao"] - d["prev"]).abs().mean()
        e_tot = (d["real_total"] - d["prev"]).abs().mean()
        enc[u] = {"mae_contra_balcao": float(e_bal), "mae_contra_total": float(e_tot),
                  "erro_extra_encomendas": float(e_tot - e_bal),
                  "pct_erro_total_por_encomendas": float((e_tot - e_bal) / e_tot * 100),
                  "pct_volume_encomenda_ano_teste": float((d["real_total"] - d["real_balcao"]).sum()
                                                          / d["real_total"].sum() * 100)}
    num["encomendas_no_erro"] = enc
    fig, ax = plt.subplots(figsize=(10, 4.5))
    xs = np.arange(len(UNIDADES))
    bal = [enc[u]["mae_contra_balcao"] for u in UNIDADES]
    ext = [enc[u]["erro_extra_encomendas"] for u in UNIDADES]
    ax.bar(xs, bal, 0.5, color="#8e44ad", label="erro no balcão (o que o modelo prevê)")
    ax.bar(xs, ext, 0.5, bottom=bal, color="#e67e22", label="erro extra: encomendas (não previstas)")
    for i, u in enumerate(UNIDADES):
        ax.text(i, bal[i] + ext[i] + 25, f"encomendas = {enc[u]['pct_volume_encomenda_ano_teste']:.0f}% do vendido\n"
                f"e {enc[u]['pct_erro_total_por_encomendas']:.0f}% do erro", ha="center", fontsize=9)
    ax.set_xticks(xs, UNIDADES)
    ax.set_ylabel("erro médio por dia contra a venda total")
    ax.set_ylim(0, max(b_ + e_ for b_, e_ in zip(bal, ext)) * 1.3)
    ax.set_title("No ano de teste, as encomendas respondem pela maior parte do erro de Itabirito")
    ax.legend(fontsize=8, loc="upper left")
    _salvar(fig, "08_erro_das_encomendas.png")

    # ------------------------------------------------------------------ #
    # 09 — teste de solução para o viés: calibração com as rodadas anteriores
    # ------------------------------------------------------------------ #
    cal = {}
    linhas = []
    for u in UNIDADES:
        d = calibrar(b[b["unidade"] == u])
        d = d[d["rodada"] > N_CALIB]  # só rodadas com 4 anteriores para calibrar
        mae0 = float((d["real_balcao"] - d["prev"]).abs().mean())
        mae1 = float((d["real_balcao"] - d["prev_calibrada"]).abs().mean())
        cal[u] = {"rodadas_avaliadas": int(d["rodada"].nunique()),
                  "sem_calibrar": {"mae": mae0, "previsto_sobre_real_pct": float(d.prev.sum() / d.real_balcao.sum() * 100)},
                  "calibrada": {"mae": mae1,
                                "previsto_sobre_real_pct": float(d.prev_calibrada.sum() / d.real_balcao.sum() * 100)},
                  "fator_medio": float(d.groupby("rodada")["fator"].first().mean())}
        linhas.append((u, cal[u]))
    num["calibracao_vies"] = cal
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3))
    for ax, chave, tit, fmt in ((axes[0], "previsto_sobre_real_pct", "Previsto ÷ vendido (ideal: 100%)", "%.0f%%"),
                                (axes[1], "mae", "Erro médio por dia (unidades)", "%.0f")):
        for j, (rot, cor) in enumerate((("sem_calibrar", "#8e44ad"), ("calibrada", "#16a085"))):
            v = [c[rot][chave] for _, c in linhas]
            bb = ax.bar(np.arange(2) + (j - 0.5) * 0.38, v, 0.38, color=cor,
                        label="sem calibrar" if j == 0 else "calibrada (4 rodadas anteriores)")
            ax.bar_label(bb, fmt=fmt, fontsize=8)
        ax.set_xticks(np.arange(2), [u for u, _ in linhas])
        ax.set_title(tit)
    axes[0].axhline(100, color="#27ae60", ls="--", lw=1.2)
    axes[0].legend(fontsize=8)
    fig.suptitle("Teste de solução para o viés: corrigir pela razão vendido/previsto das rodadas anteriores")
    _salvar(fig, "09_teste_calibracao_vies.png")

    # ------------------------------------------------------------------ #
    # 10 — MASE formal por rodada (melhor variante)
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(12, 4.3))
    ini = b.groupby("rodada")["data"].min()
    for u, cor in zip(UNIDADES, ["#1565C0", "#6A1B9A"]):
        v = num["mase_formal"][u][MELHOR]["mase_por_rodada"]
        ax.plot(ini.values, v, marker="o", ms=4, color=cor,
                label=f"{u} (média {num['mase_formal'][u][MELHOR]['mase_medio']:.2f})")
    ax.axhline(1, color="#c0392b", ls="--", lw=1.2, label="limite do projeto (MASE < 1)")
    ax.set_ylabel("MASE da rodada")
    ax.set_title("Critério do projeto: MASE < 1 em cada rodada de 14 dias (A1 com d=1)")
    ax.legend(fontsize=8)
    _salvar(fig, "10_mase_por_rodada.png")

    with open(os.path.join(L.METRICS_DIR, f"{L.NOME}_diagnostico.json"), "w", encoding="utf-8") as fh:
        json.dump(num, fh, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in num.items() if k != "mase_formal"}, ensure_ascii=False, indent=1))
    print({u: {n: round(x["mase_medio"], 3) for n, x in v.items()} for u, v in num["mase_formal"].items()})


if __name__ == "__main__":
    main()
