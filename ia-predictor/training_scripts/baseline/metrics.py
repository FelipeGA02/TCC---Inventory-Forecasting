"""Métricas de avaliação do L1 (MASE/RMSSE escaladas pela naïve sazonal m=7,
cobertura do IC 95%, MAE/RMSE/MAPE/SMAPE informativos) — CLAUDE.md §"Limiares
de Qualidade dos Modelos".

Todas recebem arrays na escala original de `qtdade` (já revertidas de log1p,
se aplicado) — comparar erro em unidades vendidas, não em log.
"""
from __future__ import annotations

import numpy as np

SEASONAL_PERIOD = 7


def _escala_naive_sazonal(y_train: np.ndarray, m: int = SEASONAL_PERIOD) -> float:
    """Denominador do MASE/RMSSE: erro médio (abs. p/ MASE, quad. p/ RMSSE) da
    naïve sazonal `y[t] = y[t-m]` dentro da amostra de treino."""
    if len(y_train) <= m:
        m = 1
    dif = y_train[m:] - y_train[:-m]
    return dif


def mase(y_true: np.ndarray, y_pred: np.ndarray, y_train: np.ndarray,
          m: int = SEASONAL_PERIOD) -> float:
    dif = _escala_naive_sazonal(np.asarray(y_train, dtype=float), m)
    escala = np.mean(np.abs(dif))
    if escala == 0:
        escala = np.finfo(float).eps
    return float(np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred))) / escala)


def rmsse(y_true: np.ndarray, y_pred: np.ndarray, y_train: np.ndarray,
          m: int = SEASONAL_PERIOD) -> float:
    dif = _escala_naive_sazonal(np.asarray(y_train, dtype=float), m)
    escala = np.mean(dif ** 2)
    if escala == 0:
        escala = np.finfo(float).eps
    return float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2) / escala))


def mae(y_true, y_pred) -> float:
    return float(np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred))))


def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2)))


def mape(y_true, y_pred) -> float | None:
    """Informativo — instável com contagem baixa (CLAUDE.md). `None` se
    algum `y_true` é zero (indefinido)."""
    y_true = np.asarray(y_true, dtype=float)
    if np.any(y_true == 0):
        return None
    return float(np.mean(np.abs((y_true - np.asarray(y_pred)) / y_true)) * 100)


def smape(y_true, y_pred) -> float:
    """Informativo — simétrico, tolera zeros (denominador nunca zera salvo
    y_true=y_pred=0, tratado como erro 0 no ponto)."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true) + np.abs(y_pred)
    erro = np.where(denom == 0, 0.0, np.abs(y_true - y_pred) / denom)
    return float(np.mean(erro) * 200)


def cobertura_ic(y_true, lower, upper) -> float:
    """% de `y_true` dentro de `[lower, upper]` — meta [90%, 98%] (CLAUDE.md)."""
    y_true = np.asarray(y_true, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    dentro = (y_true >= lower) & (y_true <= upper)
    return float(dentro.mean() * 100)
