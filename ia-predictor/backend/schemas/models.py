"""Schemas Pydantic de `/api/v1/models/*` — campos espelham `openapi.yaml` (fonte da verdade)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ModelMetrics(BaseModel):
    """Métricas do walk-forward do modelo da loja. RMSSE, RMSE e MAPE não são gravados
    pelo treino atual e vêm nulos."""

    MASE: float | None = None
    RMSSE: float | None = None
    IC_coverage_pct: float | None = None
    MAE: float | None = None
    RMSE: float | None = None
    MAPE_pct: float | None = None
    accuracy_label: str | None = None


class UnitModelStatus(BaseModel):
    unidade: str
    status: str
    sarimax_order: str | None = None
    seasonal_order: str | None = None
    metrics: ModelMetrics | None = None
    trained_at: datetime | None = None


class ModelStatusResponse(BaseModel):
    last_retrain_at: datetime | None = None
    next_retrain_at: datetime | None = None
    last_forecast_generation_at: datetime | None = None
    forecast_until: date | None = None
    skus_covered: int = 0
    total_models: int = 0
    trained_models: int = 0
    low_confidence_models: int = 0
    failed_models: int = 0
    insufficient_data_models: int = 0
    units: list[UnitModelStatus] = []
    is_training: bool = False
    training_progress_pct: float | None = None
    last_retrain_summary: str | None = None


class RetrainResponse(BaseModel):
    message: str
    started_at: datetime
