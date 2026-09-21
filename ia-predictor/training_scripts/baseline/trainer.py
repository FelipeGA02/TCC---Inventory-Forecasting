"""Ajuste e forecast de um SARIMAX já com ordem escolhida (`order_selection.py`).

Função fina de propósito único — a decisão de ordem, exógenas e log1p mora nos
módulos vizinhos; aqui só se ajusta o modelo e se extrai média + IC 95% do
forecast.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX


def fit_sarimax(y: pd.Series, order: tuple, seasonal_order: tuple,
                 exog: pd.DataFrame | None = None, trend: str | None = "c"):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        modelo = SARIMAX(
            y.astype(float), exog=exog, order=order, seasonal_order=seasonal_order,
            trend=trend, enforce_stationarity=False, enforce_invertibility=False,
        )
        return modelo.fit(disp=False)


def prever(res, steps: int, exog_future: pd.DataFrame | None = None,
           alpha: float = 0.05) -> dict[str, np.ndarray]:
    """Média + IC (1 - alpha) do forecast `steps` passos à frente."""
    fc = res.get_forecast(steps=steps, exog=exog_future)
    ic = fc.conf_int(alpha=alpha)
    return {
        "media": fc.predicted_mean.to_numpy(),
        "inf": ic.iloc[:, 0].to_numpy(),
        "sup": ic.iloc[:, 1].to_numpy(),
    }
