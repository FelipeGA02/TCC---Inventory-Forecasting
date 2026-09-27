"""L1 por loja com os achados do EDA: A0 × A1 (calendário) × variantes de nível.

Primeiro treino sobre as bases do pré-processamento v2 (Etapas 4–7). Aplica o que o EDA e os
treinos na série crua (docs 02 e 03) pediram para a modelagem:

  * uma série **por loja**, alvo = venda de **balcão** (encomendas fora, ADR-012);
  * **limiar de encomenda recalculado em cada rodada**, só com o passado (`data_corte`);
  * **teto no 99º percentil** dos dias abertos, só na série de treino (ADR-012 §2);
  * calendário corrigido: dia da semana + `loja_fechada` + `abertura_excepcional`
    (sem a janela de 7 dias que gerou 12% do erro no doc 03);
  * volta da escala log **sem correção de viés**: a previsão é a mediana, que é o que minimiza
    o erro absoluto medido aqui (e é o mesmo critério dos docs 02 e 03). O fator de Duan, usado
    no EDA, foi testado e descartado: com erros de cauda pesada ele explode (4,6× em Itabirito
    sem calendário, 1,28× com calendário) e infla todas as previsões;
  * configuração do modelo escolhida **só com dados anteriores à 1ª rodada**;
  * as mesmas avaliações do doc 03: ano inteiro (26 rodadas × 14 dias), dezembro e fevereiro,
    com erro relativo à regra simples, rodadas vencidas, largura e acerto da faixa de 95%;
  * **mudança de nível** (EDA §4 item 16): variantes que acompanham o nível recente.

Variantes:
  A0_eda          SARIMA sem exógenas (só os achados do EDA)
  A1_eda          SARIMAX + calendário corrigido
  A1_eda_d1       SARIMAX + calendário, com diferenciação (d = 1): a previsão parte do nível
                  recente em vez de voltar para a média do histórico
  HW_eda          Holt-Winters (nível + ciclo semanal) com o calendário aplicado depois:
                  previsão 0 nos dias de loja fechada

Uso (a partir de `ia-predictor/`, depois de `python -m training_scripts.preprocessing.run_all`):
    python -m training_scripts.baseline.sarimax_l1_por_loja
    python -m training_scripts.baseline.sarimax_l1_por_loja --so-graficos
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import time
import warnings
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

from training_scripts.preprocessing.constants import CALENDAR_CSV, ORDERS_CSV, SERIES_UNIDADE_CSV, UNIDADES
from training_scripts.preprocessing.encomendas import teto_quantil
from training_scripts.preprocessing.mark_orders import ler_base, marcar

warnings.filterwarnings("ignore")
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

_TS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_DIR = os.path.join(_TS, "results", "metrics")
PLOTS_DIR = os.path.join(_TS, "results", "plots", "l1_por_loja")
NOME = "l1_por_loja_eda"

M, H, N_FOLDS_ANO, ALPHA = 7, 14, 26, 0.05
INICIO_DEZ, INICIO_FEV = pd.Timestamp("2025-12-01"), pd.Timestamp("2026-02-01")
GRID_PQ, GRID_SPQ = range(0, 3), range(0, 2)
DIAS = ["seg", "ter", "qua", "qui", "sex", "sab"]
COLS_CAL = [f"dia_{d}" for d in DIAS] + ["loja_fechada", "abertura_excepcional"]

VARIANTES = {
    "A0_eda": {"exog": False, "d": None, "tipo": "sarimax"},
    "A1_eda": {"exog": True, "d": None, "tipo": "sarimax"},
    "A1_eda_d1": {"exog": True, "d": 1, "tipo": "sarimax"},
    "HW_eda": {"exog": False, "d": None, "tipo": "hw"},
}
ROTULO = {"A0_eda": "A0 · só EDA", "A1_eda": "A1 · EDA + calendário",
          "A1_eda_d1": "A1 · + acompanha nível (d=1)", "HW_eda": "Holt-Winters + calendário"}
COR = {"A0_eda": "#8e8e8e", "A1_eda": "#2e86c1", "A1_eda_d1": "#8e44ad", "HW_eda": "#e67e22",
       "naive": "#27ae60"}
# Referências da série crua (docs 02 e 03), mesmas datas do ano de teste: MAE no total das lojas.
REF_CRUA = {"A0-crua (doc 02)": 3024.1, "A1-crua (doc 03)": 2748.7}
FMT_MIL = mtick.FuncFormatter(lambda v, _: f"{v / 1000:.1f} mil".replace(".0 mil", " mil").replace(".", ",") if abs(v) >= 1000 else f"{v:.0f}")


# --------------------------------------------------------------------------- #
# Dados
# --------------------------------------------------------------------------- #
class Dados:
    """Linhas marcadas, calendário e séries. O balcão depende da origem (limiar só com o
    passado), então é calculado sob demanda e guardado por origem."""

    def __init__(self):
        self.linhas = ler_base(ORDERS_CSV)[["data", "unidade", "categoria", "qtdade"]]
        self.idx = pd.date_range(self.linhas["data"].min(), self.linhas["data"].max(), freq="D")
        cal = pd.read_csv(CALENDAR_CSV, sep=";", encoding="utf-8", parse_dates=["data"])
        for i, d in enumerate(DIAS):
            cal[f"dia_{d}"] = (cal["dia_semana"] == i).astype(float)
        self.cal = {u: g.set_index("data")[COLS_CAL].astype(float) for u, g in cal.groupby("unidade")}
        su = pd.read_csv(SERIES_UNIDADE_CSV, sep=";", decimal=",", encoding="utf-8", parse_dates=["data"])
        self.total = {u: g.set_index("data")["qtd_total"].reindex(self.idx, fill_value=0.0)
                      for u, g in su.groupby("unidade")}
        self._balcao = {}

    def balcao(self, origem: pd.Timestamp) -> dict[str, pd.Series]:
        if origem not in self._balcao:
            m, _ = marcar(self.linhas, data_corte=origem)
            b = m[m["encomenda"] == 0].groupby(["unidade", "data"])["qtdade"].sum()
            self._balcao[origem] = {u: b.loc[u].reindex(self.idx, fill_value=0.0) for u in UNIDADES}
        return self._balcao[origem]


# --------------------------------------------------------------------------- #
# Modelos
# --------------------------------------------------------------------------- #
def _ajustar(z, X, order, sorder):
    return SARIMAX(z, exog=X, order=order, seasonal_order=sorder, trend="c" if order[1] == 0 else "n",
                   enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=200)


def selecionar(y: pd.Series, X, d_fixo) -> dict:
    z = np.log1p(teto_quantil(y).clip(lower=0))
    d = d_fixo if d_fixo is not None else (0 if adfuller(z, autolag="AIC")[1] < 0.05 else 1)
    melhor = None
    for p, q, P, Q in itertools.product(GRID_PQ, GRID_PQ, GRID_SPQ, GRID_SPQ):
        try:
            r = _ajustar(z, X, (p, d, q), (P, 0, Q, M))
        except Exception:  # noqa: BLE001
            continue
        if r.mle_retvals.get("converged", True) and np.isfinite(r.aic) and (melhor is None or r.aic < melhor["aic"]):
            melhor = {"order": (p, d, q), "seasonal_order": (P, 0, Q, M), "aic": float(r.aic)}
    return melhor


def prever(var: dict, cfg: dict | None, y_tr: pd.Series, X_tr, X_fut, fechado_tr, fechado_fut):
    """Previsão na escala de unidades: (média, IC inferior, IC superior)."""
    z = np.log1p(teto_quantil(y_tr).clip(lower=0))
    passos = len(fechado_fut)
    if var["tipo"] == "hw":
        res = ExponentialSmoothing(z, trend=None, seasonal="add", seasonal_periods=M,
                                   initialization_method="estimated").fit()
        mu = np.asarray(res.forecast(passos))
        sd = float(np.std(res.resid.iloc[2 * M:]))
        lo_z, hi_z = mu - 1.96 * sd, mu + 1.96 * sd
    else:
        res = _ajustar(z, X_tr, cfg["order"], cfg["seasonal_order"])
        fc = res.get_forecast(passos, exog=X_fut)
        mu = fc.predicted_mean.values
        ic = fc.conf_int(alpha=ALPHA).values
        lo_z, hi_z = ic[:, 0], ic[:, 1]
    prev = np.expm1(mu)  # mediana na escala de unidades
    lo, hi = np.expm1(lo_z), np.expm1(hi_z)
    if var["tipo"] == "hw":
        # Holt-Winters não recebe exógenas; aplicar o calendário depois é justo (é conhecido
        # antes). O A0 fica sem calendário de propósito: é a referência "só EDA".
        prev, lo, hi = (np.where(fechado_fut, 0.0, a) for a in (prev, lo, hi))
    return np.clip(prev, 0, None), np.clip(lo, 0, None), np.clip(hi, 0, None)


# --------------------------------------------------------------------------- #
# Avaliação
# --------------------------------------------------------------------------- #
def janela(dados: Dados, u: str, nome: str, cfg, origem: pd.Timestamp, passos: int) -> pd.DataFrame:
    var = VARIANTES[nome]
    y = dados.balcao(origem)[u]
    cal = dados.cal[u].reindex(dados.idx.union(pd.date_range(origem, periods=passos)))
    fut = pd.date_range(origem, periods=passos, freq="D")
    tr = y[y.index < origem]
    X_tr = cal.loc[tr.index] if var["exog"] else None
    X_fut = cal.loc[fut] if var["exog"] else None
    fech_tr = cal.loc[tr.index, "loja_fechada"].values > 0
    fech_fut = cal.loc[fut, "loja_fechada"].values > 0
    prev, lo, hi = prever(var, cfg, tr, X_tr, X_fut, fech_tr, fech_fut)
    ult = tr.values[-M:]
    return pd.DataFrame({
        "data": fut, "unidade": u, "variante": nome, "real_balcao": y.reindex(fut).values,
        "real_total": dados.total[u].reindex(fut).values, "prev": prev, "lo": lo, "hi": hi,
        "naive": [ult[i % M] for i in range(passos)], "loja_fechada": fech_fut.astype(int),
        "abertura_excepcional": cal.loc[fut, "abertura_excepcional"].values.astype(int),
    })


def resumo(df: pd.DataFrame, alvo: str = "real_balcao") -> dict:
    e, en = (df[alvo] - df["prev"]).abs(), (df[alvo] - df["naive"]).abs()
    por = df.assign(e=e, en=en).groupby("rodada")[["e", "en"]].sum()
    return {
        "mae": float(e.mean()), "mae_naive": float(en.mean()),
        "erro_relativo_naive": float(e.sum() / en.sum()),
        "rodadas": int(len(por)), "rodadas_vence_naive": int((por["e"] < por["en"]).sum()),
        "cobertura_ic95": float(((df[alvo] >= df["lo"]) & (df[alvo] <= df["hi"])).mean() * 100),
        "largura_ic95": float((df["hi"] - df["lo"]).mean()),
        "previsto_sobre_real_pct": float(df["prev"].sum() / df[alvo].sum() * 100),
    }


def resumo_total(prev: pd.DataFrame) -> dict:
    """Soma das duas lojas, contra a venda total (encomendas incluídas), para comparar com
    os docs 02/03. A regra simples aqui repete a semana anterior do total."""
    g = prev.groupby(["rodada", "data"]).agg(prev=("prev", "sum"), real=("real_total", "sum")).reset_index()
    return {"mae_total_lojas_somadas": float((g["real"] - g["prev"]).abs().mean())}


def rodar() -> tuple[dict, pd.DataFrame]:
    t0 = time.time()
    dados = Dados()
    corte0 = dados.idx[len(dados.idx) - N_FOLDS_ANO * H]
    origens = [corte0 + pd.Timedelta(days=i * H) for i in range(N_FOLDS_ANO)]
    print(f"[dados] {dados.idx.min().date()} → {dados.idx.max().date()} · 1ª origem {corte0.date()}")

    res, prevs = {}, []
    for u in UNIDADES:
        res[u] = {}
        y_sel = dados.balcao(corte0)[u]
        y_sel = y_sel[y_sel.index < corte0]
        for nome, var in VARIANTES.items():
            t1 = time.time()
            cfg = None
            if var["tipo"] == "sarimax":
                X = dados.cal[u].loc[y_sel.index] if var["exog"] else None
                cfg = selecionar(y_sel, X, var["d"])
            linhas = []
            for i, o in enumerate(origens, start=1):
                linhas.append(janela(dados, u, nome, cfg, o, H).assign(avaliacao="ano_26", rodada=i))
            linhas.append(janela(dados, u, nome, cfg, INICIO_DEZ, 28).assign(avaliacao="dezembro", rodada=0))
            linhas.append(janela(dados, u, nome, cfg, INICIO_FEV, 28).assign(avaliacao="fevereiro", rodada=0))
            df = pd.concat(linhas)
            prevs.append(df)
            r = {"ordem": None if cfg is None else {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.items()}}
            for av in ("ano_26", "dezembro", "fevereiro"):
                d = df[df["avaliacao"] == av]
                r[av] = resumo(d)
                r[av]["contra_venda_total"] = resumo(d, "real_total")
            a = df[df["avaliacao"] == "ano_26"]
            ef = (a["real_balcao"] - a["prev"]).abs()
            fech = (a["loja_fechada"] == 1) & (a["data"].dt.dayofweek < 6)
            r["ano_26"]["mae_feriados"] = float(ef[fech].mean()) if fech.any() else None
            r["ano_26"]["mae_abertura_excepcional"] = float(ef[a["abertura_excepcional"] == 1].mean()) \
                if (a["abertura_excepcional"] == 1).any() else None
            r["tempo_s"] = round(time.time() - t1, 1)
            res[u][nome] = r
            print(f"  [{u} · {nome}] ano erro/regra {r['ano_26']['erro_relativo_naive']:.2f} · vence "
                  f"{r['ano_26']['rodadas_vence_naive']}/26 · dez {r['dezembro']['erro_relativo_naive']:.2f} · "
                  f"fev {r['fevereiro']['erro_relativo_naive']:.2f} · IC {r['ano_26']['cobertura_ic95']:.0f}% "
                  f"larg {r['ano_26']['largura_ic95']:.0f} · {r['tempo_s']}s")
    prev = pd.concat(prevs)
    res["lojas_somadas"] = {}
    for nome in VARIANTES:
        d = prev[(prev["variante"] == nome) & (prev["avaliacao"] == "ano_26")]
        res["lojas_somadas"][nome] = resumo_total(d)
        g = d.groupby(["rodada", "data"])[["real_balcao", "prev", "naive", "lo", "hi"]].sum().reset_index()
        res["lojas_somadas"][nome]["balcao"] = resumo(g)
    res["referencia_serie_crua_mae_total"] = REF_CRUA
    res["tempo_total_s"] = round(time.time() - t0, 1)
    return res, prev


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
def _salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, nome), dpi=130)
    plt.close(fig)


def graficos(res: dict, prev: pd.DataFrame) -> None:
    os.makedirs(PLOTS_DIR, exist_ok=True)
    nomes = list(VARIANTES)
    testes = [("ano_26", "Ano inteiro\n(26 rodadas)"), ("dezembro", "Dezembro"), ("fevereiro", "Fevereiro")]
    w = 0.2

    # 01 — erro relativo à regra simples, por loja
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8), sharey=True)
    for ax, u in zip(axes, UNIDADES):
        for j, n in enumerate(nomes):
            v = [res[u][n][t]["erro_relativo_naive"] * 100 for t, _ in testes]
            b = ax.bar(np.arange(3) + (j - 1.5) * w, v, w, color=COR[n], label=ROTULO[n])
            ax.bar_label(b, fmt="%.0f%%", fontsize=7)
        ax.axhline(100, color=COR["naive"], ls="--", lw=1.3)
        ax.set_xticks(np.arange(3), [t[1] for t in testes])
        ax.set_title(u)
        ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    axes[0].set_ylabel("erro do modelo ÷ erro da regra simples\n(venda de balcão)")
    axes[0].legend(fontsize=8, loc="upper left")
    fig.suptitle("Abaixo de 100% (linha verde) o modelo erra menos que repetir a semana passada")
    _salvar(fig, "01_erro_relativo_por_loja.png")

    # 02 — comparação com a série crua: MAE no total das lojas somadas (ano inteiro)
    fig, ax = plt.subplots(figsize=(11, 4.6))
    rot = list(REF_CRUA) + [ROTULO[n] for n in nomes]
    val = list(REF_CRUA.values()) + [res["lojas_somadas"][n]["mae_total_lojas_somadas"] for n in nomes]
    cores = ["#cccccc", "#9ec5e8"] + [COR[n] for n in nomes]
    b = ax.bar(rot, val, color=cores)
    ax.bar_label(b, fmt="%.0f")
    ax.set_ylabel("erro médio por dia no total vendido\n(as duas lojas, ano inteiro)")
    ax.set_title("Série crua (docs 02 e 03) × com os achados do EDA — mesmas datas, contra a venda total")
    ax.tick_params(axis="x", labelsize=8)
    _salvar(fig, "02_comparacao_com_serie_crua.png")

    # 03 — nível: média semanal do balcão real × previsões (ano inteiro), por loja
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    an = prev[prev["avaliacao"] == "ano_26"]
    for ax, u in zip(axes, UNIDADES):
        d = an[(an["unidade"] == u) & (an["loja_fechada"] == 0)]
        real = d[d["variante"] == nomes[0]].set_index("data")["real_balcao"].resample("W").mean()
        ax.plot(real.index, real.values, color="#333", lw=2, label="venda de balcão real")
        for n in nomes:
            s = d[d["variante"] == n].set_index("data")["prev"].resample("W").mean()
            ax.plot(s.index, s.values, color=COR[n], lw=1.4, label=ROTULO[n])
        ax.yaxis.set_major_formatter(FMT_MIL)
        ax.set_title(f"{u}: média por dia aberto, semana a semana")
    axes[0].legend(fontsize=8, ncol=3, loc="upper left")
    _salvar(fig, "03_acompanha_o_nivel.png")

    # 04 — fevereiro e dezembro, dia a dia, melhor variante × A0
    melhor = min(nomes, key=lambda n: res["lojas_somadas"][n]["balcao"]["erro_relativo_naive"])
    fig, axes = plt.subplots(2, 2, figsize=(14, 7))
    for i, u in enumerate(UNIDADES):
        for j, av in enumerate(("dezembro", "fevereiro")):
            ax = axes[i, j]
            d = prev[(prev["unidade"] == u) & (prev["avaliacao"] == av)]
            r = d[d["variante"] == nomes[0]]
            ax.bar(r["data"], r["real_total"], color="#f0c27b", label="venda total (com encomendas)")
            ax.bar(r["data"], r["real_balcao"], color="#bbbbbb", label="venda de balcão")
            for n in dict.fromkeys(["A0_eda", melhor]):
                s = d[d["variante"] == n]
                ax.plot(s["data"], s["prev"], color=COR[n], lw=1.8, marker="o", ms=2.5, label=ROTULO[n])
            ax.yaxis.set_major_formatter(FMT_MIL)
            ax.set_title(f"{u} · {av}", fontsize=10)
            ax.tick_params(axis="x", labelsize=7)
    axes[0, 0].legend(fontsize=7)
    _salvar(fig, "04_dezembro_e_fevereiro.png")

    # 05 — faixa de segurança: largura e acerto (ano)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.3))
    for ax, chave, tit in ((axes[0], "largura_ic95", "Largura média da faixa de 95% (unidades)"),
                           (axes[1], "cobertura_ic95", "Acerto da faixa de 95% (ideal: 90–98%)")):
        for j, n in enumerate(nomes):
            v = [res[u][n]["ano_26"][chave] for u in UNIDADES]
            b = ax.bar(np.arange(2) + (j - 1.5) * w, v, w, color=COR[n], label=ROTULO[n])
            ax.bar_label(b, fmt="%.0f", fontsize=7)
        ax.set_xticks(np.arange(2), UNIDADES)
        ax.set_title(tit)
    axes[1].axhspan(90, 98, color="#27ae60", alpha=0.12)
    axes[0].legend(fontsize=7)
    _salvar(fig, "05_faixa_de_seguranca.png")

    # 06 — rodada a rodada, por loja
    fig, axes = plt.subplots(2, 1, figsize=(13, 7.5), sharex=True)
    for ax, u in zip(axes, UNIDADES):
        for n in nomes:
            d = an[(an["unidade"] == u) & (an["variante"] == n)]
            g = d.assign(e=(d.real_balcao - d.prev).abs(), en=(d.real_balcao - d.naive).abs()) \
                 .groupby("rodada").agg(ini=("data", "min"), e=("e", "sum"), en=("en", "sum"))
            ax.plot(g["ini"], g["e"] / g["en"] * 100, marker="o", ms=3, color=COR[n], label=ROTULO[n])
        ax.axhline(100, color=COR["naive"], ls="--", lw=1.2)
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(mtick.PercentFormatter())
        ax.set_title(f"{u}: erro ÷ erro da regra simples em cada rodada (abaixo da linha verde = ganhou)")
    axes[0].legend(fontsize=8, ncol=2)
    _salvar(fig, "06_rodada_a_rodada.png")


def main() -> None:
    os.makedirs(METRICS_DIR, exist_ok=True)
    jpath = os.path.join(METRICS_DIR, f"{NOME}.json")
    ppath = os.path.join(METRICS_DIR, f"{NOME}_previsoes.csv")
    if "--so-graficos" in sys.argv:
        with open(jpath, encoding="utf-8") as fh:
            res = json.load(fh)["resultados"]
        prev = pd.read_csv(ppath, sep=";", decimal=",", parse_dates=["data"])
    else:
        res, prev = rodar()
        with open(jpath, "w", encoding="utf-8") as fh:
            json.dump({"experimento": NOME, "gerado_em": datetime.now().isoformat(timespec="seconds"),
                       "variantes": VARIANTES, "exogenas_calendario": COLS_CAL, "resultados": res},
                      fh, ensure_ascii=False, indent=2, default=str)
        prev.to_csv(ppath, sep=";", decimal=",", index=False)
        print(f"[saida] {jpath}")
    graficos(res, prev)


if __name__ == "__main__":
    main()
