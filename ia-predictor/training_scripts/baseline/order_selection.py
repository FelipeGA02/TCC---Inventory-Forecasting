"""Fase 1.6 — seleção de ordem via grid AIC (p,q ∈ 0..2; P,Q ∈ 0..1; D=0; m=7).

`d` não entra no grid: é decidido uma vez por série via ADF/KPSS — mesma regra
do EDA (`eda.eda_series._adf_kpss`): ADF rejeita raiz unitária e KPSS não
rejeita estacionariedade → d=0; os dois discordam → começa em d=0 (revisar por
resíduo); os dois apontam não-estacionariedade → d=1. `D=0` é fixo (ADR-004):
poucos ciclos anuais completos para justificar diferenciação sazonal.
"""
from __future__ import annotations

import itertools
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

SEASONAL_PERIOD = 7
D_FIXO = 0
P_MAX = Q_MAX = 2   # p, q ∈ 0..2
PS_MAX = QS_MAX = 1  # P, Q ∈ 0..1


def sugerir_d(serie: pd.Series) -> int:
    """ADF + KPSS → sugestão de `d` (mesma regra do EDA, ADR-004)."""
    from statsmodels.tools.sm_exceptions import InterpolationWarning
    from statsmodels.tsa.stattools import adfuller, kpss

    x = serie.astype(float).values
    try:
        adf_p = adfuller(x, autolag="AIC")[1]
    except Exception:                              # noqa: BLE001
        adf_p = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InterpolationWarning)
            kpss_p = kpss(x, regression="c", nlags="auto")[1]
    except Exception:                              # noqa: BLE001
        kpss_p = None
    adf_ok = adf_p is not None and adf_p < 0.05
    kpss_ok = kpss_p is not None and kpss_p > 0.05
    if not adf_ok and not kpss_ok:
        return 1
    return 0


def grid_ordens(d: int):
    """Gera (order, seasonal_order) para todo o grid — D e m fixos."""
    for p, q in itertools.product(range(P_MAX + 1), range(Q_MAX + 1)):
        for P, Q in itertools.product(range(PS_MAX + 1), range(QS_MAX + 1)):
            yield (p, d, q), (P, D_FIXO, Q, SEASONAL_PERIOD)


def selecionar_ordem(serie: pd.Series, exog: pd.DataFrame | None = None,
                      trend: str | None = "c") -> dict:
    """Varre o grid, ajusta cada combinação por AIC e devolve a melhor.

    Combinações que não convergem ou lançam exceção são descartadas — comum em
    cantos do grid com ordem alta e poucos dados. Se nenhuma convergir, cai num
    fallback conservador `(1, d, 0)(0, 0, 0, 7)` para nunca deixar o par sem
    modelo.
    """
    d = sugerir_d(serie)
    y = serie.astype(float)
    melhor = None
    for order, seasonal_order in grid_ordens(d):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = SARIMAX(
                    y, exog=exog, order=order, seasonal_order=seasonal_order,
                    trend=trend, enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit(disp=False)
            aic = float(res.aic)
            if not np.isfinite(aic):
                continue
            if melhor is None or aic < melhor["aic"]:
                melhor = {"order": order, "seasonal_order": seasonal_order,
                          "aic": aic, "d": d}
        except Exception:                          # noqa: BLE001
            continue
    if melhor is None:
        melhor = {"order": (1, d, 0), "seasonal_order": (0, D_FIXO, 0, SEASONAL_PERIOD),
                  "aic": None, "d": d, "fallback": True}
    return melhor
