"""Estacionariedade testada na mesma série e na mesma janela que o SARIMAX usa — refaz o doc 10.

`estacionariedade_janela_aic.py` (a 1ª versão do doc 10) não era fiel ao modelo em dois pontos:

1. **Série:** ela testava o resíduo de uma regressão só nos dias de loja aberta, emendados, sem a
   exógena `loja_fechada`. O SARIMAX de produção é uma regressão com erros ARIMA sobre **todos os
   dias do calendário** — yₜ = c + xₜ'β + uₜ, com xₜ = 6 dummies de dia da semana, `loja_fechada` e
   `abertura_excepcional` — e o `d` se aplica a uₜ. Tirar os dias fechados deixava a semana com 6
   dias (o lag 7 deixava de ser o mesmo dia da semana anterior) e cada feriado deslocava o resto.
   Aqui o teste é feito no resíduo de MQO de y nas **mesmas exógenas do modelo, em todos os dias**:
   é o procedimento de Hyndman & Khandakar (2008) para regressão com erros ARIMA (`auto.arima`
   com `xreg` testa os resíduos da regressão).
2. **Janela:** ela testava a janela do AIC (365 dias antes da 1ª origem do walk-forward, 68 dias
   antes do corte), mas a previsão de cada corte é ajustada nos 365 dias **até o corte**. Aqui as
   duas janelas são testadas: `aic` (onde o treino escolhe a ordem — e escolheria o d sem olhar o
   período avaliado) e `ajuste` (onde a previsão do corte é estimada).

Testes a 5%: KPSS de nível (lags automáticos, Hobijn et al.; e, como sensibilidade, a regra
"curta" do `auto.arima`, l = ⌊4(n/100)^¼⌋), ADF com constante (lags por AIC) e DF-GLS (`arch`).

Uso (a partir de `ia-predictor/`, com o banco de DATABASE_URL):
    python -m training_scripts.validation.estacionariedade_fiel_ao_modelo --workers 12
"""
from __future__ import annotations

import argparse
import os
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from backend.domain.models.trainer import ConfigTreino, motivo_inelegivel, origens_walk_forward

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(_RAIZ, "results", "metrics", "estacionariedade_fiel_ao_modelo")
CORTES = list(pd.date_range("2025-03-01", "2026-02-21", freq="7D"))


def residuo_do_modelo(y: pd.Series, X: pd.DataFrame) -> np.ndarray:
    """uₜ = yₜ − ĉ − xₜ'β̂ (MQO), em todos os dias da janela, com as exógenas do SARIMAX."""
    Xw = X.loc[y.index].astype(float)
    cols = [c for c in Xw.columns if Xw[c].std() > 0]
    A = np.column_stack([np.ones(len(y)), Xw[cols].values])
    b, *_ = np.linalg.lstsq(A, y.values.astype(float), rcond=None)
    return y.values.astype(float) - A @ b


def testes(u: np.ndarray) -> dict:
    """KPSS (H0: estacionária) e a família Dickey-Fuller (H0: raiz unitária). O ADF depende do
    número de lags da regressão aumentada, então vai com 4 regras: AIC, BIC, t-stat (Ng & Perron,
    1995: do máximo para baixo até o último lag significativo) e o lag fixo de Schwert (1989),
    l = ⌊12(n/100)^¼⌋; o máximo das 3 primeiras também é o de Schwert."""
    from arch.unitroot import DFGLS, PhillipsPerron
    from statsmodels.tsa.stattools import adfuller, kpss
    warnings.simplefilter("ignore")
    n = len(u)
    l12 = int(12 * (n / 100) ** 0.25)
    out = {"n": n, "acf1_dif": float(pd.Series(np.diff(u)).autocorr(1)),
           "kpss_p": float(kpss(u, regression="c", nlags="auto")[1]),
           "kpss_curto_p": float(kpss(u, regression="c", nlags=int(4 * (n / 100) ** 0.25))[1])}
    for nome, autolag in (("adf_p", "AIC"), ("adf_bic_p", "BIC"), ("adf_tstat_p", "t-stat")):
        r = adfuller(u, maxlag=l12, regression="c", autolag=autolag)
        out[nome], out[nome.replace("_p", "_lags")] = float(r[1]), int(r[2])
    out["adf_schwert_p"] = float(adfuller(u, maxlag=l12, regression="c", autolag=None)[1])
    for nome, f in (("dfgls_p", lambda: DFGLS(u, trend="c", method="aic").pvalue),
                    ("pp_p", lambda: PhillipsPerron(u, trend="c").pvalue)):
        try:
            out[nome] = float(f())
        except Exception:  # noqa: BLE001
            out[nome] = np.nan
    return out


def tarefa(args) -> list[dict]:
    chave, nivel, y, X, corte = args
    cfg = ConfigTreino()
    y_c = y[y.index <= corte]
    if motivo_inelegivel(y_c, cfg, nivel):
        return []
    janelas = {"aic": y_c[y_c.index < origens_walk_forward(corte, cfg)[0]].iloc[-cfg.janela_dias:],
               "ajuste": y_c.iloc[-cfg.janela_dias:]}
    linhas = []
    for nome, yj in janelas.items():
        if len(yj) < cfg.min_historico_dias:
            continue
        try:
            linhas.append({"serie": chave, "corte": f"{corte:%Y-%m-%d}", "janela": nome,
                           "inicio": f"{yj.index.min():%Y-%m-%d}", "fim": f"{yj.index.max():%Y-%m-%d}",
                           **testes(residuo_do_modelo(yj, X))})
        except Exception as e:  # noqa: BLE001
            linhas.append({"serie": chave, "corte": f"{corte:%Y-%m-%d}", "janela": nome, "erro": str(e)[:200]})
    return linhas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    from training_scripts.validation.holdout_vs_walk_forward import carregar_series
    series = carregar_series()
    escolhidas = {k: s for k, s in series.items()
                  if s.nivel == "category" or not motivo_inelegivel(s.y, ConfigTreino(), s.nivel)}
    fim = max(s.y.index.max() for s in escolhidas.values())
    tarefas = [(k, s.nivel, s.y, s.X, c) for k, s in escolhidas.items() for c in CORTES + [fim]]
    print(f"{len(escolhidas)} séries × {len(CORTES) + 1} cortes", flush=True)
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[v] = "1"
    t = time.time()
    linhas = []
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        for r in pool.map(tarefa, tarefas, chunksize=8):
            linhas += r
    os.makedirs(SAIDA, exist_ok=True)
    pd.DataFrame(linhas).to_csv(os.path.join(SAIDA, "janelas.csv"), sep=";", index=False)
    print(f"{len(linhas)} janelas testadas em {time.time() - t:.0f}s → {SAIDA}")


if __name__ == "__main__":
    main()
