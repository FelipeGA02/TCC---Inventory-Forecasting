"""Linha de base A0-crua: SARIMA puro sobre 1 série diária bruta, dados de ANTES do EDA.

Objetivo: medir o ponto de partida, para quantificar depois o ganho de cada etapa
(achados do EDA → exógenas de calendário → bases de enriquecimento).

O que entra (e nada além disso):
- Base: `data/processed/contas_a_receber_taxonomia.csv` — saída da Etapa 3 do
  pré-processamento de 2026-08-30 (commit 8e5aa6e), anterior ao EDA: colunas já
  removidas + taxonomia (3 lojas, Garden Center ainda separado).
- Série: soma diária de `qtdade` de TODAS as lojas e categorias — uma série só.
  Única regra aplicada é a que já existia antes do EDA: `Servico e taxa` fora da
  demanda (01-pre_processing.md). Devoluções (qtd < 0), encomendas grandes e picos
  ficam como estão; dias sem venda entram como 0.
- Modelo: SARIMA(p,d,q)(P,0,Q)_7 sem exógenas. d via ADF; log1p se CV > 0,7;
  grid p,q ∈ 0..2, P,Q ∈ 0..1, escolha por AIC (configuração padrão do CLAUDE.md).
- Avaliação: hold-out de 28 dias + walk-forward com 4 folds (origem móvel, h=14),
  MASE/RMSSE contra a naïve sazonal semanal, cobertura do IC 95%, Ljung-Box e
  Shapiro-Wilk nos resíduos.

Uso (a partir de `ia-predictor/`):
    python -m training_scripts.baseline.sarimax_serie_crua
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
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

warnings.filterwarnings("ignore")

# --------------------------------------------------------------------------- #
# Caminhos e parâmetros
# --------------------------------------------------------------------------- #
_BASELINE_DIR = os.path.dirname(os.path.abspath(__file__))
_TRAINING_SCRIPTS_DIR = os.path.dirname(_BASELINE_DIR)
_IA_PREDICTOR_ROOT = os.path.dirname(_TRAINING_SCRIPTS_DIR)

PRE_EDA_CSV = os.path.join(
    _IA_PREDICTOR_ROOT, "data", "processed", "contas_a_receber_taxonomia.csv"
)
METRICS_DIR = os.path.join(_TRAINING_SCRIPTS_DIR, "results", "metrics")
PLOTS_DIR = os.path.join(_TRAINING_SCRIPTS_DIR, "results", "plots", "baseline")

NOME = "A0_sarima_serie_crua_pre_eda"
M = 7
TEST_DAYS = 28
HORIZON = 14
N_FOLDS = 4
LOG_CV_THRESHOLD = 0.7
GRID_PQ = range(0, 3)
GRID_SPQ = range(0, 2)
ALPHA = 0.05


# --------------------------------------------------------------------------- #
# Série
# --------------------------------------------------------------------------- #
def carregar_serie() -> tuple[pd.Series, dict]:
    df = pd.read_csv(
        PRE_EDA_CSV,
        sep=";",
        decimal=",",
        encoding="latin-1",  # encoding misto (mojibake) — só `categoria` ASCII é usada
        dtype={"produto_cod": str},
        usecols=["emissao", "qtdade", "unidade", "categoria"],
    )
    n_total = len(df)
    servico = df["categoria"].str.strip().str.lower() == "servico e taxa"
    df = df[~servico]
    df["data"] = pd.to_datetime(df["emissao"], dayfirst=True).dt.normalize()

    diaria = df.groupby("data")["qtdade"].sum()
    calendario = pd.date_range(diaria.index.min(), diaria.index.max(), freq="D")
    serie = diaria.reindex(calendario, fill_value=0.0).astype(float)
    serie.index.name = "data"
    serie.name = "qtd_total"

    info = {
        "arquivo": os.path.relpath(PRE_EDA_CSV, _IA_PREDICTOR_ROOT).replace("\\", "/"),
        "linhas_base": int(n_total),
        "linhas_servico_excluidas": int(servico.sum()),
        "linhas_qtd_negativa": int((df["qtdade"] < 0).sum()),
        "unidades": sorted(df["unidade"].unique().tolist()),
        "categorias": sorted(df["categoria"].unique().tolist()),
        "inicio": str(serie.index.min().date()),
        "fim": str(serie.index.max().date()),
        "dias_calendario": int(len(serie)),
        "dias_com_venda": int((serie > 0).sum()),
        "dias_zero": int((serie == 0).sum()),
        "dias_negativos": int((serie < 0).sum()),
        "media": float(serie.mean()),
        "mediana": float(serie.median()),
        "desvio": float(serie.std()),
        "max": float(serie.max()),
        "cv": float(serie.std() / serie.mean()),
    }
    return serie, info


# --------------------------------------------------------------------------- #
# Transformação e seleção de ordem
# --------------------------------------------------------------------------- #
def usar_log(y: pd.Series) -> bool:
    return (y.std() / y.mean()) > LOG_CV_THRESHOLD and (y >= 0).all()


def escolher_d(z: pd.Series) -> tuple[int, float]:
    p = adfuller(z, autolag="AIC")[1]
    return (0 if p < 0.05 else 1), float(p)


def ajustar(z: pd.Series, order, seasonal_order):
    modelo = SARIMAX(
        z,
        order=order,
        seasonal_order=seasonal_order,
        trend="c" if order[1] == 0 else "n",
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    return modelo.fit(disp=False, maxiter=200)


def selecionar_ordem(z: pd.Series, d: int) -> tuple[dict, list[dict]]:
    tentativas = []
    melhor = None
    for p, q, P, Q in itertools.product(GRID_PQ, GRID_PQ, GRID_SPQ, GRID_SPQ):
        order, sorder = (p, d, q), (P, 0, Q, M)
        try:
            res = ajustar(z, order, sorder)
            aic = float(res.aic)
            ok = bool(res.mle_retvals.get("converged", True)) and np.isfinite(aic)
        except Exception:  # noqa: BLE001 — ordem que não ajusta sai do grid
            aic, ok = float("inf"), False
        tentativas.append({"order": order, "seasonal_order": sorder, "aic": aic, "convergiu": ok})
        if ok and (melhor is None or aic < melhor["aic"]):
            melhor = {"order": order, "seasonal_order": sorder, "aic": aic}
    return melhor, tentativas


# --------------------------------------------------------------------------- #
# Métricas
# --------------------------------------------------------------------------- #
def escala_naive(treino: pd.Series) -> tuple[float, float]:
    diff = treino.values[M:] - treino.values[:-M]
    return float(np.mean(np.abs(diff))), float(np.sqrt(np.mean(diff**2)))


def metricas(real, prev, lo, hi, treino: pd.Series) -> dict:
    real, prev = np.asarray(real, float), np.asarray(prev, float)
    erro = real - prev
    mae_n, rmse_n = escala_naive(treino)
    nz = real != 0
    denom = np.abs(real) + np.abs(prev)
    return {
        "mae": float(np.mean(np.abs(erro))),
        "rmse": float(np.sqrt(np.mean(erro**2))),
        "mase": float(np.mean(np.abs(erro)) / mae_n),
        "rmsse": float(np.sqrt(np.mean(erro**2)) / rmse_n),
        "mape_dias_com_venda": float(np.mean(np.abs(erro[nz] / real[nz])) * 100) if nz.any() else None,
        "smape": float(np.mean(np.where(denom > 0, 2 * np.abs(erro) / np.where(denom > 0, denom, 1), 0)) * 100),
        "cobertura_ic95": float(np.mean((real >= lo) & (real <= hi)) * 100),
        "amplitude_media_ic95": float(np.mean(np.asarray(hi) - np.asarray(lo))),
    }


def prever(treino: pd.Series, passos: int, order, sorder, log: bool):
    z = np.log1p(treino) if log else treino
    res = ajustar(z, order, sorder)
    fc = res.get_forecast(passos)
    media = fc.predicted_mean.values
    ic = fc.conf_int(alpha=ALPHA).values
    if log:
        media, ic = np.expm1(media), np.expm1(ic)
    return res, np.clip(media, 0, None), np.clip(ic[:, 0], 0, None), np.clip(ic[:, 1], 0, None)


def naive_sazonal(treino: pd.Series, passos: int) -> np.ndarray:
    ultima = treino.values[-M:]
    return np.array([ultima[i % M] for i in range(passos)])


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
def plot_serie(serie: pd.Series, corte: pd.Timestamp, path: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 4))
    ax.plot(serie.index, serie.values, lw=0.7, color="#3a6ea5")
    ax.plot(serie.rolling(28).mean(), lw=1.6, color="#c0392b", label="média móvel 28d")
    ax.axvline(corte, color="k", ls="--", lw=1, label="início do hold-out")
    ax.set_title("Série crua (pré-EDA): quantidade diária total — todas as lojas e categorias")
    ax.set_ylabel("qtd vendida / dia")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_holdout(serie, teste, prev, lo, hi, naive, path) -> None:
    contexto = serie[teste.index[0] - pd.Timedelta(days=56) :]
    fig, ax = plt.subplots(figsize=(13, 4.5))
    ax.plot(contexto.index, contexto.values, color="#555", lw=1, label="real")
    ax.plot(teste.index, prev, color="#c0392b", lw=1.8, label="SARIMA (A0-crua)")
    ax.fill_between(teste.index, lo, hi, color="#c0392b", alpha=0.15, label="IC 95%")
    ax.plot(teste.index, naive, color="#27ae60", lw=1.2, ls=":", label="naïve sazonal (7d)")
    ax.set_title("Hold-out de 28 dias — previsão × real")
    ax.set_ylabel("qtd vendida / dia")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_walk_forward(serie, folds_plot, path) -> None:
    fig, axes = plt.subplots(len(folds_plot), 1, figsize=(13, 2.6 * len(folds_plot)), sharey=False)
    for ax, f in zip(np.atleast_1d(axes), folds_plot):
        idx = f["idx"]
        ctx = serie[idx[0] - pd.Timedelta(days=28) : idx[-1]]
        ax.plot(ctx.index, ctx.values, color="#555", lw=1)
        ax.plot(idx, f["prev"], color="#c0392b", lw=1.6)
        ax.fill_between(idx, f["lo"], f["hi"], color="#c0392b", alpha=0.15)
        ax.set_title(f"Fold origem {idx[0].date()} · MASE {f['mase']:.3f} · cobertura IC95 {f['cob']:.0f}%", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_residuos(resid: pd.Series, path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
    axes[0].plot(resid.index, resid.values, lw=0.6)
    axes[0].set_title("Resíduos (escala do modelo)")
    axes[1].hist(resid.values, bins=50, color="#3a6ea5")
    axes[1].set_title("Histograma")
    plot_acf(resid, lags=28, ax=axes[2])
    axes[2].set_title("ACF dos resíduos")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    os.makedirs(METRICS_DIR, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)
    t0 = time.time()

    serie, info = carregar_serie()
    print(f"[serie] {info['inicio']} → {info['fim']} · {info['dias_calendario']} dias "
          f"({info['dias_zero']} zerados) · média {info['media']:.1f} · CV {info['cv']:.2f}")

    treino, teste = serie.iloc[:-TEST_DAYS], serie.iloc[-TEST_DAYS:]
    log = usar_log(treino)
    z = np.log1p(treino) if log else treino
    d, adf_p = escolher_d(z)
    print(f"[config] log1p={log} · ADF p={adf_p:.4f} → d={d}")

    t_sel = time.time()
    melhor, grid = selecionar_ordem(z, d)
    t_sel = time.time() - t_sel
    order, sorder = melhor["order"], melhor["seasonal_order"]
    print(f"[ordem] SARIMA{order}x{sorder} · AIC {melhor['aic']:.1f} · {t_sel:.0f}s")

    # Hold-out
    res, prev, lo, hi = prever(treino, TEST_DAYS, order, sorder, log)
    naive = naive_sazonal(treino, TEST_DAYS)
    m_hold = metricas(teste.values, prev, lo, hi, treino)
    m_naive = metricas(teste.values, naive, naive, naive, treino)
    # MASE usa a escala do treino (inflada pelos picos de encomenda); o MAE relativo
    # compara com a naïve na MESMA janela e é a medida comparável entre experimentos.
    m_hold["mae_relativo_naive"] = m_hold["mae"] / m_naive["mae"]
    resid = res.resid.iloc[max(d, 1) + M :]
    lb = acorr_ljungbox(resid, lags=[7, 14], return_df=True)["lb_pvalue"]
    shapiro_p = float(stats.shapiro(resid.values[:5000])[1])
    print(f"[hold-out] MASE {m_hold['mase']:.3f} (naïve {m_naive['mase']:.3f}) · "
          f"RMSSE {m_hold['rmsse']:.3f} · IC95 {m_hold['cobertura_ic95']:.1f}%")

    # Walk-forward: últimas N_FOLDS janelas de 14 dias, sem sobreposição
    folds, folds_plot = [], []
    n = len(serie)
    for k in range(N_FOLDS, 0, -1):
        corte = n - k * HORIZON
        tr, te = serie.iloc[:corte], serie.iloc[corte : corte + HORIZON]
        _, p, l, h = prever(tr, HORIZON, order, sorder, log)
        mf = metricas(te.values, p, l, h, tr)
        mn = metricas(te.values, naive_sazonal(tr, HORIZON), 0, 0, tr)
        folds.append({"origem": str(te.index[0].date()),
                      **{k2: mf[k2] for k2 in ("mae", "rmse", "mase", "rmsse", "smape", "cobertura_ic95", "amplitude_media_ic95")},
                      "mae_naive": mn["mae"], "mase_naive": mn["mase"], "mae_relativo_naive": mf["mae"] / mn["mae"]})
        folds_plot.append({"idx": te.index, "prev": p, "lo": l, "hi": h, "mase": mf["mase"], "cob": mf["cobertura_ic95"]})
        print(f"[wf] origem {te.index[0].date()} · MASE {mf['mase']:.3f} (naïve {mn['mase']:.3f}) · IC95 {mf['cobertura_ic95']:.0f}%")

    wf = {
        "n_folds": N_FOLDS,
        "horizonte_dias": HORIZON,
        "mase_medio": float(np.mean([f["mase"] for f in folds])),
        "rmsse_medio": float(np.mean([f["rmsse"] for f in folds])),
        "mae_medio": float(np.mean([f["mae"] for f in folds])),
        "cobertura_ic95_media": float(np.mean([f["cobertura_ic95"] for f in folds])),
        "mase_naive_medio": float(np.mean([f["mase_naive"] for f in folds])),
        "mae_relativo_naive_medio": float(np.mean([f["mae_relativo_naive"] for f in folds])),
        "folds_vence_naive": int(sum(f["mae_relativo_naive"] < 1 for f in folds)),
        "amplitude_media_ic95": float(np.mean([f["amplitude_media_ic95"] for f in folds])),
        "folds": folds,
    }

    passa_mase = wf["mase_medio"] < 1.0
    passa_cob = 90 <= wf["cobertura_ic95_media"] <= 98
    status = "trained" if (passa_mase and passa_cob) else "low_confidence"

    resultado = {
        "modelo": NOME,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "descricao": "SARIMA puro, sem exógenas, sobre 1 série diária total crua (base pré-EDA)",
        "serie": info,
        "config": {
            "m": M, "test_days": TEST_DAYS, "horizonte_wf": HORIZON, "n_folds": N_FOLDS,
            "log1p": bool(log), "adf_pvalue": adf_p, "d": d,
            "grid": "p,q∈0..2 · P,Q∈0..1 · D=0 · AIC", "exogenas": None,
        },
        "ordem": {"order": list(order), "seasonal_order": list(sorder), "aic": melhor["aic"],
                  "tempo_selecao_s": round(t_sel, 1),
                  "top5_aic": sorted(
                      [{"order": list(g["order"]), "seasonal_order": list(g["seasonal_order"]), "aic": g["aic"]}
                       for g in grid if g["convergiu"]], key=lambda g: g["aic"])[:5]},
        "holdout": {**m_hold,
                    "ljung_box_lag7_pvalue": float(lb.loc[7]),
                    "ljung_box_lag14_pvalue": float(lb.loc[14]),
                    "shapiro_pvalue": shapiro_p},
        "holdout_naive_sazonal": {k: v for k, v in m_naive.items() if k != "cobertura_ic95"},
        "walk_forward": wf,
        "status": status,
        "criterios": {"mase_wf_menor_1": passa_mase, "cobertura_wf_90_98": passa_cob},
        "tempo_total_s": round(time.time() - t0, 1),
    }

    path_json = os.path.join(METRICS_DIR, f"baseline_{NOME}.json")
    with open(path_json, "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, ensure_ascii=False, indent=2)

    pd.DataFrame({
        "data": teste.index.date, "real": teste.values, "previsto": prev,
        "ic95_inf": lo, "ic95_sup": hi, "naive_sazonal": naive,
    }).to_csv(os.path.join(METRICS_DIR, f"baseline_{NOME}_holdout.csv"), sep=";", decimal=",", index=False)

    plot_serie(serie, teste.index[0], os.path.join(PLOTS_DIR, "01_serie_crua.png"))
    plot_holdout(serie, teste, prev, lo, hi, naive, os.path.join(PLOTS_DIR, "02_holdout_previsao.png"))
    plot_walk_forward(serie, folds_plot, os.path.join(PLOTS_DIR, "03_walk_forward.png"))
    plot_residuos(resid, os.path.join(PLOTS_DIR, "04_residuos.png"))

    print(f"[status] {status} · WF MASE {wf['mase_medio']:.3f} · WF IC95 {wf['cobertura_ic95_media']:.1f}%")
    print(f"[saida] {path_json}")


if __name__ == "__main__":
    main()
