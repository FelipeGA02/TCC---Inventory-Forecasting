"""Ajuste do SARIMAX e previsão com faixa. Lógica pura (statsmodels)."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX


def ajustar(y: pd.Series, X: pd.DataFrame, ordem: tuple, ordem_sazonal: tuple, maxiter: int = 200):
    """SARIMAX com exógenas. Com d = 0 leva constante (`trend="c"`): sem ela o modelo
    reverteria a zero. Com d > 0 a diferenciação já tira o nível e a constante viraria
    tendência, então fica sem."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # avisos de convergência: a falha real vira exceção
        return SARIMAX(y, exog=X, order=ordem, seasonal_order=ordem_sazonal,
                       trend="c" if ordem[1] == 0 else "n",
                       enforce_stationarity=False, enforce_invertibility=False,
                       ).fit(disp=False, maxiter=maxiter)


def prever(resultado, X_futuro: pd.DataFrame, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Previsão pontual e faixa de (1 − alpha) para as datas de `X_futuro`, sem valores
    negativos (venda não fica abaixo de zero). No dia de loja fechada (`loja_fechada = 1`
    no calendário) previsto e faixa são zero: a exógena só desconta um valor fixo, e os
    termos MA levavam a surpresa dos dias anteriores para o domingo (ex.: Flores de corte
    de Jardim Canadá previa 7 em 01/03/2026 depois de um sábado forte), com a faixa larga de
    um dia aberto. As métricas do walk-forward já ignoram os dias fechados."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fc = resultado.get_forecast(len(X_futuro), exog=X_futuro)
    media = np.clip(np.asarray(fc.predicted_mean, dtype=float), 0, None)
    faixa = np.clip(np.asarray(fc.conf_int(alpha=alpha), dtype=float), 0, None)
    if "loja_fechada" in X_futuro:
        fechada = X_futuro["loja_fechada"].to_numpy(dtype=float) == 1
        media[fechada] = 0.0
        faixa[fechada] = 0.0
    return media, faixa[:, 0], faixa[:, 1]
