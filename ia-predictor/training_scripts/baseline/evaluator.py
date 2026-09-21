"""Fase 1.7 — avaliação: hold-out 28 dias + walk-forward CV (origem móvel,
horizonte 14 dias, >= 4 folds quando a série permitir) + diagnóstico de
resíduos (Ljung-Box, Shapiro-Wilk) — CLAUDE.md §"Limiares de Qualidade".

O hold-out final é sempre os últimos `TEST_DAYS` dias da série e nunca entra
nos folds do walk-forward — o walk-forward roda só sobre o restante ("pool de
desenvolvimento"), para o hold-out continuar sendo um teste nunca visto.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from . import metrics as M
from .trainer import fit_sarimax, prever

TEST_DAYS = 28
FORECAST_HORIZON_DAYS = 14
MIN_WALK_FORWARD_FOLDS = 4
SEASONAL_PERIOD = 7


def _inverter_log1p(valores: dict[str, np.ndarray], log1p: bool) -> dict[str, np.ndarray]:
    if not log1p:
        return valores
    return {k: np.expm1(v) for k, v in valores.items()}


def _diagnostico_residuos(res) -> dict:
    from scipy.stats import shapiro
    from statsmodels.stats.diagnostic import acorr_ljungbox

    resid = pd.Series(res.resid).dropna().to_numpy()
    out: dict = {}
    try:
        lags = [l for l in (7, 14) if l < len(resid)]
        lb = acorr_ljungbox(resid, lags=lags, return_df=True) if lags else None
        out["ljung_box_lag7_pvalue"] = float(lb["lb_pvalue"].iloc[0]) if lb is not None and 7 in lags else None
        out["ljung_box_lag14_pvalue"] = float(lb["lb_pvalue"].iloc[1]) if lb is not None and len(lags) > 1 else None
    except Exception:                              # noqa: BLE001
        out["ljung_box_lag7_pvalue"] = None
        out["ljung_box_lag14_pvalue"] = None
    try:
        n_amostra = min(len(resid), 5000)          # limite prático do teste
        out["shapiro_pvalue"] = float(shapiro(resid[:n_amostra])[1])
    except Exception:                              # noqa: BLE001
        out["shapiro_pvalue"] = None
    return out


def avaliar_holdout(y_original: pd.Series, y_fit: pd.Series, log1p: bool,
                     order: tuple, seasonal_order: tuple,
                     exog_full: pd.DataFrame | None = None,
                     test_days: int = TEST_DAYS) -> dict:
    """Ajusta em `y_fit[:-test_days]`, prevê `test_days` passos e compara com
    `y_original` na escala original de `qtdade`."""
    n = len(y_fit)
    corte = n - test_days
    y_train, y_test_original = y_fit.iloc[:corte], y_original.iloc[corte:]
    y_train_original = y_original.iloc[:corte]

    exog_train = exog_full.loc[y_train.index] if exog_full is not None else None
    exog_test = exog_full.loc[y_test_original.index] if exog_full is not None else None

    res = fit_sarimax(y_train, order, seasonal_order, exog=exog_train)
    fc = prever(res, steps=test_days, exog_future=exog_test)
    fc = _inverter_log1p(fc, log1p)

    y_true = y_test_original.to_numpy()
    y_train_np = y_train_original.to_numpy()
    return {
        "mae": M.mae(y_true, fc["media"]),
        "rmse": M.rmse(y_true, fc["media"]),
        "mase": M.mase(y_true, fc["media"], y_train_np, m=SEASONAL_PERIOD),
        "rmsse": M.rmsse(y_true, fc["media"], y_train_np, m=SEASONAL_PERIOD),
        "mape": M.mape(y_true, fc["media"]),
        "smape": M.smape(y_true, fc["media"]),
        "cobertura_ic95": M.cobertura_ic(y_true, fc["inf"], fc["sup"]),
        **_diagnostico_residuos(res),
        "aic": float(res.aic),
        "convergiu": bool(res.mle_retvals.get("converged", True)) if hasattr(res, "mle_retvals") else None,
    }


def _folds_walk_forward(n_dev: int, horizon: int, min_train: int, n_folds: int) -> list[int]:
    """Origens (índice de corte) dos folds, da mais antiga para a mais recente."""
    origens = []
    origem = n_dev - horizon
    while origem >= min_train and len(origens) < n_folds:
        origens.append(origem)
        origem -= horizon
    return sorted(origens)


def avaliar_walk_forward(y_original: pd.Series, y_fit: pd.Series, log1p: bool,
                          order: tuple, seasonal_order: tuple,
                          exog_full: pd.DataFrame | None = None,
                          test_days: int = TEST_DAYS,
                          horizon: int = FORECAST_HORIZON_DAYS,
                          n_folds: int = MIN_WALK_FORWARD_FOLDS,
                          min_train: int = 180) -> dict:
    """Walk-forward de origem móvel sobre o pool de desenvolvimento
    (`y_fit` menos o hold-out final de `test_days`), reaproveitando a MESMA
    ordem já escolhida — não repete a busca em grade a cada fold."""
    n_dev = len(y_fit) - test_days
    y_dev, y_dev_original = y_fit.iloc[:n_dev], y_original.iloc[:n_dev]
    origens = _folds_walk_forward(n_dev, horizon, min_train, n_folds)

    fold_metrics = []
    for origem in origens:
        y_train = y_dev.iloc[:origem]
        y_test_original = y_dev_original.iloc[origem:origem + horizon]
        if len(y_test_original) < horizon:
            continue
        y_train_original = y_dev_original.iloc[:origem]
        exog_train = exog_full.loc[y_train.index] if exog_full is not None else None
        exog_test = exog_full.loc[y_test_original.index] if exog_full is not None else None
        try:
            res = fit_sarimax(y_train, order, seasonal_order, exog=exog_train)
            fc = prever(res, steps=horizon, exog_future=exog_test)
        except Exception:                          # noqa: BLE001
            continue
        fc = _inverter_log1p(fc, log1p)
        y_true = y_test_original.to_numpy()
        y_train_np = y_train_original.to_numpy()
        fold_metrics.append({
            "origem": y_train.index[-1].date().isoformat(),
            "mase": M.mase(y_true, fc["media"], y_train_np, m=SEASONAL_PERIOD),
            "rmsse": M.rmsse(y_true, fc["media"], y_train_np, m=SEASONAL_PERIOD),
            "cobertura_ic95": M.cobertura_ic(y_true, fc["inf"], fc["sup"]),
        })

    if not fold_metrics:
        return {"n_folds": 0, "mase_medio": None, "rmsse_medio": None,
                "cobertura_ic95_media": None, "folds": []}
    return {
        "n_folds": len(fold_metrics),
        "mase_medio": float(np.mean([f["mase"] for f in fold_metrics])),
        "rmsse_medio": float(np.mean([f["rmsse"] for f in fold_metrics])),
        "cobertura_ic95_media": float(np.mean([f["cobertura_ic95"] for f in fold_metrics])),
        "folds": fold_metrics,
    }
